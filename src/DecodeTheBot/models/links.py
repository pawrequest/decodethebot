# from __future__ import annotations
from typing import Optional

from sqlmodel import Field, SQLModel


class GuruEpisodeLink(SQLModel, table=True):
    guru_id: Optional[int] = Field(default=None, foreign_key="guru.id", primary_key=True)
    episode_id: Optional[int] = Field(default=None, foreign_key="episode.id", primary_key=True)



class RedditThreadEpisodeLink(SQLModel, table=True):
    reddit_thread_id: Optional[int] = Field(default=None, foreign_key="redditthread.id",
                                            primary_key=True)
    episode_id: Optional[int] = Field(default=None, foreign_key="episode.id", primary_key=True)


class RedditThreadGuruLink(SQLModel, table=True):
    reddit_thread_id: Optional[int] = Field(default=None, foreign_key="redditthread.id",
                                            primary_key=True)
    guru_id: Optional[int] = Field(default=None, foreign_key="guru.id", primary_key=True)

# def ui_detail(self) -> Flex:
#     return c.Details(data=self)
