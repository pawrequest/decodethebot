from __future__ import annotations

from typing import Sequence, Union

from fastui import components as c
from fastui.events import GoToEvent
from loguru import logger
import pawsupport as ps
from pawsupport.fastui_suport import fuis
from pawsupport.fastui_suport.fuis import default_page
from pawsupport.misc import title_from_snake
from sqlalchemy import inspect

from DecodeTheBot.ui.css import HEAD, PLAY_COL, SUB_LIST, TITLE_COL, TITLE


def get_headers(header_names: list) -> c.Div:
    headers = [c.Div(components=[c.Text(text=_)], class_name=HEAD) for _ in header_names]
    head_row = fuis.Row(components=headers, class_name=HEAD)
    return head_row


def objects_ui_with(objects: Sequence) -> c.Div:
    try:
        ui_list = [_object_ui_with_related(_) for _ in objects]
        head_names = [_[0] for _ in ui_list[0]]
        head_names = [title_from_snake(_) for _ in head_names]
        headers = get_headers(head_names)
        rows = [fuis.Row([_[1] for _ in row_obj]) for row_obj in ui_list]

        col = fuis.Col(components=[headers, *rows])
        return col
    except Exception as e:
        logger.error(e)


def objects_col(objects: Sequence, class_name_int="", class_name_ext="") -> c.Div:
    try:
        if not objects:
            return fuis.empty_div(col=True)
        rows = [object_col_one(_, class_name_int) for _ in objects]
        # col = Col(components=rows, class_name=class_name_ext)
        col = fuis.Col(components=rows)
        return col
    except Exception as e:
        logger.error(e)


def object_col_one(obj, class_name="") -> Union[c.Div, c.Link]:
    if not obj:
        return fuis.empty_div(col=True)
    clink = ui_link(ps.title_or_name_val(obj), ps.slug_or_none(obj))
    return fuis.Col(components=[clink], class_name=class_name)


def get_typs() -> list[str]:
    from ..dtg_bot import DB_MODELS

    typs = [ps.misc.to_snake(_.__name__) for _ in DB_MODELS]
    return typs


def get_related_typs(obj) -> list[str]:
    from DecodeTheBot.dtg_bot import DB_MODELS

    typs = [f"{ps.misc.to_snake(_.__name__)}s" for _ in DB_MODELS if not isinstance(obj, _)]
    return typs


def _object_ui_with_related(obj) -> list[tuple[str, c.Div]]:
    out_list = [
        (
            typ,
            objects_col(getattr(obj, typ), class_name_int=SUB_LIST, class_name_ext=SUB_LIST),
        )
        for typ in get_related_typs(obj)
    ]

    ident_name = ps.title_or_name_var(obj)
    out_list.insert(1, (ident_name, title_column(obj)))
    return out_list


def title_column(obj) -> fuis.Col:
    url = ps.slug_or_none(obj)
    title = ps.title_or_name_val(obj)
    return fuis.Col(
        class_name=TITLE_COL,
        components=[
            ui_link(title, url),
        ],
    )


def play_column(url) -> fuis.Col:
    res = fuis.Col(
        class_name=PLAY_COL,
        components=[
            c.Link(
                components=[c.Text(text="Play")],
                on_click=GoToEvent(url=url),
            ),
        ],
    )
    return res


def ui_link(title, url, on_click=None, class_name="") -> c.Link:
    on_click = on_click or GoToEvent(url=url)
    link = c.Link(components=[c.Text(text=title)], on_click=on_click, class_name=class_name)
    return link


def log_object_state(obj):
    obj_name = obj.__class__.__name__
    insp = inspect(obj)
    logger.info(f"State of {obj_name}:")
    logger.info(f"Transient: {insp.transient}")
    logger.info(f"Pending: {insp.pending}")
    logger.info(f"Persistent: {insp.persistent}")
    logger.info(f"Detached: {insp.detached}")
    logger.debug("finished")


def dtg_navbar():
    from ..dtg_bot import DB_MODELS

    return fuis.nav_bar_(DB_MODELS)


def dtg_default_page(components, title=None):
    return default_page(
        title=title or "Decode The Guru",
        components=components,
        navbar=dtg_navbar(),
        header_class=TITLE,
        # page_classname=PAGE,
    )
