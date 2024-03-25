# from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship
import sqlmodel as sqm
import sqlalchemy as sqa

from scrapaw import EpisodeBase
from suppawt import get_set
from .links import GuruEpisodeLink, RedditThreadEpisodeLink

if TYPE_CHECKING:
    from DecodeTheBot.models.guru import Guru
    from .reddit_thread import RedditThread


class Episode(EpisodeBase, sqm.SQLModel, table=True):
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
