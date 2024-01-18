# nooooo sqlmodel bug from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

from fastui.components import Details
from redditbot import RedditThreadBase
from sqlmodel import Field, Relationship
from .links import RedditThreadEpisodeLink, RedditThreadGuruLink
from ..ui.mixin import Flex


if TYPE_CHECKING:
    from DecodeTheBot.models.episode_ext import Episode
    from DecodeTheBot.models.guru import Guru


class RedditThread(RedditThreadBase, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    gurus: List["Guru"] = Relationship(back_populates="reddit_threads", link_model=RedditThreadGuruLink)
    episodes: List["Episode"] = Relationship(back_populates="reddit_threads", link_model=RedditThreadEpisodeLink)

    # @property
    # def get_hash(self):
    #     return hash_simple_md5([self.reddit_id])

    @property
    def slug(self):
        return f"/red/{self.id}"

    def ui_detail(self) -> Flex:
        return Details(data=self)
