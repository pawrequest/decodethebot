# from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING

from episode_scraper.episode_model import EpisodeBase
from sqlmodel import Field, Relationship

from .links import GuruEpisodeLink, RedditThreadEpisodeLink

if TYPE_CHECKING:
    from DecodeTheBot.models.guru import Guru
#     ...
    from .reddit_ext import RedditThread
class Episode(EpisodeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gurus: List["Guru"] = Relationship(back_populates="episodes", link_model=GuruEpisodeLink)
    reddit_threads: List["RedditThread"] = Relationship(
        back_populates="episodes", link_model=RedditThreadEpisodeLink
    )
    ...
