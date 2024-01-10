# from __future__ import annotations
from typing import Optional, List

from episode_scraper.episode_model import EpisodeBase
from sqlmodel import Field



# if TYPE_CHECKING:
#     ...
#     from .guru import GuruExt
#     from .reddit_ext import RedditThreadExt


class EpisodeExt(EpisodeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # gurus: List["GuruExt"] = Relationship(back_populates="episodes", link_model=GuruEpisodeLink)
    # reddit_threads: List["RedditThreadExt"] = Relationship(
    #     back_populates="episodes", link_model=RedditThreadEpisodeLink
    # )
    ...
