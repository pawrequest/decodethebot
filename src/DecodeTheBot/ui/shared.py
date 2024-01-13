from __future__ import annotations, annotations as _annotations

from typing import TYPE_CHECKING

from fastui import AnyComponent, components as c
from fastui.events import BackEvent, GoToEvent
from loguru import logger
from sqlalchemy import inspect


if TYPE_CHECKING:
    pass


def log_object_state(obj):
    obj_name = obj.__class__.__name__
    insp = inspect(obj)
    logger.info(f"State of {obj_name}:")
    logger.info(f"Transient: {insp.transient}")
    logger.info(f"Pending: {insp.pending}")
    logger.info(f"Persistent: {insp.persistent}")
    logger.info(f"Detached: {insp.detached}")
    logger.debug("finished")


# Assuming `gurus` and `reddit_threads` are lists of Guru and RedditThread objects respectively


def default_page(components: list[AnyComponent], title: str | None = None) -> list[AnyComponent]:
    try:
        return [
            c.PageTitle(text=title if title else "DecodeTheBot"),
            nav_bar(),
            c.Page(
                components=[
                    *((c.Heading(text=title),) if title else ()),
                    *components,
                ],
                # class_name=PAGE,
            ),
            footer(),
        ]
    except Exception as e:
        logger.error(e)


def empty_page() -> list[AnyComponent]:
    return [
        c.PageTitle(text="empty page"),
        nav_bar(),
        c.Page(
            components=[
                c.Heading(text="durfault title"),
                c.Text(text="---"),
            ],
        ),
        footer(),
    ]


def back_link():
    return c.Link(components=[c.Text(text="Back")], on_click=BackEvent())


def fast_ui_default_page(*components: AnyComponent, title: str | None = None) -> list[AnyComponent]:
    return [
        c.PageTitle(text=f"{title}" if title else "DecodeTheBot"),
        nav_bar(),
        c.Page(
            components=[
                *((c.Heading(text=title),) if title else ()),
                *components,
            ],
        ),
        footer(),
    ]


def footer():
    return c.Footer(
        extra_text="extra durfault text",
        links=[
            c.Link(components=[c.Text(text="Github")], on_click=GoToEvent(url="https://github.com/pydantic/FastUI")),
        ],
    )


def nav_bar():
    return c.Navbar(
        title="DecodeTheBot",
        title_event=GoToEvent(url="/"),
        links=[
            c.Link(
                components=[c.Text(text="Episodes")],
                on_click=GoToEvent(url="/eps/"),
                active="startswith:/eps",
            ),
            c.Link(
                components=[c.Text(text="Threads")],
                on_click=GoToEvent(url="/red/"),
                active="startswith:/red",
            ),
            c.Link(
                components=[c.Text(text="Gurus")],
                on_click=GoToEvent(url="/guru/"),
                active="startswith:/guru",
            ),
        ],
    )


def tabs() -> list[AnyComponent]:
    return [
        c.LinkList(
            links=[
                c.Link(
                    components=[c.Text(text="Cities")],
                    on_click=GoToEvent(url="/table/cities"),
                    active="startswith:/table/cities",
                ),
                c.Link(
                    components=[c.Text(text="Users")],
                    on_click=GoToEvent(url="/table/users"),
                    active="startswith:/table/users",
                ),
            ],
            mode="tabs",
            class_name="+ mb-4",
        ),
    ]
