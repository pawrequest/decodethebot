import asyncio
from asyncio import Queue
from functools import lru_cache
from typing import AsyncGenerator, TypeVar, Union

from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
import sqlmodel as sqm

import scrapaw
from pawdantic.pawsql import sqlpr
from scrapaw.abs import DupeError, MaxDupesError, dupes_not_exceeded
from suppawt import async_, get_set
from .core.consts import (
    GURU_NAMES_FILE,
    MAX_DUPES,
    SCRAPER_SLEEP,
    logger,
)
from .core.database import engine_
from .models.episodedb import DTGEpisodeDB, DTGEpisodeOut
from .models.guru import Guru
from .models.reddit_thread import RedditThread
from .models.links import GuruEpisodeLink, RedditThreadEpisodeLink, RedditThreadGuruLink

load_dotenv()

DB_MODELS = (Guru, DTGEpisodeDB, RedditThread)
LINK_MODELS = (GuruEpisodeLink, RedditThreadEpisodeLink, RedditThreadGuruLink)
ALL_MODELS = (*DB_MODELS, *LINK_MODELS)
ALL_MODELS_TYPE = Union[ALL_MODELS]
DB_MODEL_TYPE = Union[DB_MODELS]
DB_MODEL_VAR = TypeVar("DB_MODEL_VAR", bound=DB_MODEL_TYPE)


class DTG:
    def __init__(
            self,
            subreddit: Subreddit,
            sqlm_session: sqm.Session | None = None,
            queue: Queue | None = None,
            http_session: ClientSession | None = None,
    ):
        self.session_q: sqm.Session = sqlm_session or sqm.Session(engine_())
        self.session_h = http_session or ClientSession()
        self.subreddit = subreddit
        self.queue_ep = queue
        self.queue_red = queue
        self.tasks = list()
        self.podcast = scrapaw.DTGPodcast()

    # @classmethod
    # @asynccontextmanager
    # async def minimum_context(
    #         cls, sub_name: str = consts.SUBREDDIT_NAME, podcast_url: str = PODCAST_URL
    # ) -> "DTG":
    #     process_qu = asyncio.Queue()
    #     with Session(engine_()) as session:
    #         # backup_bot = SQLModelBackup(session, model_map_(), BACKUP_JSON, output_dir=BACKUP_DIR)
    #         # pruner = Pruner(backup_target=BACKUP_JSON, output_dir=BACKUP_DIR)
    #
    #         async with ClientSession() as http_session:
    #             podcast = scrapaw.DTGPodcast()
    #
    #             async with subreddit_cm(
    #                     sub_name=sub_name
    #             ) as subreddit:  # noqa E1120 pycharm bug reported
    #                 try:
    #                     yield cls(
    #                         session=session,
    #                         subreddit=subreddit,
    #                         queue=process_qu,
    #                         http_session=http_session,
    #                     )
    #                 finally:
    #                     # await http_session.close()
    #                     ...

    # @ps.quiet_cancel_try_log_as
    async def run(self):
        logger.info("Initialised")
        with self.session_q as session:
            gurus_from_file(session, GURU_NAMES_FILE)

            # if RESTORE_FROM_JSON:
            #     self.backup_bot.restore()
            # if TRIM_DB:
            #     trim_db(self.session)
            # if INIT_EPS:
            #     await init_eps(self.session, self.podcast_soup.episode_stream())

            self.tasks = [
                # asyncio.create_task(
                #     ps.backup_copy_prune(self.backup_bot, self.pruner, BACKUP_SLEEP)
                # ),
                asyncio.create_task(self.q_episodes()),
                # asyncio.create_task(self.q_threads()),
                # asyncio.create_task(self.process_queue()),
            ]
            logger.info("Tasks created")

    async def kill(self):
        logger.info("Killing")
        # await self.backup_bot.backup()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks)

    @async_.quiet_cancel_try_log_as
    async def q_episodes(self):
        episodes = self.session_q.exec(sqm.select(DTGEpisodeDB)).all()
        dtg_eps = [DTGEpisodeOut.model_validate(_) for _ in episodes]
        podcast = scrapaw.DTGPodcast(episodes=dtg_eps)

        while True:
            dupes = 0

            try:
                async for ep in self.podcast.get_episodes(
                        session_h=self.session_h,
                        max_dupes=MAX_DUPES
                ):

                    await self.not_in_sesh(ep)
                    except DupeError:
                        dupes += 1
                        try:
                            await dupes_not_exceeded(dupes)
                            continue
                        except MaxDupesError:
                            break

            #     podcast.episodes.append(ep)
            #     await self.queue_ep.put(ep)
            #
            # logger.debug(f"Sleeping for {SCRAPER_SLEEP} seconds")
            # await asyncio.sleep(SCRAPER_SLEEP)

    async def not_in_sesh(self, ep):
        if sqlpr.obj_in_session(self.session_q, ep, DTGEpisodeDB):
            raise DupeError(f"Duplicate episode found: {ep.url}")

    @async_.quiet_cancel_try_log_as
    async def q_threads(self):
        sub_stream = self.subreddit.stream.submissions(skip_existing=False)
        async for sub in sub_stream:
            try:
                thread = RedditThread.from_submission(sub)

                if sqlpr.obj_in_session(self.session_q, thread, RedditThread):
                    continue

                await self.queue_red.put(thread)
            except Exception as e:
                logger.error(f"Error getting thread from submission: {e}")

    # @async_.quiet_cancel_try_log_as
    # async def process_queue(self):
    #     while True:
    #         instance = await self.queue.get()
    #         matches_d = await self.all_matches(instance)
    #         matches_n = sum([len(_) for _ in matches_d.values()])
    #         if isinstance(instance, RedditThread) and not matches_n:
    #             continue
    #         self.session_q.add(instance)
    #         await sqlpr.assign_all(instance, matches_d)
    #         logger.info(
    #             f"Processing {instance.__class__.__name__} - {get_set.title_or_name_val(instance)}"
    #         )
    #         self.session_q.commit()
    #         self.queue.task_done()

    @async_.quiet_cancel_try_log_as
    async def process_ep_queue(self):
        while True:
            episode = await self.queue_ep.get()

            gurus = db_obj_matches(self.session_q, episode, Guru)
            threads = db_obj_matches(self.session_q, episode, RedditThread)
            matches_n = len(gurus) + len(threads)
            episode.

            self.session_q.add(episode)

            await sqlpr.assign_all(episode, matches_d)
            logger.info(
                f"Processing {episode.__class__.__name__} - {get_set.title_or_name_val(episode)}"
            )
            self.session_q.commit()
            self.queue.task_done()

    async def all_matches(self, instance: DB_MODEL_TYPE) -> dict[str, list[DB_MODEL_TYPE]]:
        res = {
            get_set.snake_name_s(match_type): db_obj_matches(self.session_q, instance, match_type)
            for match_type in DB_MODELS
        }
        return res


