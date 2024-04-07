import asyncio
from asyncio import Queue
from contextlib import asynccontextmanager
from functools import lru_cache

from pydantic import alias_generators
import pydantic as _p
from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
import sqlmodel as sqm
from loguru import logger

import redditbot
import suppawt.convert
from pawdantic.pawsql import sqlpr
from scrapaw import dtg, pod_abs
from suppawt import get_set, pawsync
from .core import consts, database
from .dtg_types import ALL_MODELS, DB_MODEL_TYPE, DB_MODEL_VAR
from .models import episode_m, guru_m, reddit_m

load_dotenv()


class DTG:
    def __init__(
            self,
            subreddit: Subreddit,
            sqm_session: sqm.Session | None = None,
            episode_q: Queue | None = None,
            reddit_q: Queue | None = None,
            http_session: ClientSession | None = None,
    ):
        self.subreddit = subreddit

        self.sqm_session: sqm.Session = sqm_session or sqm.Session(database.engine_())
        self.http_session = http_session or ClientSession()
        self.episode_q = episode_q or Queue()
        self.reddit_q = reddit_q or Queue()
        self.tasks = list()

    @classmethod
    @asynccontextmanager
    async def from_env(
            cls,
    ) -> "DTG":
        with sqm.Session(database.engine_()) as sqmsesh:
            async with ClientSession() as http_session:
                async with redditbot.subreddit_cm(
                        sub_name=consts.SUBREDDIT_NAME  # noqa E1120 pycharm bug reported
                ) as subreddit:  # noqa E1120 pycharm bug reported
                    try:
                        yield cls(
                            sqm_session=sqmsesh,
                            subreddit=subreddit,
                            http_session=http_session,
                        )
                    finally:
                        await http_session.close()

    async def run(self):
        logger.info("Initialised")
        with self.sqm_session as session:
            gurus_from_file(session, consts.GURU_NAMES_FILE)

            self.tasks = [
                asyncio.create_task(self.episode_q_manager()),
                asyncio.create_task(self.reddit_q_manager()),
                asyncio.create_task(
                    self.process_queue(
                        self.reddit_q,
                        reddit_m.RedditThread,
                        log_category='reddit',
                        relation_classes=[episode_m.Episode, guru_m.Guru]
                    )
                ),

                asyncio.create_task(
                    self.process_queue(
                        self.episode_q,
                        episode_m.Episode,
                        log_category='episode',
                        relation_classes=[reddit_m.RedditThread, guru_m.Guru]
                    )
                ),
            ]
            logger.info("Tasks created")

    @pawsync.quiet_cancel
    async def kill(self):
        logger.info("Killing")
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks)

    @pawsync.quiet_cancel
    async def episode_q_manager(self):
        while True:
            try:
                await self.get_episodes()
            except pod_abs.MaxDupeError:
                logger.debug('Maximum Duplicate Episodes Reached', category='episode')

            logger.debug(
                f"Episode manager sleeping for {consts.SCRAPER_SLEEP} seconds",
                category='episode'
            )
            await asyncio.sleep(consts.SCRAPER_SLEEP)

    async def get_episodes(self, max_dupes: int = consts.MAX_DUPES):
        dupes = 0
        async for ep_ in dtg.get_episodes_blind(
                base_url=consts.PODCAST_URL,
                session_h=self.http_session,
                limit=consts.EPISODE_SCRAPE_LIMIT,
        ):
            ep = episode_m.Episode.model_validate(ep_)
            if sqlpr.obj_in_session(self.sqm_session, ep):
                logger.debug(f"Duplicate Episode: {ep.title}", category='episode')
                dupes += 1
                if max_dupes and dupes > max_dupes:
                    raise pod_abs.MaxDupeError(f"Max dupes reached: {max_dupes}")
                continue
            logger.debug(f'Found Episode: {ep.title}', category='episode')
            await self.episode_q.put(ep)

    @pawsync.quiet_cancel
    async def reddit_q_manager(self):
        while True:
            try:
                await self.get_reddit_threads()
            except pod_abs.MaxDupeError:
                logger.debug(
                    'Maximum Duplicate Threads Reached',
                    category='reddit',
                )

            logger.debug(f"RedditBot Sleeping for {consts.REDDIT_SLEEP} seconds", category='reddit')
            await asyncio.sleep(consts.REDDIT_SLEEP)

    async def get_reddit_threads(self, max_dupes: int = consts.MAX_DUPES):
        dupes = 0
        async for sub in self.subreddit.stream.submissions(skip_existing=False):
            thread = reddit_m.RedditThread.from_submission(sub)
            if sqlpr.obj_in_session(self.sqm_session, thread):
                dupes += 1
                if max_dupes and dupes > max_dupes:
                    raise pod_abs.MaxDupeError(f"Max dupes reached: {max_dupes}")
                continue

            logger.info(f'Found Reddit Thread: {thread.title}', category='reddit')
            await self.reddit_q.put(thread)

    @pawsync.quiet_cancel
    async def process_queue(
            self,
            queue,
            model_class: type(_p.BaseModel),
            relation_classes: list[type(_p.BaseModel)],
            log_category: str = 'General',
    ):
        while True:
            item_ = await queue.get()
            item = model_class.model_validate(item_)
            item_str = f'{item.__class__.__name__} - {get_set.title_or_name_val(item)}'
            logger.debug(f"Processing {item_str}", category=log_category)

            self.sqm_session.add(item)
            for relation_class in relation_classes:
                await self.assign_rel(item, relation_class)

            self.sqm_session.commit()
            self.sqm_session.refresh(item)
            queue.task_done()
            logger.info(f"Processed {item_str}", category=log_category)

    async def assign_rel(self, item, relation_class):
        related_items = db_obj_matches(self.sqm_session, item, relation_class)
        alias = alias_generators.to_snake(relation_class.__name__) + 's'
        getattr(item, alias).extend(related_items)

    # async def process_ep_queue(self):
    #     while True:
    #         episode_ = await self.episode_q.get()
    #         episode = episode_m.DTGEpisodeDB.model_validate(episode_)
    #
    #         gurus = db_obj_matches(self.sqm_session, episode, guru_m.Guru)
    #         threads = db_obj_matches(self.sqm_session, episode, reddit_m.RedditThread)
    #         episode.gurus.extend(gurus)
    #         episode.reddit_ms.extend(threads)
    #
    #         self.sqm_session.add(episode)
    #
    #         logger.info(
    #             f"Processing {episode.__class__.__name__} - {get_set.title_or_name_val(episode)}"
    #         )
    #         self.sqm_session.commit()
    #         self.episode_q.task_done()
    #
    # async def process_reddit_q(self):
    #     while True:
    #         thread_ = await self.reddit_q.get()
    #         thread = reddit_m.RedditThread.model_validate(thread_)
    #
    #         gurus = db_obj_matches(self.sqm_session, thread, guru_m.Guru)
    #         episodes = db_obj_matches(self.sqm_session, thread, episode_m.DTGEpisodeDB)
    #         thread.gurus.extend(gurus)
    #         thread.episodes.extend(episodes)
    #
    #         self.sqm_session.add(thread)
    #
    #         logger.info(
    #             f"Processing {thread.__class__.__name__} - {get_set.title_or_name_val(thread)}"
    #         )
    #         self.sqm_session.commit()
    #         self.reddit_q.task_done()


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
    session_gurus = session.exec(sqm.select(guru_m.Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [guru_m.Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()


@lru_cache()
def model_map_():
    return {suppawt.convert.snake_name(_): _ for _ in ALL_MODELS}

# @ps.quiet_cancel_try_log_as
# async def init_eps(session, episode_stream: AsyncGenerator[scrapaw.DTGEpisode, None]):
#     init_n = 1
#     init_i = 0
#     logger.info("Initialising episodes")
#     eps = []
#     async for ep in episode_stream:
#         ep = episode_m.DTGEpisodeDB.model_validate(ep)
#         eps.append(ep)
#         init_i += 1
#         if init_i >= init_n:
#             break
#
#     # eps = [Episode.model_validate(_) async for _ in episode_stream]
#     eps = sorted(eps, key=lambda _: _.date)
#     for ep in eps:
#         if sqlpr.obj_in_session(session, ep):
#             continue
#         logger.info(f"Adding {ep.title}")
#         session.add(ep)
#         thread_matches = db_obj_matches(session, ep, reddit_m.RedditThread)
#         guru_matches = db_obj_matches(session, ep, guru_m.Guru)
#         sqlpr.assign_rel(ep, reddit_m.RedditThread, thread_matches)
#         sqlpr.assign_rel(ep, guru_m.Guru, guru_matches)
#     if session.new:
#         session.commit()
