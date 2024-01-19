import asyncio
from asyncio import Queue
from functools import lru_cache
from typing import TypeVar, Union

from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
from episode_scraper.soups_dc import PodcastSoup
from pawsupport import Pruner, SQLModelBot, backup_copy_prune, get_hash, quiet_cancel, title_or_name
from pawsupport.misc import to_snake
from sqlmodel import Session, select, text

from .core.consts import (
    BACKUP_SLEEP,
    GURU_NAMES_FILE,
    INIT_EPS,
    MAX_DUPES,
    RESTORE_FROM_JSON,
    SCRAPER_SLEEP,
    TRIM_DB,
    logger,
)
from .models.episode import Episode
from .models.guru import Guru
from .models.reddit_thread import RedditThread

load_dotenv()

DB_MODEL_TYPE = Union[Guru, Episode, RedditThread]
DB_MODEL_VAR = TypeVar("DB_MODEL_VAR", bound=DB_MODEL_TYPE)


class DTG:
    def __init__(
        self,
        session: Session,
        pruner: Pruner,
        backup_bot: SQLModelBot,
        subreddit: Subreddit,
        queue: Queue,
        podcast_soup: PodcastSoup,
        http_session: ClientSession = None,
    ):
        self.session = session
        self.http_session = http_session or ClientSession()
        self.pruner = pruner
        self.backup_bot = backup_bot
        self.subreddit = subreddit
        self.process_q = queue
        self.tasks = list()
        self.podcast_soup = podcast_soup

    @quiet_cancel
    async def run(self):
        logger.info("Initialised")
        with self.session as session:
            gurus_from_file(session, GURU_NAMES_FILE)

            if RESTORE_FROM_JSON:
                self.backup_bot.restore()
            if INIT_EPS:
                await self.init_eps()
            if TRIM_DB:
                self.trim_db()

            self.tasks = [
                asyncio.create_task(backup_copy_prune(self.backup_bot, self.pruner, BACKUP_SLEEP)),
                asyncio.create_task(self.q_episodes()),
                asyncio.create_task(self.q_threads()),
                asyncio.create_task(self.process_queue()),
            ]
            logger.info("Tasks created")
            # await asyncio.gather(*self.tasks)

    async def kill(self):
        logger.info("Killing")
        await self.backup_bot.backup()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks)

    @quiet_cancel
    async def q_episodes(self):
        while True:
            dupes = 0
            async for ep in self.podcast_soup.episode_stream():
                ep = Episode.model_validate(ep)
                if self.exists(ep, Episode):
                    if dupes > MAX_DUPES:
                        logger.debug(f"Found {dupes} duplicates, stopping")
                        break
                    dupes += 1
                    continue
                await self.process_q.put(ep)

            logger.debug(f"Sleeping for {SCRAPER_SLEEP} seconds")
            await asyncio.sleep(SCRAPER_SLEEP)

    @quiet_cancel
    async def init_eps(self):
        logger.info("Initialising episodes")
        eps = [Episode.model_validate(_) async for _ in self.podcast_soup.episode_stream()]
        eps = sorted(eps, key=lambda _: _.date)
        for ep in eps:
            if self.exists(ep, Episode):
                continue
            logger.info(f"Adding {ep.title}")
            self.session.add(ep)
            thread_matches = get_matches(self.session, ep, RedditThread)
            guru_matches = get_matches(self.session, ep, Guru)
            self.assign_rel(ep, RedditThread, thread_matches)
            self.assign_rel(ep, Guru, guru_matches)
        self.session.commit()

    @quiet_cancel
    async def q_threads(self):
        sub_stream = self.subreddit.stream.submissions(skip_existing=False)
        async for sub in sub_stream:
            thread = RedditThread.from_submission(sub)

            if self.exists(thread, RedditThread):
                continue

            await self.process_q.put(thread)

    @quiet_cancel
    async def process_queue(self):
        while True:
            instance = await self.process_q.get()
            guru_matches = get_matches(self.session, instance, Guru)
            episode_matches = get_matches(self.session, instance, Episode)
            thread_matches = get_matches(self.session, instance, RedditThread)
            if isinstance(instance, RedditThread) and not any([guru_matches, episode_matches]):
                continue

            self.session.add(instance)

            self.assign_rel(instance, Guru, guru_matches)
            self.assign_rel(instance, Episode, episode_matches)
            self.assign_rel(instance, RedditThread, thread_matches)

            logger.info(f"Processing {instance.__class__.__name__} - {title_or_name(instance)}")

            self.session.commit()
            self.process_q.task_done()

    def assign_rel(self, instance: DB_MODEL_TYPE, model: type[DB_MODEL_TYPE], matches) -> int:
        if isinstance(instance, model):
            return 0
        try:
            to_extend = getattr(instance, to_snake(model.__name__ + "s"))
            to_extend.extend(matches)
            return len(matches)
        except Exception as e:
            logger.error(f"Error assigning {model.__name__} to {instance.__class__.__name__} - {e}")

    def exists(self, obj: DB_MODEL_VAR, model: type(DB_MODEL_VAR)) -> bool:
        # todo hash in db
        return get_hash(obj) in [get_hash(_) for _ in self.session.exec(select(model)).all()]

    def trim_db(self):
        ep_trim = 107
        red_trim = 0
        stmts = [
            text(_)
            for _ in [
                f"delete from episode where id >={ep_trim}",
                f"delete from guruepisodelink where episode_id >={ep_trim}",
                f"delete from redditthreadepisodelink where episode_id >={ep_trim}",
                f"delete from redditthread where id >={red_trim}",
                f"delete from redditthreadepisodelink where reddit_thread_id >={red_trim}",
                f"delete from redditthreadgurulink where reddit_thread_id >={red_trim}",
            ]
        ]
        try:
            [self.session.execute(_) for _ in stmts]
            self.session.commit()
        except Exception as e:
            logger.error(e)


