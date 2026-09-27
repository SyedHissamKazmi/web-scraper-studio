import logging
import os
import time
from urllib.parse import urljoin, urlparse
from lxml import html
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# 1. LOGGING CONTEXT CONFIGURATION
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


class ResilientInteractiveScanner:

    def __init__(self):
        self.session = self.create_session()

    def create_session(self) -> requests.Session:
        """Creates an isolated HTTP session with standard headers and robust retry configurations."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        })

        # Retry strategy: wait 1s, 2s, 4s if the remote server drops requests unexpectedly
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=5, pool_maxsize=5
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def validate_url(self, url: str) -> bool:
        """Verifies if the structured text string qualifies as a valid target schema."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False


def main_terminal_loop():
    scanner = ResilientInteractiveScanner()

    print("=" * 60)
    print("      IMPROVED AUTOMATED TERMINAL SCANNER & EXCEL EXPORT     ")
    print("=" * 60)
    print("Type 'exit' or 'q' at any time to close the application.\n")

    while True:
        user_input = (
            input("\nEnter target website URL (e.g., wikipedia.org): ")
            .strip()
        )

        if user_input.lower() in ["exit", "q"]:
            print("\nShutting down session pipeline. Goodbye!")
            break

        if not user_input:
            print("[-] Input query field cannot be empty.")
            continue

        # Force schema validation layout
        if not user_input.startswith(("http://", "https://")):
            user_input = "https://" + user_input

        if not scanner.validate_url(user_input):
            print("[-] Invalid URL pattern format. Please try again.")
            continue

        try:
            logging.info(f"Connecting to remote target: {user_input}...")
            # Defensive connect and read timeouts (5s connection window, 10s parsing window)
            response = scanner.session.get(user_input, timeout=(5, 10))

            if response.status_code != 200:
                logging.error(
                    f"Server handshake dropped. HTTP Status Code:"
                    f" {response.status_code}"
                )
                continue

            # Load content body directly into raw lxml document trees
            tree = html.fromstring(response.content)

            # Extract heading elements safely converting structural tags to text strings
            raw_headings = tree.xpath(
                "//h1/text() | //h2/text() | //h3/text()"
            )
            headings = []
            for h in raw_headings:
                text_val = str(h).strip()
                if len(text_val) > 2 and text_val not in headings:
                    headings.append(text_val)

            # Isolate link vectors, resolve path structures, and clear out repetitive fields
            raw_links = tree.xpath("//a/@href")
            clean_links_set = set()
            for l in raw_links:
                href_str = str(l).strip()
                if href_str.startswith("/") or href_str.startswith("http"):
                    absolute_url = urljoin(user_input, href_str)
                    clean_links_set.add(absolute_url)

            clean_links = list(clean_links_set)

            # Defensive Check: If the page layout blocked scraping entirely
            if not headings and not clean_links:
                logging.warning(
                    "No structural content extracted. The target site might be"
                    " a JavaScript Single Page App (SPA) or blocking requests."
                )
                continue

            # PRINT TERMINAL PREVIEW INTERFACE
            print(f"\n--- [ LIVE PREVIEW FOR {user_input} ] ---")
            print(
                f"[+] Extracted {len(headings)} Headings. Top 3:"
                f" {headings[:3]}"
            )
            print(
                f"[+] Discovered {len(clean_links)} Unique Links. Top 3:"
                f" {clean_links[:3]}"
            )

            # EXCEL STORAGE OPERATION ENGINE
            # Balanced padding keeps array dimension layouts uniform for the Pandas mapping
            max_len = max(len(headings), len(clean_links))
            padded_headings = headings + [""] * (max_len - len(headings))
            padded_links = clean_links + [""] * (max_len - len(clean_links))

            # Isolate netloc domain text formatting to title the spreadsheet file dynamically
            domain = urlparse(user_input).netloc.replace("www.", "")
            filename = f"scraped_{domain}.xlsx"

            df = pd.DataFrame({
                "Target Page Titles & Headings": padded_headings,
                "Extracted Resource Links": padded_links,
            })

            # Stream straight down to local hard disk paths
            df.to_excel(filename, index=False)
            logging.info(
                f"SUCCESS: Compiled matrix exported directly to: {filename}\n"
            )

            time.sleep(1)  # Ethical script processing buffer spacing

        except requests.exceptions.Timeout:
            logging.error("Connection attempt timed out. The server took too long to reply.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Network framework error encountered: {e}")
        except Exception as e:
            logging.error(f"Internal pipeline parsing exception: {e}")


if __name__ == "__main__":
    main_terminal_loop()
