""" Scrape website for new episodes """

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator

from aiohttp import ClientError, ClientSession as ClientSession
from bs4 import BeautifulSoup, Tag
from loguru import logger

from episode_model import EpisodeBase


class MainSoup(BeautifulSoup):
    """BeautifulSoup extended to parse main page for listing pages"""

    def __init__(self, markup: str, main_url, parser: str = "html.parser"):
        super().__init__(markup, parser)
        self.main_url = main_url
        self.listing_pages = list()

    @classmethod
    async def from_url(cls, url: str, http_session: ClientSession):
        html = await _response(url, http_session)
        main_soup = cls(html, url)
        num_pgs = main_soup._num_pages
        main_soup.listing_pages = _listing_page_strs(url, num_pgs)
        return main_soup

    async def episode_stream(self, http_session) -> AsyncGenerator[EpisodeBase, None]:
        """Yield EpisodeBase objects for each episode on each listing page"""
        async for listing_soup in self.listing_soups(http_session):
            async for ep in listing_soup.episodes():
                yield ep

    async def listing_soups(self, http_session) -> AsyncGenerator[ListingSoup, None]:
        """Yield ListingSoup object for each listing page"""
        for listing_page in self.listing_pages:
            logger.debug(f"listing page {listing_page}", bot_name="Scraper")
            listing_page_soup = await ListingSoup.from_url(listing_page, http_session)
            yield listing_page_soup

    @property
    def _num_pages(self) -> int:
        """Get number of pages of listings from pagination controls on mainpage"""
        page_links = self.select(".page-link")
        lastpage = page_links[-1]["href"]
        num_pages = lastpage.split("/")[-1].split("#")[0]
        return int(num_pages)


class ListingSoup(BeautifulSoup):
    """BeautifulSoup extended to parse listing page"""

    def __init__(self, markup: str, lp_url, parser: str = "html.parser"):
        super().__init__(markup, parser)
        self.episode_sections = self.select(".episode")
        self.episode_soups = [ListingEpisodeSubSoup(_) for _ in self.episode_sections]
        self.listing_eps = list()
        self.listing_page_url = lp_url

    async def episodes(self) -> AsyncGenerator[EpisodeBase, None]:
        """Yield EpisodeBase objects for each episode on this listing page"""
        for ep_subsoup in self.episode_soups:
            ep_detail_soup = await EpisodeDetailsSoup.from_url(ep_subsoup.url)
            list_ep_dict = dict(
                title=ep_subsoup.title,
                url=ep_subsoup.url,
                episode_number=ep_subsoup.episode_number,
                date=ep_subsoup.date,
                notes=ep_detail_soup.episode_notes,
                links=ep_detail_soup.episode_links,
            )
            yield EpisodeBase(**list_ep_dict)

    @classmethod
    async def from_url(cls, url: str, http_session: ClientSession):
        html = await _response(url, http_session)
        return cls(html, url)


@dataclass
class ListingEpisodeSubSoup:
    """Subsection of listing page soup containing episode info"""

    _soup_section: Tag

    @property
    def episode_number(self):
        """string because 'bonus' episodes are not numbered"""
        res = self._soup_section.select_one(".episode-info").text.strip().split()[1]
        return str(res)

    @property
    def date(self):
        return self._soup_section.select_one(".publish-date").text.strip()

    @property
    def url(self):
        return self._soup_section.select_one(".episode-title a")["href"]

    @property
    def title(self):
        return self._soup_section.select_one(".episode-title").text.strip()


class EpisodeDetailsSoup(BeautifulSoup):
    """BeautifulSoup extended to parse episode details page"""

    def __init__(self, markup: str, parser: str = "html.parser", url=None):
        super().__init__(markup, parser)
        self.episode_url = url

    @property
    def episode_notes(self):
        paragraphs = self.select(".show-notes p")
        show_notes = [p.text for p in paragraphs if p.text != "Links"]

        return show_notes or None

    @property
    def episode_links(self):
        show_links_html = self.select(".show-notes a")
        show_links_dict = {aref.text: aref["href"] for aref in show_links_html}
        return show_links_dict

    @classmethod
    async def from_url(cls, url: str, http_session: ClientSession = None) -> EpisodeDetailsSoup:
        http_session = http_session or ClientSession()
        async with http_session:
            html = await _response(url, http_session)
            soup = EpisodeDetailsSoup(html, "html.parser", url=url)
            return soup


async def _response(url: str, http_session: ClientSession):
    """Get response from url, retry 3 times if request fails"""
    for _ in range(3):
        try:
            async with http_session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except ClientError as e:
            logger.error(f"Request failed: {e}")
            await asyncio.sleep(2)
            continue
    else:
        raise ClientError("Request failed 3 times")


def _listing_page_strs(main_url: str, num_pages: int) -> list[str]:
    """Construct list of listing page urls from main url and number of pages"""
    return [main_url + f"/episodes/{_ + 1}/#showEpisodes" for _ in range(num_pages)]
