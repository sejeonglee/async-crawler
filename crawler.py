# crawler.py
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Set, Dict, Callable, Coroutine, Any
from urllib.parse import urljoin, urlparse
import logging

from utils import extract_links, is_valid_url

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AsyncWebCrawler:
    def __init__(
        self,
        max_concurrent_requests: int = 5,
        max_total_requests: int = 30,
    ):
        self.max_concurrent_requests = max_concurrent_requests
        self.max_total_requsts = max_total_requests
        self.url_set_lock = asyncio.Lock()
        self.queue = asyncio.Queue()

        self.client = None
        self.crawled_urls: Set[str] = set()
        self.limits = httpx.Limits(
            max_keepalive_connections=max_concurrent_requests,
            max_connections=max_concurrent_requests,
        )
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            limits=self.limits, timeout=self.timeout, follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _can_process_url(self, url: str) -> bool:
        """Check if URL can be processed"""
        async with self.url_set_lock:
            if len(self.crawled_urls) >= self.max_total_requsts:
                return False
        return is_valid_url(url)

    async def process_url(
        self,
        url: str,
        callback: Callable[[str, str], Coroutine[Any, Any, None]],
        entry_url: str,
    ) -> Set[str]:
        """Process a single URL and extract links"""

        if not self.client:
            raise RuntimeError("Crawler client not initialized")

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            await callback(url, html)

            # Usage
            links = extract_links(soup, url, entry_url)
            logger.info(f"Processed {url}, found {len(links)} valid links")
            return set(links)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error processing {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
        return set()

    async def crawl(
        self, entry_url: str, callback: Callable[[str, str], Coroutine[Any, Any, None]]
    ):
        """Main crawling method for a single entry URL"""
        if entry_url in self.crawled_urls:
            logger.warning(f"URL {entry_url} has already been crawled")
            return

        await self.queue.put(entry_url)

        async def worker():
            while True:
                try:
                    url = await self.queue.get()
                    if not await self._can_process_url(url):
                        self.queue.task_done()
                        continue
                    if url not in self.crawled_urls:
                        logger.info(f"Crawling: {url}")
                        async with self.url_set_lock:
                            self.crawled_urls.add(url)
                        links = await self.process_url(url, callback, entry_url)
                        for link in links:
                            await self.queue.put(link)
                    self.queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker error: {str(e)}")
                    self.queue.task_done()

        workers = [
            asyncio.create_task(worker()) for _ in range(self.max_concurrent_requests)
        ]

        await self.queue.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        logger.info(
            f"Crawling completed for {entry_url}. "
            f"Processed {len(self.crawled_urls)} URLs"
        )


async def example_callback(url: str, html: str):
    """Example callback function that processes crawled pages"""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string if soup.title else "No title"
    logger.info(f"Processed {url} - Title: {title}")


async def main(url: str):
    # Example URLs to crawl"

    async with AsyncWebCrawler(
        max_concurrent_requests=3, max_total_requests=10
    ) as crawler:
        # Crawl multiple sites concurrently
        await crawler.crawl(url, example_callback)

        logger.info(f"\nSummary for {url}:")
        logger.info(f"Total URLs crawled: {len(crawler.crawled_urls)}")
        logger.info("Crawled URLs:")
        # Print summary
        for crawled_url in crawler.crawled_urls:
            logger.info(f"  - {crawled_url}")


def sync_wrapper(url: str):
    asyncio.run(main(url))


if __name__ == "__main__":
    url = "https://python.org"
    sync_wrapper(url)
