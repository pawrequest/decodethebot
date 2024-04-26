import asyncio
from asyncio import Queue, Task

import pydantic as _p
import sqlmodel as sqm
from aiohttp import ClientSession
from asyncpraw import Reddit
from asyncpraw.reddit import Subreddit
from dotenv import load_dotenv
from loguru import logger
from pydantic import alias_generators

# import suppawt.convert
from scrapaw import dtg, pod_abs
from sqlmodel import select
from suppawt import get_values, pawsync

from .core import database
from .dtg_types import DB_MODEL_TYPE, DB_MODEL_VAR
from .guru_config import GuruConfig, RedditConfig
from .models import episode_m, guru_m, reddit_m
from .models.reddit_m import RedditThread

load_dotenv()


class DTG:
    def __init__(
        self,
        guru_settings: GuruConfig | None = None,
        reddit_settings: RedditConfig | None = None,
    ):
        """Decoding The Gurus Bot

        Attributes:
            reddit_settings (RedditConfig): Reddit Configuration
            guru_settings (GuruConfig): Guru Configuration
        """
        self.r_settings = reddit_settings or RedditConfig()
        self.g_settings = guru_settings or GuruConfig()
        self.episode_q = Queue()
        self.reddit_q = Queue()
        self.tasks: list[Task] = list()
        self.reddit: Reddit | None = None
        self.subreddit: Subreddit | None = None
        self.http_session: ClientSession | None = None
        self.sqm_session: sqm.Session | None = None

    async def __aenter__(self):
        self.http_session = ClientSession()
        self.sqm_session = sqm.Session(database.engine_())
        self.reddit = Reddit(
            client_id=self.r_settings.client_id,
            client_secret=self.r_settings.client_secret,
            user_agent=self.r_settings.user_agent,
            redirect_uri=self.r_settings.redirect_uri,
            refresh_token=self.r_settings.refresh_token,
        )
        self.subreddit = await self.reddit.subreddit(self.r_settings.subreddit_name)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.reddit.close()
        self.sqm_session.close()
        await self.http_session.close()

    async def run(self):
        """Run the bot

        spawn queue managers and processors for episodes and reddit threads
        """
        logger.info('Initialised')
        with self.sqm_session as session:
            gurus_from_file(session, self.g_settings.guru_names_file)

            self.tasks = [
                asyncio.create_task(self.episode_q_manager()),
                asyncio.create_task(self.reddit_q_manager()),
                asyncio.create_task(
                    self.process_queue(
                        self.reddit_q,
                        reddit_m.RedditThread,
                        log_category='reddit',
                        relation_classes=[episode_m.Episode, guru_m.Guru],
                    )
                ),
                asyncio.create_task(
                    self.process_queue(
                        self.episode_q,
                        episode_m.Episode,
                        log_category='episode',
                        relation_classes=[reddit_m.RedditThread, guru_m.Guru],
                    )
                ),
            ]
            logger.info('Tasks created')

    @pawsync.quiet_cancel
    async def kill(self):
        """Kill the bot"""
        logger.info('Killing')
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks)

    @pawsync.quiet_cancel
    async def episode_q_manager(self):
        """Manage episode scraping"""
        while True:
            try:
                await self.get_episodes()
                logger.debug(
                    f'Episode manager sleeping for {self.g_settings.scraper_sleep} seconds', category='episode'
                )
            except pod_abs.MaxDupeError:
                logger.debug('Maximum Duplicate Episodes Reached', category='episode')
            except Exception as e:
                logger.exception(f'Error getting episodes: {e}', category='episode')
            await asyncio.sleep(self.g_settings.scraper_sleep)

    async def get_episodes(self, max_dupes: int = None):
        """Get episodes from the podcast feed and add them to the episode queue"""
        logger.debug('Getting Episodes', category='episode')
        max_dupes = max_dupes or self.g_settings.max_dupes
        dupes = 0
        ep_count = 0
        async for ep_ in dtg.get_episodes_blind(
            base_url=str(self.g_settings.podcast_url),
            session_h=self.http_session,
            limit=self.g_settings.episode_scrape_limit,
        ):
            ep = episode_m.Episode.model_validate(ep_)
            if ep.get_hash in [_.get_hash for _ in self.sqm_session.exec(select(episode_m.Episode)).all()]:
                dupes += 1
                if max_dupes and dupes > max_dupes:
                    logger.debug(f'Maximum duplicate episodes reached: {max_dupes}')
                    raise pod_abs.MaxDupeError('Max duplicate episodes reached')
                continue
            ep_count += 1
            logger.debug(f'Found Episode: {ep.title}', category='episode')
            await self.episode_q.put(ep)
        logger.debug(f'Episode Queue Empty after adding {ep_count} New Episodes', category='episode')

    @pawsync.quiet_cancel
    async def reddit_q_manager(self):
        """Manage Reddit Thread Scraping"""
        while True:
            try:
                await self.get_reddit_threads()
            except pod_abs.MaxDupeError:
                logger.debug(
                    'Maximum Duplicate Threads Reached',
                    category='reddit',
                )
            except Exception as e:
                logger.exception(f'Error getting Reddit Threads: {e}', category='reddit')

            logger.debug(f'RedditBot Sleeping for {self.g_settings.reddit_sleep} seconds', category='reddit')
            await asyncio.sleep(self.g_settings.reddit_sleep)

    async def get_reddit_threads(self, max_dupes: int = None) -> None:
        """Get Reddit Threads from the subreddit and add them to the reddit queue

        Args:
            max_dupes (int): Maximum number of duplicate threads to allow before sleeping
        """
        max_dupes = max_dupes or self.g_settings.max_dupes
        dupes = 0
        async for sub in self.subreddit.stream.submissions(skip_existing=False):
            thrd = reddit_m.RedditThread.from_submission(sub)
            if thrd.get_hash in [_.get_hash for _ in self.sqm_session.exec(select(RedditThread)).all()]:
                dupes += 1
                if max_dupes and dupes > max_dupes:
                    raise pod_abs.MaxDupeError(f'Max dupes reached: {max_dupes}')
                continue

            logger.info(f'Found Reddit Thread: {thrd.title}', category='reddit')
            await self.reddit_q.put(thrd)

    @pawsync.quiet_cancel
    async def process_queue(
        self,
        queue,
        model_class: type(_p.BaseModel),
        relation_classes: list[type(_p.BaseModel)],
        log_category: str = 'General',
    ):
        """Process items from the queue

        Args:
            queue (Queue): Queue to process
            model_class (type): Model class to validate
            relation_classes (list[type]): List of related classed to check for matches
            log_category (str): organise log entries into categories
        """
        while True:
            item_ = await queue.get()
            item = model_class.model_validate(item_)
            item_str = f'{item.__class__.__name__} - {get_values.title_or_name_val(item)}'
            logger.debug(f'Processing {item_str}', category=log_category)

            self.sqm_session.add(item)
            for relation_class in relation_classes:
                await self.assign_rel(item, relation_class)

            self.sqm_session.commit()
            self.sqm_session.refresh(item)
            queue.task_done()
            logger.info(f'Processed {item_str}', category=log_category)

    async def assign_rel(self, item, relation_class):
        """Add related items to the item"""
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
    #             f"Processing {episode.__class__.__name__} - {get_values.title_or_name_val(episode)}"
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
    #             f"Processing {thread.__class__.__name__} - {get_values.title_or_name_val(thread)}"
    #         )
    #         self.sqm_session.commit()
    #         self.reddit_q.task_done()


