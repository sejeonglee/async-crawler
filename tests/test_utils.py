# test_crawler.py
import pytest
from bs4 import BeautifulSoup
from utils import extract_links
from unittest.mock import patch


@pytest.fixture
def sample_html():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Test Page</title>
    </head>
    <body>
        <a href="http://example.com/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="http://example.com/page3">Page 3</a>
        <a href="invalid-url">Invalid URL</a>
    </body>
    </html>
    """


@pytest.fixture
def soup(sample_html):
    return BeautifulSoup(sample_html, "html.parser")


@patch("crawler.is_valid_url", return_value=True)
def test_extract_links(mock_is_valid_url, soup):
    url = "http://example.com"
    entry_url = "http://example.com"
    links = extract_links(soup, url, entry_url)
    expected_links = [
        "http://example.com/page1",
        "http://example.com/page2",
        "http://example.com/page3",
    ]
    assert sorted(links) == sorted(expected_links)


# Run the tests
if __name__ == "__main__":
    pytest.main()
