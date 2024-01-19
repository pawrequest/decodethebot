import asyncio
from asyncio import Queue
from functools import lru_cache
from typing import TypeVar, Union

from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
from episode_scraper.soups_dc import PodcastSoup
from pawsupport import Pruner, SQLModelBot, backup_copy_prune, get_hash, quiet_cancel
from sqlmodel import Session, select

from .core.consts import BACKUP_SLEEP, GURU_NAMES_FILE, RESTORE_FROM_JSON, SCRAPER_SLEEP, logger
from .models.episode_model import Episode
from .models.guru import Guru
from .models.reddit_thread_model import RedditThread
from .ui.mixin import title_or_name

load_dotenv()

DB_MODEL = TypeVar("DB_MODEL", bound=Union[Guru, Episode, RedditThread])
MAX_DUPES = 12


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
                if dupes > MAX_DUPES:
                    logger.debug(f"Found {dupes} duplicates, stopping")
                    break
                ep = Episode.model_validate(ep)
                if exists(self.session, ep, Episode):
                    dupes += 1
                else:
                    await self.process_q.put(ep)
            logger.debug(f"Sleeping for {SCRAPER_SLEEP} seconds")
            await asyncio.sleep(SCRAPER_SLEEP)

    @quiet_cancel
    async def q_threads(self):
        sub_stream = self.subreddit.stream.submissions(skip_existing=False)
        async for sub in sub_stream:
            thread = RedditThread.from_submission(sub)

            if exists(self.session, thread, RedditThread):
                continue

            await self.process_q.put(thread)

    @quiet_cancel
    async def process_queue(self):
        while True:
            instance = await self.process_q.get()
            guru_matches = get_matches(self.session, instance, Guru)
            episode_matches = get_matches(self.session, instance, Episode)
            thread_matches = get_matches(self.session, instance, RedditThread)

            if guru_matches and not isinstance(instance, Guru):
                instance.gurus.extend(guru_matches)

            if episode_matches and not isinstance(instance, Episode):
                instance.episodes.extend(episode_matches)

            if thread_matches and not isinstance(instance, RedditThread):
                instance.reddit_threads.extend(thread_matches)

            self.session.add(instance)
            self.session.commit()
            self.process_q.task_done()


def get_matches(
    session: Session, obj_with_title_or_name: DB_MODEL, match_model: type(DB_MODEL)
) -> list[DB_MODEL]:
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


def one_in_other(obj: DB_MODEL, obj_var: str, compare_val: str):
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


def exists(session: Session, obj: DB_MODEL, model: type(DB_MODEL)) -> bool:
    # todo hash in db
    return get_hash(obj) in [get_hash(_) for _ in session.exec(select(model)).all()]


@lru_cache()
def json_map_():
    from .core.json_map import JSON_NAMES_TO_MODEL_MAP

    return JSON_NAMES_TO_MODEL_MAP
