from typing import List, Set
from urllib.parse import urljoin, urlparse


def is_valid_url(url: str) -> bool:
    try:
        urlparse(url)
        return url.startswith(("http://", "https://"))
    except:
        return False


def extract_links(soup, url, entry_url) -> List[str]:
    links: Set[str] = set()
    for a_tag in soup.find_all("a", href=True):
        link = urljoin(url, a_tag["href"])
        if is_valid_url(link):
            links.add(link)
    return list(links)
