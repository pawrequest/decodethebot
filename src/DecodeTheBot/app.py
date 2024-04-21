import asyncio
import sys
from contextlib import asynccontextmanager
import shelve

import sqlmodel
from fastapi import FastAPI
from fastui import prebuilt_html
from fastui.dev import dev_fastapi_app
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import dtg_types
from .core import database
from .core.consts import logger
from .routers.eps import router as eps_router
from .routers.guroute import router as guru_router
from .routers.main import router as main_router
from .routers.red import router as red_router
from .routers.forms import router as forms_router
from .dtg_bot import DTG

DTG_SHELF = r'C:\Users\RYZEN\prdev\workbench\dtg_bot.shelf'


#
# envloc = os.environ.get('GURU_ENV')
# load_dotenv(envloc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # noinspection PyArgumentList
    async with DTG.from_env() as dtg:
        try:
            database.create_db()
            with sqlmodel.Session(database.engine_()) as session:
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
    with sqlmodel.Session(database.engine_()) as session:
        with shelve.open(DTG_SHELF) as shelf:
            for model_name, mapping in dtg_types.models_map.items():
                result = session.exec(sqlmodel.select(mapping.db_model))
                outputs = [mapping.output.model_validate(_, from_attributes=True) for _ in
                           result.all()]
                shelf[model_name] = outputs
    logger.info(f'DB shelved to {DTG_SHELF}')


# async def shelf_db():
#     session = database.get_session()
#     with shelve.open("dtg_bot.shelf") as shelf:
#         for model in dtg_types.DB_MODELS:
#             shelf[model.__name__] = session.exec(sqlmodel.select(model)).all()
#     logger.info("db shelved")


frontend_reload = '--reload' in sys.argv
if frontend_reload:
    app = dev_fastapi_app(lifespan=lifespan)
else:
    app = FastAPI(lifespan=lifespan)

app.include_router(forms_router, prefix='/api/forms')
app.include_router(eps_router, prefix='/api/eps')
app.include_router(guru_router, prefix='/api/guru')
app.include_router(red_router, prefix='/api/red')

app.include_router(main_router, prefix='/api')


@app.get('/robots.txt', response_class=PlainTextResponse)
async def robots_txt() -> str:
    return 'User-agent: *\nAllow: /'


@app.get('/favicon.ico', status_code=404, response_class=PlainTextResponse)
async def favicon_ico() -> str:
    return 'page not found'


@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title='DecodeTheBot'))
