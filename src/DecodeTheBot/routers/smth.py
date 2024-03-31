from fastapi import Depends
from fastui import AnyComponent, FastUI, components as c
from suppawt.fastui_suport.fuis import RoutableModel
from suppawt.misc import snake_name, snake_name_s
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from DecodeTheBot.core.consts import PAGE_SIZE
from DecodeTheBot.core.database import get_session
from DecodeTheBot.models.reddit_m import RedditThread
from DecodeTheBot.routers.red import router
from DecodeTheBot.ui.dtg_ui import dtg_default_page
from fastuipr.from_dtg import objects_ui_with


def filter_factory(model):
    class SomeFilter(BaseModel):
        tag_name: str = Field(
            json_schema_extra={
                "search_url": f"/api/forms/search/{snake_name_s(model)}/",
                "placeholder": f"Filter by {model.__name__}...",
            }
        )

    return SomeFilter


def tag_filter(filter_form_initial, model):
    filter_model = filter_factory(model)
    return c.ModelForm(
        model=filter_model,
        submit_url=".",
        initial=filter_form_initial,
        method="GOTO",
        submit_on_change=True,
        display_mode="inline",
    )


def tag_filter_init(tag_name, tag_model, session, clazz):
    filter_form_initial = {}
    if tag_name:
        tag = session.exec(select(tag_model).where(tag_model.name == tag_name)).one()

        statement = select(clazz).where(clazz.gurus.any(tag_model.id == tag.id))

        data = session.exec(statement).all()
        filter_form_initial[snake_name(tag_model)] = {"value": tag_name, "label": tag.name}
    else:
        data = session.query(clazz).all()
    return data, filter_form_initial


def make_route(clazz, tag_model: RoutableModel):
    @router.get(
        f"/{tag_model.rout_prefix()}", response_model=FastUI, response_model_exclude_none=True
    )
    def smth_list_view(
        page: int = 1,
        tag_name: str | None = None,
        session: Session = Depends(get_session),
        data=None,
    ) -> list[AnyComponent]:
        data, filter_form_initial = tag_filter_init(tag_name, tag_model, session, clazz)
        data.sort(key=lambda x: x.created_datetime, reverse=True)

        total = len(data)
        data = data[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

        return dtg_default_page(
            title="Threads",
            components=[
                guru_filter(filter_form_initial, model="reddit_threads"),
                objects_ui_with(data),
                c.Pagination(page=page, page_size=PAGE_SIZE, total=total),
            ],
        )

    return smth_list_view


@router.get("/", response_model=FastUI, response_model_exclude_none=True)
def smth_list_view(
    page: int = 1, tag_name: str | None = None, session: Session = Depends(get_session), data=None
) -> list[AnyComponent]:
    data, filter_form_initial = tag_filter_init(tag_name, session, RedditThread)
    data.sort(key=lambda x: x.created_datetime, reverse=True)

    total = len(data)
    data = data[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

    return dtg_default_page(
        title="Threads",
        components=[
            guru_filter(filter_form_initial, model="reddit_threads"),
            objects_ui_with(data),
            c.Pagination(page=page, page_size=PAGE_SIZE, total=total),
        ],
    )