def get_matches(
    session: Session, obj_with_title_or_name: DB_MODEL_VAR, match_model: type(DB_MODEL_VAR)
) -> list[DB_MODEL_VAR]:
    if isinstance(obj_with_title_or_name, match_model):
        return []
    db_objs = session.exec(select(match_model)).all()
    identifier = title_or_name(obj_with_title_or_name)
    if hasattr(match_model, "title"):
        obj_var = "title"
    elif hasattr(match_model, "name"):
        obj_var = "name"
    else:
        raise ValueError(f"Can't find title or name attribute on {match_model.__name__}")

    if matched_tag_models := [_ for _ in db_objs if one_in_other(_, obj_var, identifier)]:
        logger.debug(
            f"Found {len(matched_tag_models)} '{match_model.__name__}' {'match' if len(matched_tag_models) == 1 else 'matches'} for {obj_with_title_or_name.__class__.__name__} - {identifier}"
        )
    return matched_tag_models


def one_in_other(obj: DB_MODEL_VAR, obj_var: str, compare_val: str):
    ob_val = getattr(obj, obj_var).lower()
    return ob_val in compare_val.lower() or compare_val.lower() in ob_val


def gurus_from_file(session, infile):
    with open(infile, "r") as f:
        guru_names = f.read().split(",")
    session_gurus = session.exec(select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()


@lru_cache()
def json_map_():
    from .core.json_map import JSON_NAMES_TO_MODEL_MAP

    return JSON_NAMES_TO_MODEL_MAP


async def assign_relations_old(session, instance) -> bool:
    guru_matches = get_matches(session, instance, Guru)
    episode_matches = get_matches(session, instance, Episode)
    thread_matches = get_matches(session, instance, RedditThread)

    if guru_matches and not isinstance(instance, Guru):
        instance.gurus.extend(guru_matches)
    if episode_matches and not isinstance(instance, Episode):
        instance.episodes.extend(episode_matches)
    if thread_matches and not isinstance(instance, RedditThread):
        instance.reddit_threads.extend(thread_matches)
    return any([guru_matches, episode_matches, thread_matches])
