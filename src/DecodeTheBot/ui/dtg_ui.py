from __future__ import annotations

from functools import lru_cache
from typing import Literal, Sequence, Union

from fastui import components as c
from loguru import logger
from pawsupport.fastui_ps import fastui_support as psf
from pawsupport import misc_ps as psm
from pawsupport.sqlmodel_ps.sqlm import get_other_table_names

from DecodeTheBot.ui.css import HEAD, SUB_LIST, TITLE, TITLE_COL


def get_headers(header_names: list) -> c.Div:
    headers = [c.Div(components=[c.Text(text=_)], class_name=HEAD) for _ in header_names]
    head_row = psf.Row(components=headers, class_name=HEAD)
    return head_row


def objects_ui_with(objects: Sequence) -> c.Div:
    """A column with rows for each object, including related objects."""
    try:
        ui_list = [_object_ui_with_related(_) for _ in objects]
        head_names = [_[0] for _ in ui_list[0]]
        head_names = [psm.title_from_snake(_) for _ in head_names]
        headers = get_headers(head_names)
        rows = [psf.Row([_[1] for _ in row_obj]) for row_obj in ui_list]

        col = psf.Col(components=[headers, *rows])
        return col
    except Exception as e:
        logger.error(e)


def objects_col(objects: Sequence, class_name_int="", class_name_ext="") -> c.Div:
    """A column with rows for each object."""
    try:
        if not objects:
            return psf.empty_div(col=True)
        rows = [object_col_one(_, class_name_int) for _ in objects]
        col = psf.Col(components=rows, class_name=class_name_ext)
        return col
    except Exception as e:
        logger.error(e)


def object_col_one(obj, class_name="") -> Union[c.Div, c.Link]:
    """A row for one object with no related objects."""
    if not obj:
        return psf.empty_div(col=True)
    clink = psf.ui_link(psm.title_or_name_val(obj), obj.slug)
    return psf.Col(components=[clink], class_name=class_name)


@lru_cache
def other_table_names(obj) -> list[str]:
    from DecodeTheBot.core.types import data_models

    return get_other_table_names(obj, data_models())


def _object_ui_with_related(obj) -> list[tuple[str, c.Div]]:
    """A tuple of (header_name, column) for title/name and related objects."""
    out_list = [
        (
            typ,
            objects_col(getattr(obj, typ), class_name_int=SUB_LIST, class_name_ext=SUB_LIST),
        )
        for typ in other_table_names(obj)
    ]

    identity_header: Literal["name", "title"] = psm.title_or_name_var(obj)
    out_list.insert(1, (identity_header, title_column(obj)))
    return out_list


def title_column(obj) -> psf.Col:
    url = obj.slug
    title = psm.title_or_name_val(obj)
    return psf.Col(
        class_name=TITLE_COL,
        components=[
            psf.ui_link(title, url),
        ],
    )


def dtg_navbar():
    from DecodeTheBot.core.types import data_models

    return psf.nav_bar_(data_models())


def dtg_default_page(components, title=None):
    return psf.default_page(
        title=title or "Decode The Guru",
        components=components,
        navbar=dtg_navbar(),
        header_class=TITLE,
        # page_classname=PAGE,
    )
