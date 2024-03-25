from __future__ import annotations

import fastui
from fastui import components as c, events
from sqlmodel import select

from DecodeTheBot.models import guru
from DecodeTheBot.ui import dtg_styles
from pawdantic.pawui import builders, styles
from DecodeTheBot.ui.dtg_styles import TITLE


def dtg_default_page(components: list[fastui.AnyComponent] | None, title=None):
    title_ = title or "Decode The Guru"
    return builders.default_page(
        title=title_,
        components=components,
        header_class=TITLE,
    ) if components else builders.empty_page(title=title_ + " - Empty Page")


def threads_div(threads_, class_name) -> c.Div:
    return builders.wrap_divs(
        components=[
            title_sluglink_div(thread_, class_name=styles.ROW_STYLE)
            for thread_ in threads_
        ],
        class_name=class_name,
    )


def gurus_div(gurus_, class_name) -> c.Div:
    return builders.wrap_divs(
        components=[
            name_sluglink_div(guru_, class_name=styles.ROW_STYLE)
            for guru_ in gurus_
        ],
        class_name=class_name,
    )


def episodes_div(episodes_: list, class_name) -> c.Div:
    return builders.wrap_divs(
        components=[
            title_sluglink_div(episode, class_name=styles.ROW_STYLE)
            for episode in episodes_
        ],
        class_name=class_name,
    )


def date_div(date, class_name) -> c.Div:
    return c.Div(
        components=[
            c.Text(text=str(date)),
        ],
        class_name=class_name,
    )


def episode_detail(episode) -> c.Div:

    top_row = builders.wrap_divs(
        components=[
            date_div(episode.date, class_name=dtg_styles.DATE_COL),
            ep_number_div(episode),

        ],
        class_name=styles.ROW_STYLE,
    )
    return builders.wrap_divs(
        components=[
            top_row,
            links_div(
                links=episode.links,
                class_name=styles.ROW_STYLE,
                inner_class_name=dtg_styles.NAMELINK,
            ),
            notes_div(episode.notes, dtg_styles.NOTES),
        ],
        class_name=dtg_styles.EPISODE_DETAIL,
    )


def links_div(links: dict[str, str], class_name, inner_class_name=None):
    return builders.wrap_divs(
        components=[
            c.Link(
                components=[
                    c.Text(text=name),
                ],
                on_click=events.GoToEvent(url=url),
            )
            for name, url in links.items()
        ],
        class_name=class_name,
        inner_class_name=inner_class_name,
    )


def ep_number_div(episode, class_name=dtg_styles.NUMBER_COL):
    return c.Div(
        components=[
            c.Link(
                components=[
                    c.Text(text=f'Episode Number {episode.number.strip()}')
                ],
                on_click=events.GoToEvent(url=episode.url),
            ),
        ],
        class_name=class_name
    )


def name_link(name, url):
    return c.Link(
        components=[c.Text(text=name)],
        on_click=events.GoToEvent(url=url),
        class_name=dtg_styles.NAMELINK
    )


def notes_div(notes, class_name):
    col = builders.wrap_divs(
        components=[c.Text(text=note) for note in notes],
        class_name=f'{styles.COL_STYLE}',
        inner_class_name=styles.ROW_STYLE,
    )
    return c.Div(
        components=[col],
        class_name=f'{styles.ROW_STYLE} w-75',
    )


def episode_row(episode) -> c.Div:
    return builders.wrap_divs(
        components=[
            gurus_div(episode.gurus, class_name=styles.COL_STYLE),
            episodes_div([episode], class_name=styles.COL_STYLE),
            threads_div(episode.reddit_threads, class_name=styles.COL_STYLE),
        ],
        class_name=styles.ROW_STYLE,
    )


def guru_row(guru_) -> c.Div:
    return builders.wrap_divs(
        components=[
            gurus_div([guru_], class_name=styles.COL_STYLE),
            episodes_div(guru_.episodes, class_name=styles.COL_STYLE),
            threads_div(guru_.reddit_threads, class_name=styles.COL_STYLE),
        ],
        class_name=styles.ROW_STYLE,
    )


def thread_row(thread_) -> c.Div:
    return builders.wrap_divs(
        components=[
            gurus_div(thread_.gurus),
            episodes_div(thread_.episodes),
            threads_div([thread_]),
        ],
        class_name=styles.ROW_STYLE,
    )


def name_sluglink_div(obj, class_name) -> c.Div:
    return c.Div(
        components=[
            c.Link(
                components=[
                    c.Text(text=obj.name),
                ],
                on_click=events.GoToEvent(url=obj.slug),
            ),
        ],
        class_name=class_name,
    )


def title_sluglink_div(obj, class_name) -> c.Div:
    return c.Div(
        components=[
            c.Link(
                components=[
                    c.Text(text=obj.title),
                ],
                on_click=events.GoToEvent(url=obj.slug),
            ),
        ],
        class_name=class_name,
    )


def guru_filter_init(guru_name, session, clazz):
    filter_form_initial = {}
    if guru_name:
        guru_ = session.exec(select(guru.Guru).where(guru.Guru.name == guru_name)).one()
        statement = select(clazz).where(clazz.gurus.any(guru.Guru.id == guru_.id))
        data = session.exec(statement).all()
        filter_form_initial["guru"] = {"value": guru_name, "label": guru_.name}
    else:
        data = session.query(clazz).all()
    return data, filter_form_initial
