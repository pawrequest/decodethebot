# no! SQLModel dragons in from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from episode_scraper import EpisodeDC
from episode_scraper.writer import RPostWriter
from pawsupport.fastui_suport.fuis import Flex
from pawsupport.misc import hash_simple_md5
from sqlmodel import Field, JSON, Relationship, SQLModel
from dateutil import parser
from pydantic import field_validator
from sqlalchemy import Column
from fastui import components as c

from .links import GuruEpisodeLink, RedditThreadEpisodeLink
from ..ui.dtg_ui import object_col_one

if TYPE_CHECKING:
    from DecodeTheBot.models.guru import Guru
    from .reddit_thread import RedditThread


class EpisodeBase(SQLModel, EpisodeDC):
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

    @classmethod
    def rout_prefix(cls):
        return "/eps/"

    def ui_detail(self) -> Flex:
        writer = RPostWriter(self)
        markup = writer.write_one()
        return Flex(
            components=[
                *(object_col_one(_) for _ in self.gurus),
                c.Markdown(text=markup),
            ]
        )
