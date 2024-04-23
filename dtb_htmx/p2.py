import os
import typing as _t

import fastapi
import sqlmodel
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import responses
from dotenv import load_dotenv

from DecodeTheBot.core.database import get_session
from DecodeTheBot.models import episode_m, guru_m, reddit_m  # noqa F401
from suppawt.pawlogger.config_loguru import logger

envloc = os.environ.get('GURU_ENV')
load_dotenv(envloc)
# load_dotenv(r'C:\Users\RYZEN\prdev\workbench\.env')
IN_DB_TYPE = _t.Literal['title', 'guru', 'notes']
app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')

templates = Jinja2Templates(directory='templates')


# @app.get("/get_all/", response_class=HTMLResponse)
# async def get_all(request: Request):
#     return templates.TemplateResponse(
#         request=request, name="episode_rows.html",
#         context={'episodes': episodes}
#     )


def episode_matches(episodes, search_str, search_kind: IN_DB_TYPE = 'title'):
    match search_kind:
        case 'title':
            matched_ = [ep for ep in episodes if search_str.lower() in ep.title.lower()]
        case 'guru':
            matched_ = [
                ep for ep in episodes if
                any(search_str.lower() in guru.name.lower() for guru in ep.gurus)
            ]
        case 'notes':
            matched_ = [
                ep for ep in episodes
                for note in ep.notes
                if search_str.lower() in note.lower()
            ]
        case _:
            raise ValueError(f'Invalid kind: {search_kind}')
    return sorted(matched_, key=lambda ep: ep.date, reverse=True)


@app.get('/get_eps/', response_class=HTMLResponse)
async def get_eps(
        request: Request,
        session: sqlmodel.Session = fastapi.Depends(get_session)
):
    episodes = await from_sesh(episode_m.Episode, session)
    episodes = sorted(episodes, key=lambda ep: ep.date, reverse=True)

    return templates.TemplateResponse(
        request=request, name='episode_cards.html',
        context={'episodes': episodes}
    )


@app.post('/get_eps/', response_class=HTMLResponse)
async def search_eps(
        request: Request,
        search_kind: IN_DB_TYPE = Form(...),
        search_str: str = Form(...),
        session: sqlmodel.Session = fastapi.Depends(get_session)

):
    episodes = await from_sesh(episode_m.Episode, session)

    if search_kind and search_str:
        matched_episodes = episode_matches(episodes, search_str, search_kind)
    else:
        matched_episodes = episodes

    matched_episodes = sorted(matched_episodes, key=lambda ep: ep.date, reverse=True)

    return templates.TemplateResponse(
        request=request, name='episode_cards.html',
        context={'episodes': matched_episodes}
    )


@app.get('/eps/{ep_id}/', response_class=HTMLResponse)
async def read_episode(
        ep_id: int,
        request: Request,
        sesssion: sqlmodel.Session = fastapi.Depends(get_session)
):
    episode = sesssion.get(episode_m.Episode, ep_id)
    return templates.TemplateResponse(
        request=request, name='episode_detail.html',
        context={'episode': episode}
    )


@app.get('/guru/{guru_id}/', response_class=HTMLResponse)
async def read_guru(
        guru_id: int,
        request: Request,
        sesssion: sqlmodel.Session = fastapi.Depends(get_session)
):
    guru = sesssion.get(guru_m.Guru, guru_id)

    return templates.TemplateResponse(
        request=request, name='guru_detail.html',
        context={'guru': guru}
    )


@app.post('/guru/{guru_id}/', response_class=HTMLResponse)
async def post_guru(
        guru_id: int,
        request: Request,
        sesssion: sqlmodel.Session = fastapi.Depends(get_session)
):
    guru = sesssion.get(guru_m.Guru, guru_id)

    return templates.TemplateResponse(
        request=request, name='guru_edit.html',
        context={'guru': guru}
    )


@app.get('/eps/', response_class=HTMLResponse)
async def all_eps(request: Request, session=fastapi.Depends(get_session)):
    episodes = await from_sesh(episode_m.Episode, session)
    episodes = sorted(episodes, key=lambda ep: ep.date, reverse=True)
    return templates.TemplateResponse(
        request=request, name='main.html',
        context={'episodes': episodes}
    )


@app.get('/', response_class=HTMLResponse)
async def index():
    logger.info('index')
    return responses.RedirectResponse(url='/eps/')


async def from_sesh(clz, session: sqlmodel.Session):
    return session.exec(sqlmodel.select(clz)).all()
