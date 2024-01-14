import asyncio
import sys
from contextlib import asynccontextmanager
from functools import lru_cache

from aiohttp import ClientSession
from dotenv import load_dotenv
from fastapi import FastAPI
from fastui import prebuilt_html
from fastui.dev import dev_fastapi_app
from pawsupport import Pruner, SQLModelBot
from redditbot import subreddit_cm
from sqlmodel import Session
from fastapi.responses import HTMLResponse, PlainTextResponse

from .core.consts import BACKUP_DIR, BACKUP_JSON, BACKUP_SLEEP, RESTORE_FROM_JSON, SUBREDDIT_NAME, \
    logger, GURU_NAMES_FILE
from .core.database import create_db, engine_
from .routers.eps import router as eps_router
from .routers.guroute import router as guru_router
from .routers.main import router as main_router
from .routers.red import router as red_router
from .routers.forms import router as forms_router
from .tasks import restore_with_gurus, backup_and_prune, scraper_tasks, monitor_tasks, \
    gurus_from_file

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    try:
        create_db()
        logger.info("tables created", bot_name="BOOT")
        with Session(engine_()) as session:

            backup_bot = SQLModelBot(session, json_map_(), BACKUP_JSON, output_dir=BACKUP_DIR)
            pruner = Pruner(backup_target=BACKUP_JSON, output_dir=BACKUP_DIR)

            if RESTORE_FROM_JSON:
                gurus_from_file(session, GURU_NAMES_FILE)
                # backup_bot.restore()
            tasks.append(asyncio.create_task(backup_and_prune(backup_bot, pruner, BACKUP_SLEEP)))

            async with ClientSession() as aio_session:
                tasks.extend(await scraper_tasks(aio_session, session))
                async with subreddit_cm(sub_name=SUBREDDIT_NAME) as subreddit:  # noqa E1120
                    tasks.extend(await monitor_tasks(session, subreddit))

                    yield
                    logger.info('exit backup')

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
