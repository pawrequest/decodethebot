from typing import TypeVar, Union


def data_models():
    from DecodeTheBot.models.episode import Episode
    from DecodeTheBot.models.guru import Guru
    from DecodeTheBot.models.reddit_thread import RedditThread

    return Guru, Episode, RedditThread


def link_models():
    from DecodeTheBot.models.links import (
        GuruEpisodeLink,
        RedditThreadEpisodeLink,
        RedditThreadGuruLink,
    )

    return GuruEpisodeLink, RedditThreadEpisodeLink, RedditThreadGuruLink


ALL_MODEL = (*data_models(), *link_models())
DATA_MODEL = Union[data_models()]
DATA_MODEL_VAR = TypeVar("DATA_MODEL_VAR", bound=DATA_MODEL)
ALL_MODEL_TYPE = Union[ALL_MODEL]
