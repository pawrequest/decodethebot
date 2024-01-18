import asyncio
import sys
from contextlib import asynccontextmanager

from aiohttp import ClientSession
from dotenv import load_dotenv
from episode_scraper.soups_dc import PodcastSoup
from fastapi import FastAPI
from fastui import prebuilt_html
from fastui.dev import dev_fastapi_app
from pawsupport import Pruner, SQLModelBot
from redditbot import subreddit_cm
from sqlmodel import Session
from fastapi.responses import HTMLResponse, PlainTextResponse

from .core.consts import BACKUP_DIR, BACKUP_JSON, PODCAST_URL, SUBREDDIT_NAME, logger
from .core.database import create_db, engine_
from .routers.eps import router as eps_router
from .routers.guroute import router as guru_router
from .routers.main import router as main_router
from .routers.red import router as red_router
from .routers.forms import router as forms_router
from .tasks import DTGBot, json_map_

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    process_qu = asyncio.Queue()
    try:
        create_db()
        logger.info("tables created")

        with Session(engine_()) as session:
            async with ClientSession() as http_session:
                async with subreddit_cm(sub_name=SUBREDDIT_NAME) as subreddit:  # noqa E1120 pycharm bug reported
                    backup_bot = SQLModelBot(
                        session, json_map_(), BACKUP_JSON, output_dir=BACKUP_DIR
                    )

                    pruner = Pruner(backup_target=BACKUP_JSON, output_dir=BACKUP_DIR)
                    # episode_bot = await EpisodeBotDC.from_url(PODCAST_URL, process_qu, http_session)
                    podcast_soup = await PodcastSoup.from_url(PODCAST_URL, http_session, process_qu)

                    dtg_bot = DTGBot(
                        session=session,
                        pruner=pruner,
                        backup_bot=backup_bot,
                        subreddit=subreddit,
                        queue=process_qu,
                        http_session=http_session,
                        podcast_soup=podcast_soup,
                    )
                    tasks.append(asyncio.create_task(dtg_bot.run()))

                    yield
                    await dtg_bot.kill()

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
