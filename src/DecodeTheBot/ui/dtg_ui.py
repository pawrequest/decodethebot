from __future__ import annotations

from functools import partial
from typing import Sequence, Union

from fastui import components as c
from fastui.events import GoToEvent
from loguru import logger
import pawsupport as ps

# from pawsupport import slug_or_none, title_or_name_val, title_or_name_var
from pawsupport.fastui_suport import fuis

from DecodeTheBot.ui.css import HEAD, PLAY_COL, SUB_LIST, TITLE_COL


def get_headers(header_names: list) -> c.Div:
    headers = [c.Div(components=[c.Text(text=_)], class_name=HEAD) for _ in header_names]
    head_row = fuis.Row(components=headers, class_name=HEAD)
    return head_row


def objects_ui_with(objects: Sequence) -> c.Div:
    try:
        ui_list = [_object_ui_with_related2(_) for _ in objects]
        head_names = [_[0] for _ in ui_list[0]]
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
    from DecodeTheBot.dtg_bot import DB_MODELS

    typs = [ps.misc.to_snake(_.__name__) for _ in DB_MODELS]
    return typs


def get_related_typs(obj) -> list[str]:
    from DecodeTheBot.dtg_bot import DB_MODELS

    typs = [f"{ps.misc.to_snake(_.__name__)}s" for _ in DB_MODELS if not isinstance(obj, _)]
    return typs


# def _object_ui_with_related(obj) -> dict[str, c.Div]:
#     # typs = ["gurus", "episodes", "reddit_threads"]
#     typs = [ps.misc.to_snake(_.__name__) for _ in DB_MODELS]
#     out_d = dict()
#
#     for typ in typs:
#         if hasattr(obj, typ):
#             out = getattr(obj, typ, None)
#             out_d[typ] = (
#                 objects_col(out, class_name_int=SUB_LIST, class_name_ext=SUB_LIST)
#                 if out
#                 else fuis.empty_div(col=True)
#             )
#     last = out_d.popitem()
#     ident_name = ps.title_or_name_var(obj)
#     out_d[ident_name] = title_column(obj)
#     out_d.update({last[0]: last[1]})
#     return out_d


def _object_ui_with_related2(obj) -> list[tuple[str, c.Div]]:
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


guru_col = partial(fuis.Col, classes=["col-10"])
