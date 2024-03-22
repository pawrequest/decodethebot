import datetime as dt
from typing import List

from fastui import components as c, events

import scrapaw
from pawdantic.pawui import builders, styles
from . import guru, reddit_thread


# from scrapaw import DTGEpisode


# def episodes_col(episodes_) -> c.Div:
#     return builders.wrap_divs(
#         components=[
#             c.Link(
#                 components=[
#                     c.Text(text=episode.title),
#                 ],
#                 on_click=events.GoToEvent(url=episode.url),
#             )
#             for episode in episodes_
#         ],
#         class_name=styles.COL_STYLE,
#         inner_class_name=styles.ROW_STYLE,
#     )


class DTGEpisodeOut(scrapaw.DTGEpisode):
    id: int
    title: str
    url: str
    date: dt.date
    notes: list[str]
    links: dict[str, str]
    number: str

    gurus: List[guru.GuruBase]
    reddit_threads: List[reddit_thread.RedditThreadBase]

    @property
    def slug(self):
        return f"/eps/{self.id}"

    def fastui_detail_view(self) -> c.Div:
        return builders.wrap_divs(
            components=[
                c.Text(text=self.title),
                c.Text(text=str(self.date)),
                c.Text(text=self.number),
                c.Text(text=self.url),
                *[
                    c.Link(
                        components=[c.Text(text=name)],
                        on_click=events.GoToEvent(url=url),
                    )
                    for name, url in self.links.items()
                ],
                c.Text(text=str(self.notes)),
            ],
            class_name=styles.COL_STYLE,
            inner_class_name=styles.ROW_STYLE,
        )


class GuruOut(guru.GuruBase):
    id: int
    episodes: List[scrapaw.DTGEpisode]
    reddit_threads: List[reddit_thread.RedditThreadBase]

    def fastui_col_basic(self) -> c.Div:
        return builders.wrap_divs(
            components=[
                c.Text(text=self.name),
            ],
            class_name=styles.COL_STYLE,
            inner_class_name=styles.ROW_STYLE,

        )


class RedditThreadOut(reddit_thread.RedditThreadBase):
    id: int
    gurus: list[guru.GuruBase]
    episodes: list[scrapaw.DTGEpisode]

    def fastui_col_basic(self) -> c.Div:
        return builders.wrap_divs(
            components=[
                c.Text(text=self.title),
                c.Text(text=str(self.created_datetime)),
            ],
            class_name=styles.COL_STYLE,
            inner_class_name=styles.ROW_STYLE,
        )


# class EpisodeMeta(BaseModel):
#     length: int
#     msg: str = ""
#

# class EpisodeResponse(BaseModel):
#     meta: EpisodeMeta
#     episodes: list[Episode]
#
#     @classmethod
#     async def from_episodes(cls, episodes: Sequence[Episode], msg="") -> EpisodeResponse:
#         eps = [Episode.model_validate(ep) for ep in episodes]
#         if len(eps) == 0:
#             msg = "No Episodes Found"
#         meta_data = EpisodeMeta(
#             length=len(eps),
#             msg=msg,
#         )
#         res = cls.model_validate(dict(episodes=eps, meta=meta_data))
#         Episode.log_episodes(res.episodes, msg="Responding")
#         return res
#
#     def __str__(self):
#         return f"{self.__class__.__name__}: {self.meta.length} {self.episodes[0].__class__.__name__}s"
