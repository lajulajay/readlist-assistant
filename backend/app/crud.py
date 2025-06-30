"""
Database CRUD Operations

This module provides all database operations for the ReadList Assistant application,
including book management, episode tracking, and processing statistics.

Key Functions:
- Book CRUD: create_book, get_book, get_books, update_book, delete_book
- Episode Tracking: create_processed_episode, get_processed_episode, get_processing_stats
- Batch Operations: delete_books_by_episode, get_processed_episode_ids

Features:
- Automatic duplicate detection and updating
- Episode processing result tracking
- Processing statistics and success rate calculation
- Flexible filtering and querying
- Error handling and logging

Database Operations:
- Uses SQLAlchemy ORM for type-safe database operations
- Handles both SQLAlchemy models and Pydantic schemas
- Supports PostgreSQL-specific features (arrays, JSON)
- Implements proper transaction management

Author: ReadList Assistant Team
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models

def get_book(db: Session, book_id: int):
    return db.query(models.BookDB).filter(models.BookDB.id == book_id).first()

def get_books(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    filters: models.BookFilter = None
):
    query = db.query(models.BookDB)
    
    if filters:
        if filters.genre:
            query = query.filter(models.BookDB.genre == filters.genre)
        if filters.min_ratings:
            query = query.filter(models.BookDB.num_ratings >= filters.min_ratings)
        if filters.min_rating:
            query = query.filter(models.BookDB.avg_rating >= filters.min_rating)
        if filters.search:
            search = f"%{filters.search}%"
            query = query.filter(
                or_(
                    models.BookDB.title.ilike(search),
                    models.BookDB.author.ilike(search)
                )
            )
    
    return query.offset(skip).limit(limit).all()

def create_book(db: Session, book: models.BookCreate):
    # Convert Pydantic model to dict and convert HttpUrl fields to strings
    book_dict = book.model_dump()
    if book_dict.get('source_url'):
        book_dict['source_url'] = str(book_dict['source_url'])
    if book_dict.get('goodreads_url'):
        book_dict['goodreads_url'] = str(book_dict['goodreads_url'])
    
    # Check for existing book
    existing_book = None
    if book_dict.get('goodreads_url'):
        existing_book = db.query(models.BookDB).filter(
            models.BookDB.goodreads_url == book_dict['goodreads_url']
        ).first()
    else:
        # If no goodreads_url, check by (title, author, episode_id)
        existing_book = db.query(models.BookDB).filter(
            models.BookDB.title == book_dict['title'],
            models.BookDB.author == book_dict['author'],
            models.BookDB.episode_id == book_dict.get('episode_id')
        ).first()
    
    if existing_book:
        # Update the existing book
        for key, value in book_dict.items():
            setattr(existing_book, key, value)
        db.commit()
        db.refresh(existing_book)
        return existing_book
    
    # Create a new book if it doesn't exist
    db_book = models.BookDB(**book_dict)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def update_book(db: Session, book_id: int, book: models.BookCreate):
    db_book = get_book(db, book_id)
    if db_book:
        # Convert Pydantic model to dict and convert HttpUrl fields to strings
        book_dict = book.model_dump()
        if book_dict.get('source_url'):
            book_dict['source_url'] = str(book_dict['source_url'])
        if book_dict.get('goodreads_url'):
            book_dict['goodreads_url'] = str(book_dict['goodreads_url'])
            
        for key, value in book_dict.items():
            setattr(db_book, key, value)
        db.commit()
        db.refresh(db_book)
    return db_book

def delete_book(db: Session, book_id: int):
    db_book = get_book(db, book_id)
    if db_book:
        db.delete(db_book)
        db.commit()
        return True
    return False 

def delete_books_by_episode(db: Session, episode_id: str):
    """Delete all books associated with a specific episode."""
    deleted_count = db.query(models.BookDB).filter(models.BookDB.episode_id == episode_id).delete()
    db.commit()
    return deleted_count

# Processed Episode CRUD operations
def get_processed_episode(db: Session, episode_id: str):
    return db.query(models.ProcessedEpisodeDB).filter(models.ProcessedEpisodeDB.episode_id == episode_id).first()

def get_processed_episodes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ProcessedEpisodeDB).offset(skip).limit(limit).all()

def create_processed_episode(db: Session, episode: models.ProcessedEpisodeCreate):
    # Check if episode already exists
    existing_episode = get_processed_episode(db, episode.episode_id)
    if existing_episode:
        # Update the existing episode
        episode_dict = episode.model_dump()
        for key, value in episode_dict.items():
            setattr(existing_episode, key, value)
        db.commit()
        db.refresh(existing_episode)
        return existing_episode
    
    # Create a new processed episode
    db_episode = models.ProcessedEpisodeDB(**episode.model_dump())
    db.add(db_episode)
    db.commit()
    db.refresh(db_episode)
    return db_episode

def get_processed_episode_ids(db: Session) -> set:
    """Get a set of all processed episode IDs."""
    episodes = db.query(models.ProcessedEpisodeDB.episode_id).all()
    return {episode[0] for episode in episodes}

def get_processing_stats(db: Session):
    """Get processing statistics."""
    total_processed = db.query(models.ProcessedEpisodeDB).count()
    successful_episodes = db.query(models.ProcessedEpisodeDB).filter(models.ProcessedEpisodeDB.success == True).count()
    failed_episodes = db.query(models.ProcessedEpisodeDB).filter(models.ProcessedEpisodeDB.success == False).count()
    
    success_rate = (successful_episodes / total_processed * 100) if total_processed > 0 else 0
    
    # Get recent episodes with parsing methods
    recent_episodes = db.query(models.ProcessedEpisodeDB).order_by(
        models.ProcessedEpisodeDB.created_at.desc()
    ).limit(50).all()
    
    recent_episodes_data = []
    for episode in recent_episodes:
        recent_episodes_data.append({
            "episode_id": episode.episode_id,
            "episode_title": episode.episode_title,
            "books_found": episode.books_found,
            "parsing_method": episode.parsing_method,
            "success": episode.success,
            "created_at": episode.created_at.isoformat() if episode.created_at else None
        })
    
    return {
        "total_processed": total_processed,
        "successful_episodes": successful_episodes,
        "failed_episodes": failed_episodes,
        "success_rate": round(success_rate, 2),
        "recent_episodes": recent_episodes_data
    } 