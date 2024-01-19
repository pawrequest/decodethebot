# from __future__ import annotations

import inspect
from datetime import datetime
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

from episode_scraper.writer_dc import RPostWriter
from pawsupport.fastui_suport.fuis import Flex
from pawsupport.misc import hash_simple_md5
from sqlmodel import Field, JSON, Relationship, SQLModel
from dateutil import parser
from pydantic import BaseModel, field_validator
from sqlalchemy import Column
from loguru import logger
from fastui import components as c

from .links import GuruEpisodeLink, RedditThreadEpisodeLink
from ..ui.dtg_ui import object_ui

if TYPE_CHECKING:
    from DecodeTheBot.models.guru import Guru
    from .reddit_thread import RedditThread

MAYBE_ATTRS = ["title", "notes", "links", "date"]


class EpisodeBase(SQLModel):
    url: str = Field(index=True)
    title: str = Field(index=True)
    notes: List[str] = Field(default=None, sa_column=Column(JSON))
    links: Dict[str, str] = Field(default=None, sa_column=Column(JSON))
    date: Optional[datetime] = Field(default=None)
    episode_number: Optional[str] = Field(default=None)

    @field_validator("episode_number", mode="before")
    def ep_number_is_str(cls, v) -> str:
        return str(v)

    @field_validator("date", mode="before")
    def parse_date(cls, v) -> datetime:
        if isinstance(v, str):
            try:
                v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                v = parser.parse(v)
        return v

    def log_str(self) -> str:
        if self.title and self.date:
            return f"\t\t<green>{self.date.date()}</green> - <bold><cyan>{self.title}</cyan></bold>"
        else:
            return f"\t\t{self.url}"

    def __str__(self):
        return f"{self.__class__.__name__}: {self.title or self.url}"

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.url})>"

    @property
    def slug(self):
        raise NotImplementedError("Implement in subclass")

    @classmethod
    def log_episodes(cls, eps: Sequence["EpisodeBase"], calling_func=None, msg: str = ""):
        """Logs the first 3 episodes and the last 2 episodes of a sequence episodes"""
        if not eps:
            return
        if calling_func:
            calling_f = calling_func.__name__
        else:
            calling_f = f"{inspect.stack()[1].function} INSPECTED, YOU SHOULD PROVIDE THE FUNC"

        new_msg = f"{msg} {len(eps)} Episodes in {calling_f}():\n"
        new_msg += episodes_log_msg(eps)
        logger.info(new_msg)


class EpisodeMeta(BaseModel):
    length: int
    msg: str = ""


def episodes_log_msg(eps: Sequence[EpisodeBase]) -> str:
    msg = ""  # in case no eps
    msg += "\n".join([_.log_str() for _ in eps[:3]])

    if len(eps) == 4:
        fth = eps[3]
        msg += f"\n{fth.log_str()}"
    elif len(eps) > 4:
        to_log = min([2, abs(len(eps) - 4)])
        msg += " \n\t... more ...\n"
        msg += "\n".join([_.log_str() for _ in eps[-to_log:]])
    return msg


class Episode(EpisodeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gurus: List["Guru"] = Relationship(back_populates="episodes", link_model=GuruEpisodeLink)
    reddit_threads: List["RedditThread"] = Relationship(
        back_populates="episodes", link_model=RedditThreadEpisodeLink
    )

    @property
    def slug(self):
        return f"/eps/{self.id}"

    @property
    def get_hash(self):
        return hash_simple_md5([self.title, str(self.date)])

    def ui_detail(self) -> Flex:
        writer = RPostWriter(self)
        markup = writer.write_one()
        return Flex(
            components=[
                *(object_ui(_) for _ in self.gurus),
                c.Markdown(text=markup),
            ]
        )


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
