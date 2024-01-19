import asyncio
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastui import prebuilt_html
from fastui.dev import dev_fastapi_app
from fastapi.responses import HTMLResponse, PlainTextResponse

from .core.consts import logger
from .core.database import create_db
from .routers.eps import router as eps_router
from .routers.guroute import router as guru_router
from .routers.main import router as main_router
from .routers.red import router as red_router
from .routers.forms import router as forms_router
from .dtg_bot import DTG

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with DTG.minimum_context() as dtg:  # noqa E1120 pycharm bug reported
        try:
            create_db()
            logger.info("tables created")
            main_task = asyncio.create_task(dtg.run())
            yield

        finally:
            await dtg.kill()
            main_task.cancel()
            await asyncio.gather(main_task)


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
