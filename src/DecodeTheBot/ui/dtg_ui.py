from __future__ import annotations

from functools import partial
from typing import Sequence, Union

from fastui import AnyComponent, components as c
from fastui.events import GoToEvent
from loguru import logger
from pydantic import BaseModel
from pawsupport import slug_or_none, title_or_name
from pawsupport.fastui_suport import fuis

from DecodeTheBot.ui.css import HEAD, PLAY_COL, SUB_LIST, TITLE_COL


def get_headers(header_names: list) -> c.Div:
    headers = [c.Div(components=[c.Text(text=_)], class_name=HEAD) for _ in header_names]
    head_row = fuis.Row(components=headers, class_name=HEAD)
    return head_row


def objects_ui_with(objects: Sequence) -> c.Div:
    try:
        ui_elements = [_object_ui_with_related(_) for _ in objects]
        head_names = list(ui_elements[0].keys())
        headers = get_headers(head_names)
        rows = [fuis.Row([_ for _ in o.values()]) for o in ui_elements]
        col = fuis.Col(components=[headers, *rows])
        return col
    except Exception as e:
        logger.error(e)


def objects_ui(objects: Sequence, class_name_int="", class_name_ext="") -> c.Div:
    try:
        if not objects:
            return fuis.empty_div(col=True)
        rows = [object_ui(_, class_name_int) for _ in objects]
        # col = Col(components=rows, class_name=class_name_ext)
        col = fuis.Col(components=rows)
        return col
    except Exception as e:
        logger.error(e)


def object_ui(obj, class_name="") -> Union[c.Div, c.Link]:
    if not obj:
        return fuis.empty_div(col=True)
    clink = ui_link(title_or_name(obj), slug_or_none(obj))
    return fuis.Col(components=[clink], class_name=class_name)


class UIThing(BaseModel):
    gurus: list[AnyComponent]
    episodes: list[AnyComponent]
    threads: list[AnyComponent]


def _object_ui_with_related(obj) -> dict[str, c.Div]:
    typs = ["gurus", "episodes", "reddit_threads"]
    out_d = dict()
    for i, typ in enumerate(typs):
        if hasattr(obj, typ):
            out = getattr(obj, typ, None)
            out_d[typ] = (
                objects_ui(out, class_name_int=SUB_LIST, class_name_ext=SUB_LIST)
                if out
                else fuis.empty_div(col=True)
            )
    last = out_d.popitem()
    out_d.update(title=title_column(obj))
    out_d.update({last[0]: last[1]})
    return out_d


def title_column(obj) -> fuis.Col:
    url = slug_or_none(obj)
    title = title_or_name(obj)
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


guru_col = partial(fuis.Col, classes=["col-10"])
