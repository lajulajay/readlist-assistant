"""
Web Scraping Module for Goodreads

This module provides web scraping functionality for extracting book data
from Goodreads pages as a fallback when the API is unavailable or limited.

Key Components:
- GoodreadsScraper: Async context manager for scraping Goodreads pages
- Rate limiting and retry logic for robust scraping
- BeautifulSoup-based HTML parsing
- Fake user agent rotation for avoiding detection

Features:
- Book detail extraction from Goodreads pages
- Rating and review count parsing
- Publication date and format detection
- Genre extraction from page metadata
- ISBN and language information
- Summary and description extraction

Scraping Capabilities:
- Rate limiting to respect website policies
- Retry logic with exponential backoff
- User agent rotation to avoid blocking
- Error handling and logging
- Concurrent scraping with asyncio

Data Extraction:
- Title and author information
- Rating statistics and distribution
- Publication details (date, format, pages)
- Genre tags and categories
- Book summaries and descriptions
- ISBN and language codes

Author: ReadList Assistant Team
"""

from typing import List, Optional
from .models import Book
import asyncio
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
from .models import Book, BookCreate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoodreadsScraper:
    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize the Goodreads scraper with rate limiting.
        
        Args:
            rate_limit: Minimum time between requests in seconds
        """
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.ua = UserAgent()

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.ua.random}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _wait_for_rate_limit(self):
        """Ensure we respect rate limits between requests."""
        now = asyncio.get_event_loop().time()
        time_since_last_request = now - self.last_request_time
        if time_since_last_request < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _fetch_page(self, url: str) -> str:
        """Fetch a page with retry logic and rate limiting."""
        await self._wait_for_rate_limit()
        
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise

    def _parse_rating_distribution(self, soup: BeautifulSoup) -> List[int]:
        """Extract rating distribution from the page."""
        try:
            distribution = []
            rating_bars = soup.select("div.rating-distribution__bar")
            for bar in rating_bars:
                # Extract the number from the bar's title attribute
                title = bar.get("title", "")
                count = int(title.split()[0].replace(",", ""))
                distribution.append(count)
            return distribution
        except (AttributeError, ValueError) as e:
            logger.warning(f"Error parsing rating distribution: {str(e)}")
            return []

    def _parse_publication_date(self, date_str: str) -> Optional[datetime]:
        """Parse publication date from various formats."""
        try:
            # Try different date formats
            formats = [
                "%B %d, %Y",  # April 13, 2023
                "%B %Y",      # April 2023
                "%Y"          # 2023
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            return None
        except Exception as e:
            logger.warning(f"Error parsing publication date '{date_str}': {str(e)}")
            return None

    async def scrape_book(self, url: str) -> Optional[BookCreate]:
        """
        Scrape a book's details from its Goodreads page.
        
        Args:
            url: The Goodreads book URL
            
        Returns:
            BookCreate object if successful, None if failed
        """
        try:
            html = await self._fetch_page(url)
            soup = BeautifulSoup(html, "lxml")
            
            # Extract basic information
            title = soup.select_one("h1.Text__title1").text.strip()
            author = soup.select_one("span.ContributorLink__name").text.strip()
            
            # Extract summary
            summary_elem = soup.select_one("div.BookDetails__description")
            summary = summary_elem.text.strip() if summary_elem else None
            
            # Extract genres
            genres = [
                genre.text.strip()
                for genre in soup.select("div.BookPageMetadataSection__genres a")
            ]
            
            # Extract ratings
            ratings_text = soup.select_one("div.RatingStatistics__meta").text.strip()
            num_ratings = int(ratings_text.split()[0].replace(",", ""))
            avg_rating = float(soup.select_one("div.RatingStatistics__rating").text.strip())
            rating_distribution = self._parse_rating_distribution(soup)
            
            # Extract publication details
            details = soup.select_one("div.BookDetails__formatAndLanguage")
            publication_date = None
            date_text = None
            format = None
            num_pages = None
            language = None
            if details:
                format_text = details.select_one("div.BookDetails__format")
                if format_text is not None:
                     format = format_text.text.strip()
                date_text = details.select_one("div.BookDetails__publicationInfo")
                if date_text is not None:
                     publication_date = self._parse_publication_date(date_text.text.strip())
                else:
                     publication_date = None
                pages_text = details.select_one("div.BookDetails__pageCount")
                if pages_text is not None:
                     num_pages = int(pages_text.text.split()[0])
                language_text = details.select_one("div.BookDetails__language")
                if language_text is not None:
                     language = language_text.text.strip()
            
            # Extract ISBN if available
            isbn_elem = soup.select_one("div.BookDetails__isbn")
            isbn = isbn_elem.text.strip() if isbn_elem else None
            
            return BookCreate(
                title=title,
                author=author,
                summary=summary,
                genres=genres,
                num_ratings=num_ratings,
                avg_rating=avg_rating,
                rating_distribution=rating_distribution,
                source_url=None,
                goodreads_url=str(url),
                publication_date=publication_date,
                num_pages=num_pages,
                format=format,
                isbn=isbn,
                language=language
            )
            
        except Exception as e:
            logger.error(f"Error scraping book {url}: {str(e)}")
            return None

    async def scrape_books(self, urls: List[str]) -> List[BookCreate]:
        """
        Scrape multiple books concurrently with rate limiting.
        
        Args:
            urls: List of Goodreads book URLs
            
        Returns:
            List of BookCreate objects for successfully scraped books
        """
        tasks = [self.scrape_book(str(url)) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        books = []
        for result in results:
            if isinstance(result, BookCreate):
                books.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in scraping task: {str(result)}")
        
        return books

# Example usage
async def scrape_goodreads_books(urls: List[str]) -> List[BookCreate]:
    """
    Scrape books from Goodreads URLs.
    
    Args:
        urls: List of Goodreads book URLs
        
    Returns:
        List of BookCreate objects
    """
    async with GoodreadsScraper(rate_limit=2.0) as scraper:
        return await scraper.scrape_books(urls)

async def get_ezra_klein_book_recommendations() -> List[Book]:
    # Placeholder: you'd implement scraping logic here.
    # For now, return a few sample books for MVP/testing.
    return [
        Book(
            title="The Warmth of Other Suns",
            author="Isabel Wilkerson",
            summary="A sweeping history of the Great Migration...",
            genre="History",
            num_ratings=35000,
            avg_rating=4.4,
            source_url="https://www.nytimes.com/2010/09/05/books/review/Smith-t.html"
        ),
        Book(
            title="Thinking, Fast and Slow",
            author="Daniel Kahneman",
            summary="Kahneman takes us on a groundbreaking tour of the mind...",
            genre="Science, Psychology",
            num_ratings=500000,
            avg_rating=4.2,
            source_url="https://www.goodreads.com/book/show/11468377-thinking-fast-and-slow"
        ),
        Book(
            title="Becoming",
            author="Michelle Obama",
            summary="A memoir by the former First Lady of the United States...",
            genre="Biography",
            num_ratings=400000,
            avg_rating=4.5,
            source_url="https://www.goodreads.com/book/show/38746485-becoming"
        ),
    ]