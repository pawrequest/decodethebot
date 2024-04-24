# from __future__ import annotations
import sqlmodel
from fastui import AnyComponent, FastUI, components as c
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from loguru import logger
from pawdantic.pawui import builders

import DecodeTheBot.ui.dtg_ui
from DecodeTheBot.guru_config import guru_settings
from DecodeTheBot.models import responses
from DecodeTheBot.core.database import get_session
from DecodeTheBot.models.episode_m import Episode
from DecodeTheBot.models.guru_m import Guru
from DecodeTheBot.routers.guroute import guru_filter
from DecodeTheBot.ui.dtg_ui import dtg_default_page

router = APIRouter()


# FastUI
@router.get('/{ep_id}', response_model=FastUI, response_model_exclude_none=True)
async def episode_view(ep_id: int, session: Session = Depends(get_session)) -> list[AnyComponent]:
    episode_ = session.get(Episode, ep_id)
    episode = responses.EpisodeOut.model_validate(episode_, from_attributes=True)
    return dtg_default_page(
        components=[
            builders.back_link(),
            DecodeTheBot.ui.dtg_ui.episode_detail(episode) if episode else c.Text(text='Episode not found'),
        ],
        title=episode.title,
    )


@router.get('/', response_model=FastUI, response_model_exclude_none=True)
def episode_list_view(
    page: int = 1, guru_name: str | None = None, session: Session = Depends(get_session)
) -> list[AnyComponent]:
    g_sett = guru_settings()
    page_size = g_sett.page_size
    logger.info('episode_filter')
    episodes_, filter_form_initial = guru_filter_init(guru_name, session, Episode)
    episodes = [responses.EpisodeOut.model_validate(_, from_attributes=True) for _ in episodes_]
    episodes.sort(key=lambda x: x.date, reverse=True)

    total = len(episodes)
    episodes = episodes[(page - 1) * page_size : page * page_size]
    episode_rows = [DecodeTheBot.ui.dtg_ui.episode_row(episode) for episode in episodes]

    return dtg_default_page(
        title='Episodes',
        components=[
            guru_filter(filter_form_initial, 'episodes'),
            *episode_rows,
            c.Pagination(page=page, page_size=page_size, total=total),
        ],
    )


def guru_filter_init(
    guru_name: str, session: sqlmodel.Session, clazz: type[sqlmodel.SQLModel]
) -> tuple[list[sqlmodel.SQLModel], dict]:
    filter_form_initial = {}
    if guru_name:
        guru = session.exec(select(Guru).where(Guru.name == guru_name)).one()
        # data = guru.episodes
        statement = select(clazz).where(clazz.gurus.any(Guru.id == guru.id))
        data = session.exec(statement).all()
        filter_form_initial['guru'] = {'value': guru_name, 'label': guru.name}
    else:
        data = session.query(clazz).all()
    return data, filter_form_initial
