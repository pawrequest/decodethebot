from __future__ import annotations

from typing import List, TYPE_CHECKING

from redditbot import RedditThread
from sqlmodel import Relationship

if TYPE_CHECKING:
    from gurupod.models.episode_ext import EpisodeExt
from gurupod.models.guru import Guru
from gurupod.models.links import RedditThreadGuruLink, RedditThreadEpisodeLink


class RedditThreadExt(RedditThread, table=True, extend_existing=True):
    # id: Optional[int] = Field(default=None, primary_key=True)

    gurus: List["Guru"] = Relationship(back_populates="reddit_threads", link_model=RedditThreadGuruLink)
    episodes: List["EpisodeExt"] = Relationship(back_populates="reddit_threads", link_model=RedditThreadEpisodeLink)
