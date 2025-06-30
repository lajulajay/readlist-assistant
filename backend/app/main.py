"""
ReadList Assistant API - FastAPI Backend

This module provides the main FastAPI application for the ReadList Assistant,
a system that scrapes and manages book recommendations from podcast episodes.

Key Features:
- Book recommendation extraction from Spotify podcast episodes
- Hybrid parsing system (manual + LLM backup)
- Goodreads data enrichment
- Episode tracking and processing statistics
- RESTful API for frontend consumption

Endpoints:
- /api/books/ - Book management and filtering
- /api/episodes/ - Episode processing and batch operations
- /api/episodes/processing-stats - Parsing system statistics

Author: ReadList Assistant Team
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Set, Tuple, Any
import asyncio
from bs4 import BeautifulSoup
from sqlalchemy import or_, and_, func, any_, cast, String, ARRAY, distinct
from urllib.parse import urlparse, urlunparse
import re
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from . import crud, models, database
from .spotify import spotify_client, cleanup
from .goodreads import goodreads_client, GoodreadsBook
from .scraper import GoodreadsScraper

# Set up logging
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="ReadList Assistant API",
    description="API for managing book recommendations from podcast episodes",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create database tables at startup
database.Base.metadata.create_all(bind=database.engine)

# Add cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down."""
    await cleanup()

