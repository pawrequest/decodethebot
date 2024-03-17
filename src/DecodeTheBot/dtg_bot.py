import asyncio
from asyncio import Queue
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator, TypeVar, Union

from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
import sqlmodel as sqm

import redditbot
import scrapaw
from pawdantic.pawsql import sqlpr
from scrapaw import abs, dtg
from suppawt import get_set
from .core import consts
from .core.consts import (
    GURU_NAMES_FILE,
    logger,
)
from .core.database import engine_
from .models.episodedb import DTGEpisodeDB
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
            sqm_session: sqm.Session | None = None,
            queue_ep: Queue | None = None,
            queue_red: Queue | None = None,
            http_session: ClientSession | None = None,
            # podcast: scrapaw.DTGPodcast | None = None,
    ):
        self.subreddit = subreddit

        self.sqm_session: sqm.Session = sqm_session or sqm.Session(engine_())
        self.http_session = http_session or ClientSession()
        self.queue_ep = queue_ep or Queue()
        self.queue_red = queue_red or Queue()
        # self.podcast = podcast or scrapaw.DTGPodcast()
        self.tasks = list()

    @classmethod
    @asynccontextmanager
    async def from_env(
            cls,
    ) -> "DTG":
        with sqm.Session(engine_()) as sqmsesh:
            async with ClientSession() as http_session:
                async with redditbot.subreddit_cm(
                        sub_name=consts.SUBREDDIT_NAME
                ) as subreddit:  # noqa E1120 pycharm bug reported
                    try:
                        yield cls(
                            sqm_session=sqmsesh,
                            subreddit=subreddit,
                            http_session=http_session,
                        )
                    finally:
                        await http_session.close()

        # with sqm.Session(engine_()) as sqmsesh:
        #     async with (
        #         ClientSession() as session_h,
        #         redditbot.subreddit_cm(sub_name=consts.SUBREDDIT_NAME) as subreddit # noqa E1120 pycharm bug reported
        #     ):
        #
        #         try:
        #             yield cls(
        #                 sqm_session=sqmsesh,
        #                 subreddit=subreddit,
        #                 http_session=session_h,
        #             )
        #         finally:
        #             await session_h.close()
        #             ...

    # @ps.quiet_cancel_try_log_as
    async def run(self):
        logger.info("Initialised")
        with self.sqm_session as session:
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
                asyncio.create_task(self.schedule_episode_q()),
                asyncio.create_task(self.process_ep_queue()),
                asyncio.create_task(self.schedule_thread_q()),
                asyncio.create_task(self.process_thread_queue()),
            ]
            logger.info("Tasks created")

    async def kill(self):
        logger.info("Killing")
        # await self.backup_bot.backup()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks)

    async def schedule_episode_q(self):
        while True:
            try:
                await self.q_episodes()
            except abs.MaxDupeError:
                logger.info('Maximum Duplicate Episodes Reached')

            logger.debug(f"Sleeping for {consts.SCRAPER_SLEEP} seconds")
            await asyncio.sleep(consts.SCRAPER_SLEEP)

    async def schedule_thread_q(self):
        while True:
            try:
                await self.q_threads()
            except abs.MaxDupeError:
                logger.info('Maximum Duplicate Threads Reached')

            logger.debug(f"RedditBot Sleeping for {consts.REDDIT_SLEEP} seconds")
            await asyncio.sleep(consts.REDDIT_SLEEP)

    async def q_episodes(self, max_dupes: int = consts.MAX_DUPES):
        dupes = 0
        async for ep_ in dtg.get_episodes_blind(
                base_url=consts.PODCAST_URL,
                session_h=self.http_session,
                # limit=consts.EPISODE_SCRAPE_LIMIT,
        ):
            ep = DTGEpisodeDB.model_validate(ep_)
            if sqlpr.obj_in_session(self.sqm_session, ep):
                dupes += 1
                if dupes > max_dupes:
                    raise abs.MaxDupeError(f"Max dupes reached: {max_dupes}")
                continue

            await self.queue_ep.put(ep)

    async def q_threads(self, max_dupes: int = consts.MAX_DUPES):
        dupes = 0
        async for sub in self.subreddit.stream.submissions(skip_existing=False):
            thread = RedditThread.from_submission(sub)
            if sqlpr.obj_in_session(self.sqm_session, thread):
                dupes += 1
                if dupes > max_dupes:
                    raise abs.MaxDupeError(f"Max dupes reached: {max_dupes}")
                continue

            await self.queue_red.put(thread)

    async def process_ep_queue(self):
        while True:
            episode_ = await self.queue_ep.get()
            episode = DTGEpisodeDB.model_validate(episode_)

            gurus = db_obj_matches(self.sqm_session, episode, Guru)
            threads = db_obj_matches(self.sqm_session, episode, RedditThread)
            episode.gurus.extend(gurus)
            episode.reddit_threads.extend(threads)

            self.sqm_session.add(episode)

            logger.info(
                f"Processing {episode.__class__.__name__} - {get_set.title_or_name_val(episode)}"
            )
            self.sqm_session.commit()
            self.queue_ep.task_done()

    async def process_thread_queue(self):
        while True:
            thread_ = await self.queue_red.get()
            thread = RedditThread.model_validate(thread_)

            gurus = db_obj_matches(self.sqm_session, thread, Guru)
            episodes = db_obj_matches(self.sqm_session, thread, DTGEpisodeDB)
            thread.gurus.extend(gurus)
            thread.episodes.extend(episodes)

            self.sqm_session.add(thread)

            logger.info(
                f"Processing {thread.__class__.__name__} - {get_set.title_or_name_val(thread)}"
            )
            self.sqm_session.commit()
            self.queue_red.task_done()


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
