# from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

from episode_scraper.episode_model import EpisodeBase
from episode_scraper.writer import RPostWriter
from sqlmodel import Field, Relationship
from fastui import components as c

from .links import GuruEpisodeLink, RedditThreadEpisodeLink
from ..ui.mixin import Flex, object_ui

if TYPE_CHECKING:
    from DecodeTheBot.models.guru import Guru
    from .reddit_ext import RedditThread


class Episode(EpisodeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gurus: List["Guru"] = Relationship(back_populates="episodes", link_model=GuruEpisodeLink)
    reddit_threads: List["RedditThread"] = Relationship(back_populates="episodes", link_model=RedditThreadEpisodeLink)

    @property
    def slug(self):
        return f"/eps/{self.id}"

    # @property
    # def get_hash(self):
    #     return hash_simple_md5([self.title, str(self.date)])

    def ui_detail(self) -> Flex:
        writer = RPostWriter(self)
        markup = writer.write_one()
        return Flex(
            components=[
                *(object_ui(_) for _ in self.gurus),
                c.Markdown(text=markup),
            ]
        )

    ...