# Book endpoints
@app.get("/api/books/", response_model=List[models.Book])
def get_books(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    """Get all books from the database."""
    return crud.get_books(db, skip=skip, limit=limit)

@app.get("/api/books/genres", response_model=List[str])
def get_available_genres(
    min_books: int = Query(1, ge=1, description="Minimum number of books in genre to include"),
    db: Session = Depends(database.get_db)
):
    """
    Get a list of available genres with at least min_books books.
    Useful for discovering what genres are available for filtering.
    """
    try:
        # Get all books
        books = db.query(models.BookDB).all()
        
        # Count genres
        genre_counts: Dict[str, int] = {}
        for book in books:
            if book.genres is not None:  # Handle None case
                for genre in book.genres:
                    if genre:  # Skip empty strings
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Filter and sort genres
        available_genres = [
            genre for genre, count in genre_counts.items()
            if count >= min_books
        ]
        
        return sorted(available_genres)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/books/filter", response_model=Dict[str, Any])
def filter_books(
    db: Session = Depends(database.get_db),
    genre: Optional[str] = None,
    min_ratings: Optional[int] = None,
    min_rating: Optional[float] = None,
    min_pages: Optional[int] = None,
    max_pages: Optional[int] = None,
    language: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    search: Optional[str] = None,
    sort: str = "num_ratings_desc",
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Filter books by various criteria.
    Critical filters:
    - genre: Filter by genre (case-insensitive)
    - min_ratings: Minimum number of ratings
    - min_rating: Minimum average rating (0-5)
    - sort: Sort order (num_ratings_desc, avg_rating_desc, title_asc, title_desc, author_asc, author_desc)
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of records to return (for pagination)
    """
    try:
        # Create a base query
        query = db.query(models.BookDB)
        
        # Apply filters
        if genre:
            normalized_genre = genre.lower()
            query = query.filter(
                func.array_to_string(models.BookDB.genres, ',').ilike(f'%{normalized_genre}%')
            )
        
        if min_ratings is not None:
            query = query.filter(models.BookDB.num_ratings >= min_ratings)
        
        if min_rating is not None:
            query = query.filter(models.BookDB.avg_rating >= min_rating)
        
        if min_pages is not None:
            query = query.filter(models.BookDB.num_pages >= min_pages)
        
        if max_pages is not None:
            query = query.filter(models.BookDB.num_pages <= max_pages)
        
        if language:
            query = query.filter(func.lower(models.BookDB.language) == language.lower())
        
        if min_year is not None:
            query = query.filter(models.BookDB.publication_date >= datetime(min_year, 1, 1))
        
        if max_year is not None:
            query = query.filter(models.BookDB.publication_date <= datetime(max_year, 12, 31))
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(models.BookDB.title).like(search_term),
                    func.lower(models.BookDB.author).like(search_term),
                    func.lower(models.BookDB.summary).like(search_term)
                )
            )
        
        # Get total count before pagination
        total = query.count()
        
        # Apply sorting
        sort_mapping = {
            "num_ratings_desc": models.BookDB.num_ratings.desc(),
            "num_ratings_asc": models.BookDB.num_ratings.asc(),
            "avg_rating_desc": models.BookDB.avg_rating.desc(),
            "avg_rating_asc": models.BookDB.avg_rating.asc(),
            "title_asc": models.BookDB.title.asc(),
            "title_desc": models.BookDB.title.desc(),
            "author_asc": models.BookDB.author.asc(),
            "author_desc": models.BookDB.author.desc(),
        }
        
        sort_order = sort_mapping.get(sort, models.BookDB.num_ratings.desc())
        query = query.order_by(sort_order)
        
        # Apply pagination
        books = query.offset(skip).limit(limit).all()
        
        # Convert SQLAlchemy models to Pydantic models
        book_models = [models.Book.model_validate(book) for book in books]
        
        return {
            "books": book_models,
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/books/{book_id}", response_model=models.Book)
def get_book(book_id: int, db: Session = Depends(database.get_db)):
    """Get a specific book by ID."""
    db_book = crud.get_book(db, book_id=book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

def deduplicate_recommendations(recommendations: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    """
    Deduplicate book recommendations based on title and author.
    Returns a list of unique recommendations as dictionaries.
    """
    # Use a set to track unique (title, author) pairs
    seen = set()
    unique_recommendations = []
    
    for title, author in recommendations:
        # Normalize the title and author for comparison
        normalized_title = title.lower().strip()
        normalized_author = author.lower().strip()
        
        # Create a tuple for deduplication
        book_key = (normalized_title, normalized_author)
        
        if book_key not in seen:
            seen.add(book_key)
            unique_recommendations.append({"title": title, "author": author})
    
    return unique_recommendations

def normalize_goodreads_url(url: str) -> str:
    """
    Normalize a Goodreads URL by extracting just the book ID and title.
    Example:
    Input:  https://www.goodreads.com/book/show/41021344-thomas-jefferson?from_search=true&from_srp=true&qid=mN5f2AbKgA&rank=1
    Output: https://www.goodreads.com/book/show/41021344-thomas-jefferson
    """
    if not url:
        return None
    
    # Extract the book ID and title using regex
    match = re.search(r'goodreads\.com/book/show/(\d+[^/?]+)', url)
    if match:
        book_path = match.group(1)
        return f"https://www.goodreads.com/book/show/{book_path}"
    
    # Fallback to basic URL parsing if regex doesn't match
    parsed = urlparse(url)
    if parsed.netloc == 'www.goodreads.com' and parsed.path.startswith('/book/show/'):
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    
    return url

async def enrich_book_with_goodreads(title: str, author: str) -> Optional[GoodreadsBook]:
    """
    Enrich book data with Goodreads information.
    First tries the API, then falls back to scraping if needed.
    """
    try:
        # Try API first
        if goodreads_client:
            book = await goodreads_client.search_book(title, author)
            if book:
                return book
        
        # Fall back to scraping
        async with GoodreadsScraper(rate_limit=2.0) as scraper:
            # Search for the book on Goodreads
            search_url = f"https://www.goodreads.com/search?q={title}+{author}"
            html = await scraper._fetch_page(search_url)
            soup = BeautifulSoup(html, "lxml")
            
            # Get the first result's URL
            first_result = soup.select_one("a.bookTitle")
            if first_result:
                book_url = f"https://www.goodreads.com{first_result['href']}"
                book = await scraper.scrape_book(book_url)
                if book:
                    return GoodreadsBook(
                        title=book.title,
                        author=book.author,
                        goodreads_url=book.goodreads_url,
                        description=book.summary,
                        genres=book.genres,
                        average_rating=book.avg_rating,
                        ratings_count=book.num_ratings,
                        published_year=book.publication_date.year if book.publication_date else None,
                        published_month=book.publication_date.month if book.publication_date else None,
                        published_day=book.publication_date.day if book.publication_date else None,
                        num_pages=book.num_pages,
                        language=book.language,
                        isbn=book.isbn
                    )
        
        return None
    except Exception as e:
        return None

async def process_recommendations(
    recommendations: List[Tuple[str, str]],
    source_url: str,
    source_metadata: Dict[str, Any],
    db: Session
) -> List[models.Book]:
    """
    Process a list of book recommendations:
    1. Deduplicate
    2. Enrich with Goodreads data (API or scraping)
    3. Save to database (always, even if enrichment fails)
    """
    # Deduplicate recommendations
    unique_recommendations = deduplicate_recommendations(recommendations)
    saved_books = []
    
    # Extract episode metadata from source_metadata
    episode_id = None
    episode_title = None
    episode_book_count = len(unique_recommendations)
    
    if "episode_id" in source_metadata:
        episode_id = source_metadata["episode_id"]
        episode_title = source_metadata.get("episode_title")
    elif "episode_ids" in source_metadata and source_metadata["episode_ids"]:
        # For batch processing, use the first episode ID
        episode_id = source_metadata["episode_ids"][0]
        episode_title = source_metadata.get("episode_title")
    
    # Process each recommendation
    for rec in unique_recommendations:
        try:
            # Enrich with Goodreads data
            goodreads_data = await enrich_book_with_goodreads(rec["title"], rec["author"])
            
            # Convert HttpUrl objects to strings and normalize Goodreads URL
            goodreads_url = normalize_goodreads_url(str(goodreads_data.goodreads_url)) if goodreads_data and goodreads_data.goodreads_url else None
            source_url_str = str(source_url) if source_url else None
            
            # Create book object (always save, even if enrichment fails)
            book = models.BookCreate(
                title=rec["title"],
                author=rec["author"],
                goodreads_url=goodreads_url,
                summary=goodreads_data.description if goodreads_data else None,
                genres=goodreads_data.genres if goodreads_data else [],
                num_ratings=goodreads_data.ratings_count if goodreads_data else None,
                avg_rating=goodreads_data.average_rating if goodreads_data else None,
                source="spotify",
                source_url=source_url_str,
                source_metadata=source_metadata,
                episode_id=episode_id,  # Set the episode ID
                episode_title=episode_title,  # Set the episode title
                episode_book_count=episode_book_count,  # Set the total book count for this episode
                # Additional Goodreads fields
                published_year=goodreads_data.published_year if goodreads_data else None,
                published_month=goodreads_data.published_month if goodreads_data else None,
                published_day=goodreads_data.published_day if goodreads_data else None,
                num_pages=goodreads_data.num_pages if goodreads_data else None,
                language=goodreads_data.language if goodreads_data else None,
                isbn=goodreads_data.isbn if goodreads_data else None
            )
            db_book = crud.create_book(db, book)
            saved_books.append(db_book)
        except Exception as e:
            # If enrichment or saving fails, save minimal book entry
            try:
                book = models.BookCreate(
                    title=rec["title"],
                    author=rec["author"],
                    source="spotify",
                    source_url=str(source_url) if source_url else None,
                    source_metadata=source_metadata,
                    episode_id=episode_id,
                    episode_title=episode_title,
                    episode_book_count=episode_book_count
                )
                db_book = crud.create_book(db, book)
                saved_books.append(db_book)
            except Exception as inner_e:
                # If even this fails, skip
                continue
    return saved_books

@app.post("/api/episodes/latest/books", response_model=List[models.Book])
async def save_latest_episode_recommendations(
    db: Session = Depends(database.get_db)
):
    """
    Get book recommendations from the latest episode, enrich with Goodreads data,
    and save them to database.
    """
    try:
        recommendations, episode_id, episode_title = await spotify_client.get_latest_episode_recommendations()
        saved_books = await process_recommendations(
            recommendations,
            f"https://open.spotify.com/episode/{episode_id}" if episode_id else f"https://open.spotify.com/show/{spotify_client.ezra_klein_show_id}",
            {
                "episode_id": episode_id,
                "episode_title": episode_title
            },
            db
        )
        return saved_books
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/episodes/{episode_id}/books", response_model=List[models.Book])
async def save_episode_recommendations(
    episode_id: str,
    db: Session = Depends(database.get_db)
):
    """
    Get book recommendations from a specific episode, enrich with Goodreads data,
    and save them to database. Also tracks the episode processing result.
    """
    try:
        # Get episode details to include title
        episode = await spotify_client.get_episode(episode_id)
        episode_title = episode.name if episode else None
        
        # Extract book recommendations using hybrid parsing
        recommendations, parsing_method = await spotify_client._extract_book_recommendations(episode.description)
        
        # Track the episode processing result
        processed_episode = models.ProcessedEpisodeCreate(
            episode_id=episode_id,
            episode_title=episode_title,
            books_found=len(recommendations),
            parsing_method=parsing_method,
            success=len(recommendations) > 0,
            error_message=None
        )
        crud.create_processed_episode(db, processed_episode)
        
        # Process and save books if any were found
        if recommendations:
            # Delete existing books for this episode to prevent duplication
            deleted_count = crud.delete_books_by_episode(db, episode_id)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} existing books for episode {episode_id}")
            
            saved_books = await process_recommendations(
                recommendations,
                f"https://open.spotify.com/episode/{episode_id}",
                {
                    "episode_id": episode_id,
                    "episode_title": episode_title
                },
                db
            )
            return saved_books
        else:
            return []
            
    except Exception as e:
        # Track failed episode processing
        processed_episode = models.ProcessedEpisodeCreate(
            episode_id=episode_id,
            episode_title=None,
            books_found=0,
            parsing_method="none",
            success=False,
            error_message=str(e)
        )
        crud.create_processed_episode(db, processed_episode)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/episodes/batch/process", response_model=List[models.Book])
async def process_episode_batch(
    batch_size: int = Query(5, ge=1, le=50, description="Number of episodes to process in this batch"),
    offset: int = Query(0, ge=0, description="Offset for pagination (episodes to skip)"),
    save_to_db: bool = Query(True, description="Whether to save recommendations to database"),
    db: Session = Depends(database.get_db)
):
    """
    Process a batch of episodes, enrich book recommendations with Goodreads data,
    and optionally save them to database.
    
    Features:
    - Process multiple episodes at once
    - Enrich with Goodreads data (API + scraping)
    - Optional database saving
    - Pagination support via offset
    - Returns all saved books with complete metadata
    
    Use cases:
    - Initial database population
    - Weekly updates
    - Backfilling historical episodes
    """
    try:
        # Get episodes for this batch
        episodes = await spotify_client._get_episodes_batch(
            spotify_client.ezra_klein_show_id, 
            batch_size, 
            offset
        )
        if not episodes:
            return []

        all_recommendations = []
        for episode in episodes:
            recommendations, parsing_method = await spotify_client._extract_book_recommendations(episode['description'])
            if recommendations:
                all_recommendations.extend(recommendations)

        if not save_to_db:
            # Just return the recommendations without Goodreads data
            return deduplicate_recommendations(all_recommendations)

        # Process all recommendations with Goodreads enrichment
        saved_books = await process_recommendations(
            all_recommendations,
            f"https://open.spotify.com/episode/{episodes[0]['id']}",  # Use first episode as source
            {
                "batch_processed": True,
                "episode_count": len(episodes),
                "episode_ids": [ep["id"] for ep in episodes]
            },
            db
        )

        return saved_books

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/episodes/batch/ids")
async def get_episode_batch_ids(
    batch_size: int = Query(5, ge=1, le=50, description="Number of episodes to get IDs for"),
    offset: int = Query(0, ge=0, description="Offset for pagination (episodes to skip)")
):
    """
    Get episode IDs for a batch without processing them.
    Useful for checking which episodes have already been processed.
    """
    try:
        episodes = await spotify_client._get_episodes_batch(
            spotify_client.ezra_klein_show_id, 
            batch_size, 
            offset
        )
        if not episodes:
            return {"episode_ids": []}
        
        episode_ids = [ep["id"] for ep in episodes]
        return {"episode_ids": episode_ids}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/episodes/processing-stats")
def get_processing_stats(db: Session = Depends(database.get_db)):
    """
    Get processing statistics for the hybrid parsing system.
    Shows success rates and parsing method breakdown.
    """
    try:
        stats = crud.get_processing_stats(db)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))