def db_obj_matches(
        session: sqm.Session, obj: DB_MODEL_TYPE, model: type(DB_MODEL_VAR)
) -> list[DB_MODEL_VAR]:
    if isinstance(obj, model):
        return []
    db_objs = session.exec(sqm.select(model)).all()
    identifier = get_set.title_or_name_val(obj)
    obj_var = get_set.title_or_name_var(model)

    if matched_tag_models := [_ for _ in db_objs if one_in_other(_, obj_var, identifier)]:
        logger.debug(
            f"Found {len(matched_tag_models)} '{model.__name__}' {'match' if len(matched_tag_models) == 1 else 'matches'} for {obj.__class__.__name__} - {identifier}"
        )
    return matched_tag_models


def one_in_other(obj: DB_MODEL_VAR, obj_var: str, compare_val: str):
    ob_low = getattr(obj, obj_var).lower()
    return ob_low in compare_val.lower() or compare_val.lower() in ob_low


def gurus_from_file(session, infile):
    with open(infile, "r") as f:
        guru_names = f.read().split(",")
    session_gurus = session.exec(sqm.select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()


@lru_cache()
def model_map_():
    return {get_set.snake_name(_): _ for _ in ALL_MODELS}


# @ps.quiet_cancel_try_log_as
async def init_eps(session, episode_stream: AsyncGenerator[scrapaw.DTGEpisode, None]):
    init_n = 1
    init_i = 0
    logger.info("Initialising episodes")
    eps = []
    async for ep in episode_stream:
        ep = DTGEpisodeDB.model_validate(ep)
        eps.append(ep)
        init_i += 1
        if init_i >= init_n:
            break

    # eps = [Episode.model_validate(_) async for _ in episode_stream]
    eps = sorted(eps, key=lambda _: _.date)
    for ep in eps:
        if sqlpr.obj_in_session(session, ep, DTGEpisodeDB):
            continue
        logger.info(f"Adding {ep.title}")
        session.add(ep)
        thread_matches = db_obj_matches(session, ep, RedditThread)
        guru_matches = db_obj_matches(session, ep, Guru)
        sqlpr.assign_rel(ep, RedditThread, thread_matches)
        sqlpr.assign_rel(ep, Guru, guru_matches)
    if session.new:
        session.commit()
