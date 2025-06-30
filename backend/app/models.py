"""
Database Models and Data Structures

This module defines the SQLAlchemy database models and Pydantic schemas
for the ReadList Assistant application.

Database Models:
- BookDB: Core book entity with all metadata and episode tracking
- ProcessedEpisodeDB: Tracks episode processing results and parsing methods

Pydantic Schemas:
- BookBase/BookCreate/Book: Book data validation and serialization
- ProcessedEpisodeBase/ProcessedEpisodeCreate/ProcessedEpisode: Episode tracking
- BookFilter: Filter parameters for book queries

Key Features:
- Episode tracking with episode_id, episode_title, and episode_book_count
- Goodreads integration with URL and metadata fields
- Flexible genre support using PostgreSQL arrays
- Processing statistics and error tracking
- Comprehensive book metadata (publication date, pages, ISBN, etc.)

Author: ReadList Assistant Team
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Text, ARRAY, DateTime, Boolean
from .database import Base

# SQLAlchemy Models
class BookDB(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    summary = Column(Text, nullable=True)
    genres = Column(ARRAY(String), nullable=True, index=True)
    num_ratings = Column(Integer, nullable=True)
    avg_rating = Column(Float, nullable=True)
    source_url = Column(String, nullable=True)
    goodreads_url = Column(String, nullable=True, unique=True)
    episode_id = Column(String, nullable=True)
    episode_title = Column(String, nullable=True)
    episode_book_count = Column(Integer, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    num_pages = Column(Integer, nullable=True)
    format = Column(String, nullable=True)
    isbn = Column(String, nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

class ProcessedEpisodeDB(Base):
    __tablename__ = "processed_episodes"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(String, unique=True, index=True, nullable=False)
    episode_title = Column(String, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    books_found = Column(Integer, default=0, nullable=False)
    parsing_method = Column(String, nullable=True)  # "manual_split", "openai_llm", "none"
    success = Column(Boolean, default=False, nullable=False)  # True if books found, False otherwise
    error_message = Column(Text, nullable=True)  # For tracking parsing errors

# Pydantic Models
class BookBase(BaseModel):
    title: str
    author: str
    summary: Optional[str] = None
    genres: Optional[List[str]] = []
    num_ratings: Optional[int] = None
    avg_rating: Optional[float] = None
    source_url: Optional[str] = None
    goodreads_url: Optional[str] = None
    episode_id: Optional[str] = None
    episode_title: Optional[str] = None
    episode_book_count: Optional[int] = None
    publication_date: Optional[datetime] = None
    num_pages: Optional[int] = None
    format: Optional[str] = None
    isbn: Optional[str] = None
    language: Optional[str] = None

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int

    class Config:
        from_attributes = True

class ProcessedEpisodeBase(BaseModel):
    episode_id: str
    episode_title: Optional[str] = None
    books_found: int = 0
    parsing_method: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None

class ProcessedEpisodeCreate(ProcessedEpisodeBase):
    pass

class ProcessedEpisode(ProcessedEpisodeBase):
    id: int
    processed_at: datetime

    class Config:
        from_attributes = True

class BookFilter(BaseModel):
    genre: Optional[str] = None
    min_ratings: Optional[int] = None
    min_rating: Optional[float] = None
    search: Optional[str] = None  # For searching in title or author