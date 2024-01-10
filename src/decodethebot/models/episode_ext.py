# from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING

from episode_scraper.episode_model import EpisodeBase
from sqlmodel import Field, Relationship

from src.decodethebot.models.links import GuruEpisodeLink


if TYPE_CHECKING:
    from src.decodethebot.models.guru import Guru
#     ...
#     from .guru import GuruExt
#     from .reddit_ext import RedditThreadExt


class Episode(EpisodeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gurus: List["Guru"] = Relationship(back_populates="episodes", link_model=GuruEpisodeLink)
    # reddit_threads: List["RedditThreadExt"] = Relationship(
    #     back_populates="episodes", link_model=RedditThreadEpisodeLink
    # )
    ...
