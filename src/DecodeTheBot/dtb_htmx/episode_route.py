import typing as _t
from pathlib import Path

import fastapi
import sqlmodel
from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from suppawt.pawlogger.config_loguru import logger

from DecodeTheBot.core.database import get_session
from DecodeTheBot.models import episode_m, guru_m, reddit_m  # noqa F401

SearchKind = _t.Literal['title', 'guru', 'notes']
# app = FastAPI()
router = fastapi.APIRouter()
# app.mount('/static', StaticFiles(directory='static'), name='static')
THIS_DIR = Path(__file__).resolve().parent
template_dir = THIS_DIR.parent / 'ui/templates'
print('TEMPLATE DIR', template_dir)
templates = Jinja2Templates(directory=str(template_dir))


# @app.get("/get_all/", response_class=HTMLResponse)
# async def get_all(request: Request):
#     return templates.TemplateResponse(
#         request=request, name="episode_rows.html",
#         context={'episodes': episodes}
#     )


def episode_matches(episodes, search_str, search_kind: SearchKind = 'title'):
    match search_kind:
        case 'title':
            matched_ = [ep for ep in episodes if search_str.lower() in ep.title.lower()]
        case 'guru':
            matched_ = [ep for ep in episodes if any(search_str.lower() in guru.name.lower() for guru in ep.gurus)]
        case 'notes':
            matched_ = [ep for ep in episodes for note in ep.notes if search_str.lower() in note.lower()]
        case _:
            raise ValueError(f'Invalid kind: {search_kind}')
    return sorted(matched_, key=lambda ep: ep.date, reverse=True)


def episode_matches2(session, search_str, search_kind: SearchKind = 'title'):
    match search_kind:
        case 'title':
            statement = select(episode_m.Episode).where(search_str.lower() in episode_m.Episode.title.lower())
        case 'guru':
            statement = select(episode_m.Episode).where(
                search_str.lower() in any([_.name for _ in episode_m.Episode.gurus])
            )
        case 'notes':
            statement = select(episode_m.Episode).where(search_str.lower() in any([_ for _ in episode_m.Episode.notes]))
        case _:
            raise ValueError(f'Invalid kind: {search_kind}')

    matched_ = session.exec(statement).all()
    return sorted(matched_, key=lambda ep: ep.date, reverse=True)


@router.get('/get_eps/', response_class=HTMLResponse)
async def get_ep_cards(request: Request, session: sqlmodel.Session = fastapi.Depends(get_session)):
    episodes = await from_sesh(episode_m.Episode, session)
    episodes = sorted(episodes, key=lambda ep: ep.date, reverse=True)

    return templates.TemplateResponse(
        request=request, name='episode/episode_cards.html', context={'episodes': episodes}
    )


@router.post('/get_eps/', response_class=HTMLResponse)
async def search_eps(
    request: Request,
    search_kind: SearchKind = Form(...),
    search_str: str = Form(...),
    session: sqlmodel.Session = fastapi.Depends(get_session),
):
    episodes = await from_sesh(episode_m.Episode, session)
    if search_kind and search_str:
        matched_episodes = episode_matches(episodes, search_str, search_kind)
    else:
        matched_episodes = episodes

    matched_episodes = sorted(matched_episodes, key=lambda ep: ep.date, reverse=True)

    return templates.TemplateResponse(
        request=request, name='episode/episode_cards.html', context={'episodes': matched_episodes}
    )


@router.get('/{ep_id}/', response_class=HTMLResponse)
async def read_episode(ep_id: int, request: Request, sesssion: sqlmodel.Session = fastapi.Depends(get_session)):
    episode = sesssion.get(episode_m.Episode, ep_id)
    return templates.TemplateResponse(request=request, name='episode/episode_detail.html', context={'episode': episode})


@router.get('/', response_class=HTMLResponse)
async def all_eps(request: Request, session=fastapi.Depends(get_session)):
    logger.debug('all_eps')
    episodes = await from_sesh(episode_m.Episode, session)
    episodes = sorted(episodes, key=lambda ep: ep.date, reverse=True)
    return templates.TemplateResponse(
        request=request, name='episode/episode_index.html', context={'episodes': episodes}
    )


async def from_sesh(clz, session: sqlmodel.Session):
    return session.exec(sqlmodel.select(clz)).all()
