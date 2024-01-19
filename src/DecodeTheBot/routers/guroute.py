from typing import Literal

from fastui import AnyComponent, FastUI, components as c
from fastapi import APIRouter, Depends
from sqlmodel import Session
from loguru import logger
from pydantic import BaseModel, Field
from pawsupport import fuis

from DecodeTheBot.core.consts import PAGE_SIZE
from DecodeTheBot.core.database import get_session
from DecodeTheBot.models.guru import Guru
from DecodeTheBot.ui.dtg_ui import objects_ui_with, dtg_navbar, dtg_default_page

router = APIRouter()


@router.get("/{guru_id}", response_model=FastUI, response_model_exclude_none=True)
async def guru_view(guru_id: int, session: Session = Depends(get_session)) -> list[AnyComponent]:
    guru = session.get(Guru, guru_id)
    # guru = Guru.model_validate(guru)
    # guru = Guru.model_validate(guru)
    if not isinstance(guru, Guru):
        return fuis.empty_page()

    return dtg_default_page(
        title=guru.name,
        components=[
            fuis.back_link(),
            guru.ui_detail(),
        ],
    )


@router.get("/", response_model=FastUI, response_model_exclude_none=True)
def guru_list_view(page: int = 1, session: Session = Depends(get_session)) -> list[AnyComponent]:
    logger.info("guru list view")

    data = session.query(Guru).all()
    data = [_ for _ in data if _.episodes or _.reddit_threads]
    data.sort(key=lambda x: len(x.episodes) + len(x.reddit_threads), reverse=True)
    # if not data:
    #     return empty_page()
    total = len(data)

    data = data[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    try:
        return dtg_default_page(
            title="Gurus",
            components=[
                objects_ui_with(data),
                c.Pagination(page=page, page_size=PAGE_SIZE, total=total),
            ],
        )

    except Exception as e:
        logger.error(e)
        return fuis.empty_page(nav_bar=dtg_navbar())


class EpisodeGuruFilter(BaseModel):
    guru_name: str = Field(
        # json_schema_extra={"search_url": "/api/forms/episodes/", "placeholder": "Filter by Guru..."}
        json_schema_extra={
            "search_url": "/api/forms/search/episodes/",
            "placeholder": "Filter by Guru...",
        }
    )


class ThreadGuruFilter(BaseModel):
    guru_name: str = Field(
        json_schema_extra={
            "search_url": "/api/forms/search/reddit_threads/",
            "placeholder": "Filter by Guru...",
        }
    )


def guru_filter(filter_form_initial, model: Literal["episodes", "reddit_threads"]):
    filter_model = EpisodeGuruFilter if model == "episodes" else ThreadGuruFilter
    return c.ModelForm(
        model=filter_model,
        submit_url=".",
        initial=filter_form_initial,
        method="GOTO",
        submit_on_change=True,
        display_mode="inline",
    )
