import argparse
import logging
import os
import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from lxml import html
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


class WebScraper:
    """A reusable web scraper to extract headings and links from web pages."""

    def __init__(self, user_agent: Optional[str] = None):
        self.session = self._create_session(user_agent=user_agent)

    @staticmethod
    def _create_session(user_agent: Optional[str] = None) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
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

    def fetch_page(self, url: str, timeout: Tuple[int, int] = (5, 10)) -> str:
        url = self.normalize_url(url)
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content.decode(response.encoding or "utf-8", errors="replace")

    @staticmethod
    def extract_headings_and_links(base_url: str, content: str) -> Tuple[List[str], List[str]]:
        document = html.fromstring(content)
        headings = [
            text.strip()
            for text in document.xpath("//h1/text() | //h2/text() | //h3/text()")
            if text and text.strip()
        ]
        unique_headings = []
        for heading in headings:
            if heading not in unique_headings:
                unique_headings.append(heading)

        raw_links = document.xpath("//a/@href")
        clean_links = set()
        for href in raw_links:
            href_text = str(href).strip()
            if not href_text:
                continue
            if href_text.startswith("#"):
                continue
            if href_text.startswith("mailto:") or href_text.startswith("tel:"):
                continue
            absolute_url = urljoin(base_url, href_text)
            parsed = urlparse(absolute_url)
            if parsed.scheme and parsed.netloc:
                clean_links.add(absolute_url)

        return unique_headings, sorted(clean_links)

    @staticmethod
    def build_dataframe(headings: List[str], links: List[str]) -> pd.DataFrame:
        max_len = max(len(headings), len(links), 1)
        headings += [""] * (max_len - len(headings))
        links += [""] * (max_len - len(links))
        return pd.DataFrame(
            {
                "Target Page Titles & Headings": headings,
                "Extracted Resource Links": links,
            }
        )

    @staticmethod
    def write_output(dataframe: pd.DataFrame, output_path: str) -> None:
        output_ext = os.path.splitext(output_path)[1].lower()
        if output_ext == ".csv":
            dataframe.to_csv(output_path, index=False)
        else:
            dataframe.to_excel(output_path, index=False)
        logging.info(f"Saved scraped data to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape headings and links from a web page and export to Excel or CSV."
    )
    parser.add_argument("url", help="Target website URL to scrape")
    parser.add_argument(
        "--output",
        "-o",
        default="",
        help="Output filename. Defaults to scraped_<domain>.xlsx",
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=0.5,
        help="Delay in seconds before writing output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scraper = WebScraper()

    try:
        normalized_url = scraper.normalize_url(args.url)
        logging.info(f"Fetching page: {normalized_url}")
        page_content = scraper.fetch_page(normalized_url)

        headings, links = scraper.extract_headings_and_links(normalized_url, page_content)
        logging.info(f"Extracted {len(headings)} headings and {len(links)} links.")

        if not args.output:
            domain = urlparse(normalized_url).netloc.replace("www.", "")
            args.output = f"scraped_{domain}.xlsx"

        dataframe = scraper.build_dataframe(headings, links)
        time.sleep(args.delay)
        scraper.write_output(dataframe, args.output)

    except Exception as error:
        logging.error(f"Scraping failed: {error}")


if __name__ == "__main__":
    main()
