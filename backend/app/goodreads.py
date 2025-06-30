"""
Goodreads API Integration

This module provides integration with the Goodreads API for enriching book data
with comprehensive metadata including ratings, publication details, and genres.

Key Components:
- GoodreadsBook: Pydantic model for structured book data
- GoodreadsClient: Async client for Goodreads API interactions
- Search and detail retrieval functionality

Features:
- Book search by title and author
- Detailed book information retrieval
- Publication date parsing and validation
- Genre extraction from Goodreads shelves
- Rating and review count data
- ISBN and language information
- Image URL extraction

API Integration:
- Uses Goodreads XML API for data retrieval
- Async HTTP requests with aiohttp
- Error handling and logging
- Rate limiting consideration

Data Enrichment:
- Enhances basic book recommendations with comprehensive metadata
- Provides validation and structured data models
- Supports the main application's book management system

Author: ReadList Assistant Team
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
from pydantic import BaseModel, HttpUrl
import xml.etree.ElementTree as ET
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class GoodreadsBook(BaseModel):
    """Model for Goodreads book data."""
    title: str
    author: str
    goodreads_url: Optional[HttpUrl] = None
    goodreads_id: Optional[str] = None
    isbn: Optional[str] = None
    isbn13: Optional[str] = None
    description: Optional[str] = None
    published_year: Optional[int] = None
    published_month: Optional[int] = None
    published_day: Optional[int] = None
    publisher: Optional[str] = None
    num_pages: Optional[int] = None
    average_rating: Optional[float] = None
    ratings_count: Optional[int] = None
    reviews_count: Optional[int] = None
    genres: list[str] = []
    language: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    small_image_url: Optional[HttpUrl] = None

class GoodreadsClient:
    """Client for interacting with the Goodreads API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.goodreads.com"
        self.search_url = f"{self.base_url}/search/index.xml"
        self.book_url = f"{self.base_url}/book/show.xml"
    
    async def search_book(self, title: str, author: str) -> Optional[GoodreadsBook]:
        """
        Search for a book by title and author.
        Returns the best match if found.
        """
        try:
            # Clean and format the search query
            search_query = f"{title} {author}"
            search_query = re.sub(r'[^\w\s]', '', search_query)  # Remove special characters
            
            async with aiohttp.ClientSession() as session:
                # Search for the book
                params = {
                    "key": self.api_key,
                    "q": search_query
                }
                async with session.get(self.search_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Goodreads search failed: {response.status}")
                        return None
                    
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)
                    
                    # Get the first result
                    results = root.findall(".//work")
                    if not results:
                        logger.warning(f"No results found for: {search_query}")
                        return None
                    
                    # Get the best match (first result)
                    work = results[0]
                    book = work.find("best_book")
                    
                    if book is None:
                        return None
                    
                    # Extract basic info
                    book_id = book.find("id").text
                    title = book.find("title").text
                    author = book.find("author/name").text
                    
                    # Get detailed book info
                    return await self.get_book_details(book_id)
                    
        except Exception as e:
            logger.error(f"Error searching Goodreads: {str(e)}")
            return None
    
    async def get_book_details(self, book_id: str) -> Optional[GoodreadsBook]:
        """Get detailed information about a book by its Goodreads ID."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "key": self.api_key,
                    "id": book_id
                }
                async with session.get(self.book_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Goodreads book details failed: {response.status}")
                        return None
                    
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)
                    book = root.find("book")
                    
                    if book is None:
                        return None
                    
                    # Extract publication date
                    pub_date = book.find("publication_date")
                    pub_year = None
                    pub_month = None
                    pub_day = None
                    if pub_date is not None and pub_date.text:
                        try:
                            date = datetime.strptime(pub_date.text.strip(), "%m/%d/%Y")
                            pub_year = date.year
                            pub_month = date.month
                            pub_day = date.day
                        except ValueError:
                            pass
                    
                    # Extract genres
                    genres = []
                    for shelf in book.findall(".//shelf"):
                        if shelf.get("name") and shelf.get("count"):
                            genres.append(shelf.get("name"))
                    
                    # Create GoodreadsBook object
                    return GoodreadsBook(
                        title=book.find("title").text,
                        author=book.find("authors/author/name").text,
                        goodreads_url=f"https://www.goodreads.com/book/show/{book_id}",
                        goodreads_id=book_id,
                        isbn=book.find("isbn").text if book.find("isbn") is not None else None,
                        isbn13=book.find("isbn13").text if book.find("isbn13") is not None else None,
                        description=book.find("description").text if book.find("description") is not None else None,
                        published_year=pub_year,
                        published_month=pub_month,
                        published_day=pub_day,
                        publisher=book.find("publisher").text if book.find("publisher") is not None else None,
                        num_pages=int(book.find("num_pages").text) if book.find("num_pages") is not None else None,
                        average_rating=float(book.find("average_rating").text) if book.find("average_rating") is not None else None,
                        ratings_count=int(book.find("ratings_count").text) if book.find("ratings_count") is not None else None,
                        reviews_count=int(book.find("reviews_count").text) if book.find("reviews_count") is not None else None,
                        genres=genres,
                        language=book.find("language_code").text if book.find("language_code") is not None else None,
                        image_url=book.find("image_url").text if book.find("image_url") is not None else None,
                        small_image_url=book.find("small_image_url").text if book.find("small_image_url") is not None else None
                    )
                    
        except Exception as e:
            logger.error(f"Error getting Goodreads book details: {str(e)}")
            return None

# Initialize the client at module level
goodreads_client = None

def init_goodreads_client(api_key: str):
    """Initialize the Goodreads client with an API key."""
    global goodreads_client
    goodreads_client = GoodreadsClient(api_key) 