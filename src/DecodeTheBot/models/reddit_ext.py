# nooooo sqlmodel bug from __future__ import annotations

from typing import List, TYPE_CHECKING, Optional

from redditbot import RedditThreadBase
from sqlmodel import Relationship, Field

from .links import RedditThreadGuruLink, RedditThreadEpisodeLink

if TYPE_CHECKING:
    from DecodeTheBot.models.episode_ext import Episode
    from DecodeTheBot.models.guru import Guru


class RedditThread(RedditThreadBase, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    gurus: List["Guru"] = Relationship(back_populates="reddit_threads", link_model=RedditThreadGuruLink)
    episodes: List["Episode"] = Relationship(back_populates="reddit_threads", link_model=RedditThreadEpisodeLink)
