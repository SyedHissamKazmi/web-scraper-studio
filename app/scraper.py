from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    url: str
    headings: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    meta_description: str = ""
    og_title: str = ""
    og_image: str = ""
    og_type: str = ""
    title: str = ""
    robots_allowed: bool = True
    status_code: int = 0
    error: str = ""
    content: str = ""


class WebScraper:
    """Extract structured data from any public web page."""

    def __init__(self, user_agent: str | None = None) -> None:
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        session.mount("http://", HTTPAdapter(max_retries=retry))
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    @staticmethod
    def normalize_url(url: str) -> str:
        url = url.strip()
        if not url:
            raise ValueError("URL cannot be empty.")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        return url

    def check_robots(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(self.user_agent, url)
        except Exception as exc:
            logger.warning("robots.txt check failed: %s", exc)
            return True

    def fetch(self, url: str, timeout: Tuple[int, int] = (5, 15)) -> str:
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content.decode(response.encoding or "utf-8", errors="replace")

    @staticmethod
    def parse(url: str, content: str) -> ScrapeResult:
        result = ScrapeResult(url=url)
        doc = html.fromstring(content)

        title_nodes = doc.xpath("//title/text()")
        result.title = title_nodes[0].strip() if title_nodes else ""

        seen = set()
        for h in doc.xpath("//h1/text() | //h2/text() | //h3/text()"):
            text = str(h).strip()
            if len(text) > 2 and text not in seen:
                seen.add(text)
                result.headings.append(text)

        link_set = set()
        for href in doc.xpath("//a/@href"):
            href_str = str(href).strip()
            if not href_str or href_str.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urljoin(url, href_str)
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                link_set.add(absolute)
        result.links = sorted(link_set)

        md = doc.xpath("//meta[@name='description']/@content")
        result.meta_description = md[0].strip() if md else ""

        for prop, attr in [("og:title", "og_title"), ("og:image", "og_image"), ("og:type", "og_type")]:
            values = doc.xpath(f"//meta[@property='{prop}']/@content")
            if values:
                setattr(result, attr, values[0].strip())

        return result


def scrape(
    url: str,
    timeout: Tuple[int, int] = (5, 15),
    user_agent: str | None = None,
    respect_robots: bool = True,
) -> ScrapeResult:
    scraper = WebScraper(user_agent=user_agent)
    normalized = scraper.normalize_url(url)

    allowed = scraper.check_robots(normalized) if respect_robots else True

    try:
        content = scraper.fetch(normalized, timeout=timeout)
    except Exception as exc:
        return ScrapeResult(url=normalized, robots_allowed=allowed, error=str(exc))

    result = scraper.parse(normalized, content)
    result.robots_allowed = allowed
    result.content = content
    return result