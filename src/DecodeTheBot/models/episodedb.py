# from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship
from fastui import components as c
import sqlmodel as sqm
import sqlalchemy as sqa

import scrapaw
from scrapaw import DTGEpisode
from suppawt import get_set
from .links import GuruEpisodeLink, RedditThreadEpisodeLink
from ..ui.dtg_ui import object_col_one
from fastuipr import builders

if TYPE_CHECKING:
    from DecodeTheBot.models.guru import Guru
    from .reddit_thread import RedditThread


class DTGEpisodeDB(DTGEpisode, sqm.SQLModel, table=True):
    __tablename__ = "episode"
    links: dict[str, str] = Field(default_factory=dict, sa_column=sqm.Column(sqa.JSON))
    notes: List[str] = Field(default_factory=list, sa_column=sqm.Column(sqa.JSON))
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
        return get_set.hash_simple_md5([self.title, str(self.date)])

    @classmethod
    def rout_prefix(cls):
        return "/eps/"

    def ui_detail(self):
        writer = scrapaw.RPostWriter(self)
        markup = writer.write_one()
        return builders.wrap_divs(
            components=[
                *(object_col_one(_) for _ in self.gurus),
                c.Markdown(text=markup),
            ]
        )
