from fastui import AnyComponent, FastUI, components as c
from fastapi import APIRouter, Depends
from sqlmodel import Session

from fastuipr import builders
from ..core.consts import PAGE_SIZE
from ..core.database import get_session
from ..models.guru import guru_filter_init
from ..models.reddit_thread import RedditThread
from ..routers.guroute import guru_filter
from ..ui.dtg_ui import dtg_default_page, objects_ui_with

router = APIRouter()


@router.get("/{thread_id}", response_model=FastUI, response_model_exclude_none=True)
async def thread_view(
    thread_id: int, session: Session = Depends(get_session)
) -> list[AnyComponent]:
    thread = session.get(RedditThread, thread_id)
    if not thread or not isinstance(thread, RedditThread):
        raise Exception(f"Thread {thread_id} not found")
    return dtg_default_page(
        title=thread.title,
        components=[
            builders.back_link(),
            thread.ui_detail(),
        ],
    )


@router.get("/", response_model=FastUI, response_model_exclude_none=True)
def thread_list_view(
    page: int = 1, guru_name: str | None = None, session: Session = Depends(get_session)
) -> list[AnyComponent]:
    data, filter_form_initial = guru_filter_init(guru_name, session, RedditThread)
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
