from fastui import AnyComponent, FastUI, components as c
from fastapi import APIRouter, Depends
from sqlmodel import Session
from pawdantic.pawui import builders, from_dtg

from .eps import guru_filter_init
from ..core.database import get_session
from ..guru_config import guru_settings
from ..models.reddit_m import RedditThread
from ..routers.guroute import guru_filter
from ..ui.dtg_ui import dtg_default_page

router = APIRouter()


@router.get('/{thread_id}', response_model=FastUI, response_model_exclude_none=True)
async def thread_view(thread_id: int, session: Session = Depends(get_session)) -> list[AnyComponent]:
    thread = session.get(RedditThread, thread_id)
    if not thread or not isinstance(thread, RedditThread):
        raise Exception(f'Thread {thread_id} not found')
    return dtg_default_page(
        title=thread.title,
        components=[
            builders.back_link(),
            thread.ui_detail(),
        ],
    )


@router.get('/', response_model=FastUI, response_model_exclude_none=True)
def thread_list_view(
    page: int = 1, guru_name: str | None = None, session: Session = Depends(get_session)
) -> list[AnyComponent]:
    g_sett = guru_settings()
    page_size = g_sett.page_size
    data, filter_form_initial = guru_filter_init(guru_name, session, RedditThread)
    data.sort(key=lambda x: x.created_datetime, reverse=True)

    total = len(data)
    data = data[(page - 1) * page_size : page * page_size]

    return dtg_default_page(
        title='Threads',
        components=[
            guru_filter(filter_form_initial, model='reddit_threads'),
            from_dtg.objects_ui_with(data),
            c.Pagination(page=page, page_size=page_size, total=total),
        ],
    )
