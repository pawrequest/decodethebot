# no dont do this!! from __future__ import annotations
# it does this :(
"""sqlalchemy.exc.InvalidRequestError: One or more mappers failed to initialize - can't proceed with initialization of other mappers. Triggering mapper: 'Mapper[Guru(guru)]'. Original exception was: When initializing mapper Mapper[Guru(guru)], expression "relationship("List['Episode']")" seems to be using a generic class as the argument to relationship(); please state the generic argument using an annotation, e.g. "episodes: Mapped[List['Episode']] = relationship()"
E           sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[Guru(guru)], expression "relationship("List['Episode']")" seems to be using a generic class as the argument to relationship(); please state the generic argument using an annotation, e.g. "episodes: Mapped[List['Episode']] = relationship()"

"""
from typing import List, Optional, TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, select

from .links import GuruEpisodeLink, RedditThreadGuruLink
from ..ui.mixin import Flex, objects_ui_with

if TYPE_CHECKING:
    from .episode_model import Episode
    from .reddit_ext import RedditThread

    ...


class GuruBase(SQLModel):
    name: Optional[str] = Field(index=True, default=None, unique=True)

    @property
    def slug(self):
        return f"/guru/{self.id}"


class Guru(GuruBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    episodes: List["Episode"] = Relationship(back_populates="gurus", link_model=GuruEpisodeLink)

    reddit_threads: List["RedditThread"] = Relationship(
        back_populates="gurus", link_model=RedditThreadGuruLink
    )

    @property
    def interest(self):
        return len(self.episodes) + len(self.reddit_threads)

    def ui_detail(self) -> Flex:
        return objects_ui_with([self])

    # @property
    # def get_hash(self):
    #     return hash_simple_md5([self.name])
    #


def guru_filter_init(guru_name, session, clazz):
    filter_form_initial = {}
    if guru_name:
        guru = session.exec(select(Guru).where(Guru.name == guru_name)).one()
        statement = select(clazz).where(clazz.gurus.any(Guru.id == guru.id))
        data = session.exec(select(clazz).where(clazz.gurus.any(Guru.id == guru.id))).all()
        filter_form_initial["guru"] = {"value": guru_name, "label": guru.name}
    else:
        data = session.query(clazz).all()
    return data, filter_form_initial
