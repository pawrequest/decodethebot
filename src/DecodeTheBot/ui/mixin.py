from __future__ import annotations

from functools import partial
from typing import List, Sequence, TYPE_CHECKING, Union

from fastui import AnyComponent, components as c
from fastui.events import GoToEvent
from loguru import logger
from pydantic import BaseModel

from DecodeTheBot.ui.css import HEAD, ROW, COL_DFLT, SUB_LIST, TITLE_COL, PLAY_COL


def slug_or_none(obj) -> str | None:
    return getattr(obj, "slug", None)


def get_headers(header_names: list) -> c.Div:
    headers = [c.Div(components=[c.Text(text=_)], class_name=HEAD) for _ in header_names]
    head_row = Row(components=headers, class_name=HEAD)
    return head_row


def objects_ui_with(objects: Sequence) -> c.Div:
    try:
        ui_elements = [_object_ui_with_related(_) for _ in objects]
        head_names = list(ui_elements[0].keys())
        headers = get_headers(head_names)
        rows = [Row([_ for _ in o.values()], class_name=ROW) for o in ui_elements]
        col = Col(components=[headers, *rows])
        return col
    except Exception as e:
        logger.error(e)


def objects_ui(objects: Sequence, class_name_int="", class_name_ext="") -> c.Div:
    try:
        if not objects:
            return empty_div(col=True)
        rows = [object_ui(_, class_name_int) for _ in objects]
        # col = Col(components=rows, class_name=class_name_ext)
        col = Col(components=rows)
        return col
    except Exception as e:
        logger.error(e)


def object_ui(obj, class_name="") -> Union[c.Div, c.Link]:
    if not obj:
        return empty_div(col=True)
    clink = ui_link(title_or_name(obj), slug_or_none(obj))
    return Col(components=[clink], class_name=class_name)




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
                objects_ui(out, class_name_int=SUB_LIST, class_name_ext=SUB_LIST) if out else empty_div(col=True)
            )
    last = out_d.popitem()
    out_d.update(title=title_column(obj))
    out_d.update({last[0]: last[1]})
    return out_d




def title_column(obj) -> Col:
    url = slug_or_none(obj)
    title = title_or_name(obj)
    return Col(
        class_name=TITLE_COL,
        components=[
            ui_link(title, url),
        ],
    )


def url_or_slug(obj):
    return getattr(obj, "url", getattr(obj, "slug", None))


def play_column(url) -> Col:
    res = Col(
        class_name=PLAY_COL,
        components=[
            c.Link(
                components=[c.Text(text="Play")],
                on_click=GoToEvent(url=url),
            ),
        ],
    )
    return res


def empty_div(col=False, container=False) -> c.Div:
    if col:
        return empty_col()
    elif container:
        return empty_container()
    else:
        return c.Div(components=[c.Text(text="---")])


def empty_col():
    return Col(components=[c.Text(text="---")])


def empty_container():
    return Flex(components=[c.Text(text="---")])


def title_or_name(obj) -> str:
    return getattr(obj, "title", None) or getattr(obj, "name", None)


def ui_link(title, url, on_click=None, class_name="") -> c.Link:
    on_click = on_click or GoToEvent(url=url)
    link = c.Link(components=[c.Text(text=title)], on_click=on_click, class_name=class_name)
    return link


def Flex(components: list[AnyComponent], class_name="") -> c.Div:
    logger.info("Flex")
    try:
        if not components:
            return c.Div(components=[c.Text(text="---")])
    except Exception as e:
        logger.error(e)
    try:
        # class_name = f"container border-bottom border-secondary {class_name}"
        # class_name = f"d-flex border-bottom border-secondary {class_name}"
        return c.Div(components=components, class_name=class_name)
    except Exception as ee:
        logger.error(ee)


def Row(components: List[AnyComponent], class_name=ROW) -> c.Div:
    try:
        # return c.Div(components=components, class_name="row")
        if not components:
            return c.Div(components=[c.Text(text="---")])
        class_name = f"row {class_name}"
        return c.Div(components=components, class_name=class_name)
    except Exception as e:
        logger.error(e)


def Col(components: List[AnyComponent], class_name=COL_DFLT) -> c.Div:
    try:
        # return Col.with_width(components=components, width=2)
        # return c.Div(components=components, class_name="col")
        class_name = f"col {class_name}"
        return c.Div(components=components, class_name=class_name)
    except Exception as e:
        logger.error(e)


guru_col = partial(Col, classes=["col-10"])
