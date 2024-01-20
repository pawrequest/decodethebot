import asyncio
from asyncio import Queue
from contextlib import asynccontextmanager

from aiohttp import ClientSession
from asyncpraw.models import Subreddit
from dotenv import load_dotenv
from episode_scraper import PodGetter
from pawsupport import sqlmodel_support as psql
from pawsupport import backup_paw as psb
from pawsupport import async_support as psa
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
    logger,
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
        pod_getter: PodGetter,
        process_q: Queue = None,
        http_session: ClientSession = None,
    ):
        self.session = session
        self.pruner = pruner
        self.backup_bot = backup_bot
        self.subreddit = subreddit
        self.pod_getter = pod_getter
        self.process_q = process_q or Queue()
        self.http_session = http_session or ClientSession()
        self.tasks = list()

    @classmethod
    @asynccontextmanager
    async def context(cls, sub_name: str = SUBREDDIT_NAME, podcast_url: str = PODCAST_URL) -> "DTG":
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
                        pod_getter = PodGetter(podcast_url, http_session, ep_queue)

                        yield cls(
                            session=session,
                            pruner=pruner,
                            backup_bot=backup_bot,
                            subreddit=subreddit,
                            process_q=process_qu,
                            http_session=http_session,
                            pod_getter=pod_getter,
                        )
        finally:
            ...

    async def setup(self):
        logger.info("Initialised")
        with self.session as session:
            gurus_from_file(session, GURU_NAMES_FILE)

            if RESTORE_FROM_JSON:
                self.backup_bot.restore()
            if TRIM_DB:
                trim_db(self.session)
            # if INIT_EPS:
            #     tmp_q = Queue()
            #     asyncio.create_task(self.q_episodes()),
            #
            #     await init_eps_q(self.session, self.queue)

    async def run(self):
        try:
            self.tasks = [
                asyncio.create_task(
                    psb.backup_copy_prune(self.backup_bot, self.pruner, BACKUP_SLEEP)
                ),
                asyncio.create_task(self.pod_getter.run()),
                asyncio.create_task(self.q_episodes()),
                asyncio.create_task(self.q_threads()),
                asyncio.create_task(self.process_queue()),
            ]
            logger.info("Tasks created")
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
    async def q_episodes(self):
        try:
            while True:
                ep = await self.pod_getter.queue.get()
                episode = Episode.model_validate(ep)

                dupes = 0
                if psql.obj_in_session(self.session, episode, Episode):
                    if dupes > MAX_DUPES:
                        logger.debug(f"Found {dupes} duplicates, stopping")
                        break
                    dupes += 1
                    continue

                logger.debug(f"Queuing {episode.title}")
                await self.process_q.put(episode)
                self.pod_getter.queue.task_done()

        except Exception as e:
            logger.error(f"Error in q_episodes: {e}")
            raise e

        finally:
            logger.debug(f"Sleeping for {SCRAPER_SLEEP} seconds")
            await asyncio.sleep(SCRAPER_SLEEP)

    @psa.quiet_cancel_as
    async def q_threads(self):
        sub_stream = self.subreddit.stream.submissions(skip_existing=False)
        async for sub in sub_stream:
            try:
                thread = RedditThread.from_submission(sub)

                if psql.obj_in_session(self.session, thread, RedditThread):
                    continue

                await self.process_q.put(thread)
            except Exception as e:
                logger.error(f"Error getting thread from submission: {e}")
                raise e

    @psa.quiet_cancel_as
    async def process_queue(self):
        # clunky to allow ignore non-matching threads
        while True:
            try:
                instance = await self.process_q.get()
                matches_d = await psql.all_matches(self.session, instance, data_models())
                matches_n = sum([len(_) for _ in matches_d.values()])
                if isinstance(instance, RedditThread) and not matches_n:
                    logger.debug(f"No matches for {psql.instance_log_str(instance)}, skipping")
                    continue
                self.session.add(instance)
                await psql.assign_all(instance, matches_d)
                self.session.commit()
                logger.info(f"Committed {psql.instance_log_str(instance)} with {matches_n} matches")
                self.process_q.task_done()
            except Exception as e:
                logger.error(f"Error in process_queue: {e}")
                raise e


def gurus_from_file(session, infile):
    with open(infile, "r") as f:
        guru_names = f.read().split(",")
    session_gurus = session.exec(select(Guru.name)).all()
    if new_gurus := set(guru_names) - set(session_gurus):
        logger.info(f"Adding {len(new_gurus)} new gurus")
        gurus = [Guru(name=_) for _ in new_gurus]
        session.add_all(gurus)
        session.commit()


@psa.quiet_cancel_try_log_as
async def init_eps(session, queue: Queue):
    ep_i = 0
    max_eps = INIT_EPS
    logger.info("Initialising episodes")
    eps = []
    ep = await queue.get()
    ep = Episode.model_validate(ep)
    eps.append(ep)
    ep_i += 1
    if ep_i >= max_eps:
        return

    eps = sorted(eps, key=lambda _: _.date)
    for ep in eps:
        if psql.obj_in_session(session, ep, Episode):
            continue
        logger.info(f"Adding {ep.title}")
        session.add(ep)
        thread_matches = psql.db_obj_matches(session, ep, RedditThread)
        guru_matches = psql.db_obj_matches(session, ep, Guru)
        psql.assign_rel(ep, RedditThread, thread_matches)
        psql.assign_rel(ep, Guru, guru_matches)
    if session.new:
        session.commit()


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
                    pod_getter = PodGetter(podcast_url, http_session, ep_queue)

                    yield DTG(
                        session=session,
                        pruner=pruner,
                        backup_bot=backup_bot,
                        subreddit=subreddit,
                        process_q=process_qu,
                        http_session=http_session,
                        pod_getter=pod_getter,
                    )
    finally:
        ...