def db_obj_matches(session: sqm.Session, obj: DB_MODEL_TYPE, model: type(DB_MODEL_VAR)) -> list[DB_MODEL_VAR]:
    """Get matching objects from the database

    Args:
        session (sqlmodel.Session): Database session
        obj (DB_MODEL_TYPE): Object to match
        model (type): Model to match against

    Returns:
        list: List of matching objects

    """
    if isinstance(obj, model):
        return []
    db_objs = session.exec(sqm.select(model)).all()
    identifier = get_values.title_or_name_val(obj)
    obj_var = get_values.title_or_name_var(model)

    if matched_tag_models := [_ for _ in db_objs if one_in_other(_, obj_var, identifier)]:
        logger.debug(
            f"Found {len(matched_tag_models)} '{model.__name__}' {'match' if len(matched_tag_models) == 1 else 'matches'} for {obj.__class__.__name__} - {identifier}"
        )
    return matched_tag_models


def one_in_other(obj: DB_MODEL_VAR, obj_var: str, compare_val: str) -> bool:
    """Check if one string is in another

    Args:
        obj (DB_MODEL_VAR): Object to check
        obj_var (str): Attribute to check
        compare_val (str): Value to compare

    Returns:
        bool: True if one string is in the other
    """
    ob_low = getattr(obj, obj_var).lower()
    return ob_low in compare_val.lower() or compare_val.lower() in ob_low


def gurus_from_file(session, infile):
    """Add gurus from a file to the database"""
    with open(infile) as f:
        guru_names = f.read().split(',')
    session_gurus = session.exec(sqm.select(guru_m.Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f'Adding {len(new_gurus)} new gurus')
        gurus = [guru_m.Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()


# @lru_cache
# def model_map_():
#     return {suppawt.convert.snake_name(_): _ for _ in ALL_MODELS}

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
