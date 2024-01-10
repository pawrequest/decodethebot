from DecodeTheBot.models.episode_ext import Episode
from DecodeTheBot.models.guru import Guru
from DecodeTheBot.models.links import GuruEpisodeLink, RedditThreadEpisodeLink, RedditThreadGuruLink
from DecodeTheBot.models.reddit_ext import RedditThread

JSON_NAMES_TO_MODEL_MAP = {
    "episode": Episode,
    "guru": Guru,
    "reddit_thread": RedditThread,
    "guru_ep_link": GuruEpisodeLink,
    "reddit_thread_episode_link": RedditThreadEpisodeLink,
    "reddit_thread_guru_link": RedditThreadGuruLink,
}
