# no dont do this!! from __future__ import annotations
# it does this :(
"""sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[Guru(guru)]'. Original exception was: When initializing mapper Mapper[Guru(guru)], expression "relationship("List['Episode']")" seems to be using a generic class as the argument to relationship(); please state the generic argument using an annotation, e.g. "episodes: Mapped[List['Episode']] = relationship()"
E           sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[Guru(guru)], expression "relationship("List['Episode']")" seems to be using a generic class as the argument to relationship(); please state the generic argument using an annotation, e.g. "episodes: Mapped[List['Episode']] = relationship()"

"""
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

from .links import GuruEpisodeLink, RedditThreadGuruLink

if TYPE_CHECKING:
    from .episodedb import DTGEpisodeDB
    from .reddit_thread import RedditThread


class GuruBase(SQLModel):
    name: str = Field(index=True, unique=True)

    @property
    def slug(self):
        return f"/guru/{self.id}"


class Guru(GuruBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    episodes: List["DTGEpisodeDB"] = Relationship(back_populates="gurus", link_model=GuruEpisodeLink)

    reddit_threads: List["RedditThread"] = Relationship(
        back_populates="gurus", link_model=RedditThreadGuruLink
    )

    @classmethod
    def rout_prefix(cls):
        return "/guru/"

    @property
    def interest(self):
        return len(self.episodes) + len(self.reddit_threads)


