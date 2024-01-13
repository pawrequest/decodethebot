import asyncio
import os
import sys
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from aiohttp import ClientSession
from dotenv import load_dotenv
from episode_scraper.episode_bot import EpisodeBot
from fastapi import FastAPI
from fastui import prebuilt_html
from fastui.dev import dev_fastapi_app
from pawsupport.backup_paw import Pruner, SQLModelBot
from pawsupport.logger_paw.logger_config_loguru import get_logger
from redditbot import SubredditMonitor
from redditbot.managers import subreddit_cm
from sqlmodel import Session
from fastapi.responses import PlainTextResponse, HTMLResponse

from .core.database import create_db, engine_
from .models.episode_ext import Episode
from .models.guru import Guru
from .models.reddit_ext import RedditThread as RedditThread
logger = get_logger('/data/logs/guru_log.log', 'local')
load_dotenv()
SUBREDDIT_NAME = os.environ.get("SUBREDDIT_NAME", "test")
BACKUP_SLEEP = os.environ.get('BACKUP_SLEEP', 60 * 60 * 24)
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "backups"))
RESTORE_FROM_JSON = os.environ.get("RESTORE_FROM_JSON", False)
BACKUP_JSON = Path(os.environ.get("BACKUP_JSON", BACKUP_DIR / "guru_backup.json"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # logger.info(f"Loading with params: {param_log_strs()}", bot_name="BOOT")
    tasks = []
    try:
        create_db()
        logger.info("tables created", bot_name="BOOT")
        with Session(engine_()) as session:

            backup_bot = SQLModelBot(session, json_map_(), BACKUP_JSON, output_dir=BACKUP_DIR)
            pruner = Pruner(backup_target=BACKUP_JSON, output_dir=BACKUP_DIR)

            if RESTORE_FROM_JSON:
                backup_bot.restore()
            tasks.append(asyncio.create_task(backup_and_prune(backup_bot, pruner, BACKUP_SLEEP)))

            async with ClientSession() as aio_session:
                episode_q = asyncio.Queue()
                pod_url = os.environ.get("PODCAST_URL")
                ep_bot = await EpisodeBot.from_url(pod_url, session, aio_session,
                                                   episode_db_type=Episode)
                tasks.append(asyncio.create_task(ep_bot.run_q(episode_q)))
                tasks.append(asyncio.create_task(process_episodes(episode_q)))

                async with subreddit_cm(sub_name=SUBREDDIT_NAME) as subreddit:  # noqa E1120
                    thread_q = asyncio.Queue()
                    monitor_bot = SubredditMonitor(subreddit=subreddit,
                                                   session=session,
                                                   match_model=Guru,
                                                   thread_db_type=RedditThread,
                                                   )
                    tasks.append(asyncio.create_task(monitor_bot.run_q(thread_q)))
                    tasks.append(asyncio.create_task(process_threads(thread_q)))

                    yield

                    await backup_bot.backup()

    finally:
        logger.info("Shutting down")
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)


frontend_reload = "--reload" in sys.argv
if frontend_reload:
    app = dev_fastapi_app(lifespan=lifespan)
else:
    app = FastAPI(lifespan=lifespan)

from .routers.eps import router as eps_router
from .routers.guroute import router as guru_router
from .routers.main import router as main_router
from .routers.red import router as red_router
from .routers.forms import router as forms_router

app.include_router(forms_router, prefix="/api/forms")
app.include_router(eps_router, prefix="/api/eps")
app.include_router(guru_router, prefix="/api/guru")
app.include_router(red_router, prefix="/api/red")

app.include_router(main_router, prefix="/api")


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt() -> str:
    return "User-agent: *\nAllow: /"


@app.get("/favicon.ico", status_code=404, response_class=PlainTextResponse)
async def favicon_ico() -> str:
    return "page not found"


@app.get("/{path:path}")
async def html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title="DecodeTheBot"))


@lru_cache()
def json_map_():
    from .core.json_map import JSON_NAMES_TO_MODEL_MAP
    return JSON_NAMES_TO_MODEL_MAP
    # from DecodeTheBot.models.episode_ext import Episode
    # from DecodeTheBot.models.guru import Guru
    # from DecodeTheBot.models.links import GuruEpisodeLink, RedditThreadEpisodeLink, \
    #     RedditThreadGuruLink
    # from DecodeTheBot.models.reddit_ext import RedditThread
    # return {
    #     "episode": Episode,
    #     "guru": Guru,
    #     "reddit_thread": RedditThread,
    #     "guru_ep_link": GuruEpisodeLink,
    #     "reddit_thread_episode_link": RedditThreadEpisodeLink,
    #     "reddit_thread_guru_link": RedditThreadGuruLink,
    # }


async def process_episodes(queue: asyncio.Queue):
    while True:
        result = await queue.get()
        print(result.title)
        queue.task_done()


async def process_threads(queue: asyncio.Queue):
    while True:
        result = await queue.get()
        print(result.title)
        queue.task_done()


async def backup_and_prune(backupbot: SQLModelBot, pruner: Pruner, backup_sleep):
    while True:
        await asyncio.sleep(backup_sleep)
        await backupbot.backup()
        pruner.copy_and_prune()
