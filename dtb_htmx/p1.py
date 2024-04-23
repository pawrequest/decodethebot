import shelve
import typing as _t

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import responses

from DecodeTheBot.models.guru_m import Guru

IN_DB_TYPE = _t.Literal['title', 'guru', 'notes']
app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')

templates = Jinja2Templates(directory='templates')

with shelve.open(r'C:\Users\RYZEN\prdev\workbench\dtg_bot.shelf') as shelf:
    episodes = shelf.get('episode')
    gurus = shelf.get('guru')
episodes = sorted(episodes, key=lambda x: x.date, reverse=True)
gurus = sorted(gurus, key=lambda x: x.id)


def episode_matches(search_str, search_kind: IN_DB_TYPE = 'title'):
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
    return matched_


@app.get('/get_eps/', response_class=HTMLResponse)
async def get_eps(request: Request):
    return templates.TemplateResponse(
        request=request, name='episode_cards.html',
        context={'episodes': episodes}
    )


@app.post('/get_eps/', response_class=HTMLResponse)
async def search_eps(
        request: Request,
        search_kind: IN_DB_TYPE = Form(...),
        search_str: str = Form(...)
):
    if search_kind and search_str:
        matched_episodes = episode_matches(search_str, search_kind)
    else:
        matched_episodes = episodes

    return templates.TemplateResponse(
        request=request, name='episode_cards.html',
        context={'episodes': matched_episodes}
    )


@app.post('/guru/edit/{guru_id}/', response_class=HTMLResponse)
async def edit_guru(
        guru_id: int,
        guru: Guru,
        request: Request,
):
    return templates.TemplateResponse(
        request=request, name='guru_edit.html',
        context={'guru': gurus[guru_id - 1]}
    )


@app.get('/eps/{ep_id}/', response_class=HTMLResponse)
async def read_episode(ep_id: int, request: Request):
    return templates.TemplateResponse(
        request=request, name='episode_detail.html',
        context={'episode': episodes[ep_id - 1]}
    )


@app.get('/guru/{guru_id}/', response_class=HTMLResponse)
async def read_guru(guru_id: int, request: Request):
    return templates.TemplateResponse(
        request=request, name='guru_detail.html',
        context={'guru': gurus[guru_id - 1]}
    )


@app.get('/eps/', response_class=HTMLResponse)
async def all_eps(request: Request):
    return templates.TemplateResponse(
        request=request, name='main.html',
        context={'episodes': episodes}
    )


#
# @app.get("/eps/", response_class=HTMLResponse)
# async def all_eps(request: Request):
#     return templates.TemplateResponse(
#         request=request, name="main.html",
#         context={'episodes': episodes}
#     )


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return responses.RedirectResponse(url='/eps/')

    # return templates.TemplateResponse(
    #     request=request, name="main.html",
    #     context={'episodes': episodes}
    # )
