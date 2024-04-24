import asyncio
from contextlib import asynccontextmanager
import shelve
from pathlib import Path

import sqlmodel
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from loguru import logger
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from . import dtg_types
from .core import database
from .guru_config import GuruConfig, guru_settings
from .dtb_htmx.episode_route import router as ep_router
from .dtb_htmx.guru_route import router as guru_router
from .dtg_bot import DTG

THIS_DIR = Path(__file__).resolve().parent


def db_from_shelf(session: sqlmodel.Session, settings: GuruConfig = guru_settings()):
    with shelve.open(str(settings.guru_shelf)) as shelf:
        episodes = shelf.get('episode')
        gurus = shelf.get('guru')
    episodes = sorted(episodes, key=lambda x: x.date, reverse=True)
    gurus = sorted(gurus, key=lambda x: x.id)
    session.add_all(episodes)
    session.add_all(gurus)
    session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # noinspection PyArgumentList
    async with DTG() as dtg:
        try:
            database.create_db()

            with sqlmodel.Session(database.engine_()) as session:
                if dtg.g_settings.restore_from_shelf:
                    db_from_shelf(session)
                if dtg.g_settings.trim_db:
                    database.trim_db(session)
            logger.info('tables created')
            main_task = asyncio.create_task(dtg.run())
            yield

        finally:
            await shelf_db()
            await dtg.kill()
            main_task.cancel()
            await main_task


async def shelf_db():
    g_sett = guru_settings()
    with sqlmodel.Session(database.engine_()) as session:
        with shelve.open(g_sett.guru_shelf) as shelf:
            for model_name, mapping in dtg_types.models_map.items():
                result = session.exec(sqlmodel.select(mapping.db_model))
                outputs = [mapping.output.model_validate(_, from_attributes=True) for _ in result.all()]
                shelf[model_name] = outputs
    logger.info(f'DB shelved to {g_sett.guru_shelf}')


# async def shelf_db():
#     session = database.get_session()
#     with shelve.open("dtg_bot.shelf") as shelf:
#         for model in dtg_types.DB_MODELS:
#             shelf[model.__name__] = session.exec(sqlmodel.select(model)).all()
#     logger.info("db shelved")


app = FastAPI(lifespan=lifespan)
app.mount('/static', StaticFiles(directory=THIS_DIR / 'ui/static'), name='static')
templates = Jinja2Templates(directory='/ui/templates')

app.include_router(ep_router, prefix='/eps')
app.include_router(guru_router, prefix='/guru')


@app.get('/robots.txt', response_class=PlainTextResponse)
async def robots_txt() -> str:
    return 'User-agent: *\nAllow: /'


@app.get('/favicon.ico', status_code=404, response_class=PlainTextResponse)
async def favicon_ico() -> str:
    return 'page not found'


@app.get('/', response_class=HTMLResponse)
async def index():
    logger.info('index')
    return RedirectResponse(url='/eps/')
