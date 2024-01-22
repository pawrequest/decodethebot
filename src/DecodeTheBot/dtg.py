import asyncio
from asyncio import Queue
from contextlib import asynccontextmanager

from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
from episode_scraper import DTGScraper, ScraperGeneral
from loguru import logger
from pawsupport import async_ps as psa
from pawsupport import backup_ps as psb
from pawsupport.sqlmodel_ps import sqlm as psql
from pawsupport import misc_ps as psm
from redditbot import subreddit_cm
from sqlmodel import Session, select

from .core.consts import (
    BACKUP_DIR,
    BACKUP_JSON,
    BACKUP_SLEEP,
    GURU_NAMES_FILE,
    INIT_EPS,
    MAX_DUPES,
    PODCAST_URL,
    RESTORE_FROM_JSON,
    SCRAPER_SLEEP,
    SUBREDDIT_NAME,
    TRIM_DB,
)
from .core.database import engine_, trim_db
from .models.episode import Episode
from .models.guru import Guru
from .models.reddit_thread import RedditThread
from DecodeTheBot.core.types import ALL_MODEL, data_models

load_dotenv()


class DTG(object):
    def __init__(
        self,
        session: Session,
        pruner: psb.Pruner,
        backup_bot: psb.SQLModelBot,
        subreddit: Subreddit,
        scraper: DTGScraper,
        process_q: Queue = None,
        http_session: ClientSession = None,
    ):
        self.session = session
        self.pruner = pruner
        self.backup_bot = backup_bot
        self.subreddit = subreddit
        self.scraper = scraper
        self.process_q = process_q or Queue()
        self.http_session = http_session or ClientSession()
        self.tasks = list()

    async def setup(self):
        with self.session as session:
            gurus_from_file(session, GURU_NAMES_FILE)

            if RESTORE_FROM_JSON:
                self.backup_bot.restore()
            if TRIM_DB:
                trim_db(self.session)
            if INIT_EPS:
                await init_eps(self.session, self.scraper)

    async def run(self):
        try:
            self.tasks = [
                asyncio.create_task(
                    psb.backup_copy_prune(self.backup_bot, self.pruner, BACKUP_SLEEP)
                ),
                asyncio.create_task(self.scraper.run()),
                asyncio.create_task(self.q_episodes()),
                asyncio.create_task(self.q_threads()),
                asyncio.create_task(self.process_queue()),
            ]
            logger.info("Tasks created", category="BOOT")
        except Exception as e:
            logger.error(f"Error in run: {e}")
            raise e

    async def kill(self):
        logger.info("Killing")
        await self.backup_bot.backup()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks)

    @psa.quiet_cancel_as
    async def q_episodes(self, max_dupes=MAX_DUPES):
        try:
            dupes = 0
            while True:
                if dupes >= max_dupes:
                    await self.sleep_ep_q()
                    dupes = 0

                episode = await self.get_val_ep()

                if psql.obj_in_session(self.session, episode, Episode):
                    logger.debug(f"Duplicate Episode {episode.title}", category="EP_Q")
                    dupes += 1
                else:
                    await self.q_ep(episode)
                    dupes = 0
                self.scraper.queue.task_done()

        except Exception as e:
            logger.error(f"Error in q_episodes: {e}", category="EP_Q")
            raise e

    async def q_ep(self, episode):
        logger.debug(f"Queuing {episode.title}", category="EP_Q")
        await self.process_q.put(episode)

    async def sleep_ep_q(self):
        self.scraper.queue = Queue()
        logger.debug(
            f"Found {MAX_DUPES} duplicates, Sleeping for {SCRAPER_SLEEP} seconds", category="EP_Q"
        )
        await asyncio.sleep(SCRAPER_SLEEP)

    async def get_val_ep(self):
        ep = await self.scraper.queue.get()
        episode = Episode.model_validate(ep)
        return episode

    @psa.quiet_cancel_as
    async def q_threads(self):
        sub_stream = self.subreddit.stream.submissions(skip_existing=False)
        async for sub in sub_stream:
            try:
                thread = RedditThread.from_submission(sub)
                if not psql.obj_in_session(self.session, thread, RedditThread):
                    await self.process_q.put(thread)
            except Exception as e:
                logger.error(f"Error getting thread from submission: {e}", category="THREAD_Q")
                raise e

    @psa.quiet_cancel_as
    async def process_queue(self):
        # clunky to allow skip non-matching threads
        while True:
            try:
                instance = await self.process_q.get()
                matches_d = await psql.all_matches(self.session, instance, data_models())
                matches_n = sum([len(_) for _ in matches_d.values()])
                if isinstance(instance, RedditThread) and not matches_n:
                    continue
                self.session.add(instance)
                await psql.assign_all(instance, matches_d)
                self.session.commit()
                logger.info(
                    f"Committed {psm.instance_log_str(instance)} with {matches_n} matches",
                    category="DB",
                )
                self.process_q.task_done()
            except Exception as e:
                logger.error(f"Error in process_queue: {e}")
                raise e


@asynccontextmanager
async def dtg_context(sub_name: str = SUBREDDIT_NAME, podcast_url: str = PODCAST_URL) -> "DTG":
    try:
        process_qu = asyncio.Queue()
        ep_queue = asyncio.Queue()

        with Session(engine_()) as session:
            async with ClientSession() as http_session:
                async with subreddit_cm(sub_name=sub_name) as subreddit:  # noqa E1120 pycharm bug reported
                    backup_bot = psb.SQLModelBot(
                        session, psql.model_map_(ALL_MODEL), BACKUP_JSON, output_dir=BACKUP_DIR
                    )
                    pruner = psb.Pruner(backup_target=BACKUP_JSON, output_dir=BACKUP_DIR)
                    scraper = DTGScraper(podcast_url, http_session, ep_queue)

                    yield DTG(
                        session=session,
                        pruner=pruner,
                        backup_bot=backup_bot,
                        subreddit=subreddit,
                        process_q=process_qu,
                        http_session=http_session,
                        scraper=scraper,
                    )
    finally:
        ...


async def init_eps(session: Session, scraper: ScraperGeneral):
    logger.info("Initialising episodes")
    eps = [_ async for _ in scraper.get_some_eps(limit=INIT_EPS)]
    eps = sorted(eps, key=lambda _: _.date)
    for ep in eps:
        ep = Episode.model_validate(ep)
        if psql.obj_in_session(session, ep, Episode):
            continue
        session.add(ep)
        thread_matches = psql.db_obj_matches(session, ep, RedditThread)
        guru_matches = psql.db_obj_matches(session, ep, Guru)
        psql.assign_rel(ep, RedditThread, thread_matches)
        psql.assign_rel(ep, Guru, guru_matches)
        session.commit()
        logger.info(f"Committed {ep.title}")


def gurus_from_file(session, infile):
    with open(infile, "r") as f:
        guru_names = f.read().split(",")
    session_gurus = session.exec(select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()
