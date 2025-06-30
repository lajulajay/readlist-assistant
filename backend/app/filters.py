"""
Book Filtering Module

This module provides filtering functionality for book collections based on
various criteria such as genre, ratings, and other metadata.

Key Features:
- Genre-based filtering with case-insensitive matching
- Rating threshold filtering (minimum ratings count, average rating)
- Extensible filter system for additional criteria
- Efficient in-memory filtering for small to medium datasets

Filter Criteria:
- Genre: Case-insensitive substring matching
- Min Ratings: Minimum number of ratings threshold
- Min Rating: Minimum average rating threshold (0-5 scale)

Usage:
- Used by the main API endpoints for book filtering
- Supports the frontend filtering interface
- Can be extended for additional filter criteria

Author: ReadList Assistant Team
"""

from typing import List
from .models import Book, BookFilter

def filter_books(books: List[Book], filters: BookFilter) -> List[Book]:
    """
    Filter a list of books based on specified criteria.
    
    Args:
        books: List of Book objects to filter
        filters: BookFilter object containing filter criteria
        
    Returns:
        List of Book objects that match the filter criteria
        
    Filter Logic:
        - Genre: Case-insensitive substring matching
        - Min Ratings: Books must have at least this many ratings
        - Min Rating: Books must have at least this average rating
    """
    def matches(book: Book) -> bool:
        # Genre filtering with case-insensitive matching
        if filters.genre and (not book.genre or filters.genre.lower() not in book.genre.lower()):
            return False
        # Minimum ratings count filtering
        if filters.min_ratings and (not book.num_ratings or book.num_ratings < filters.min_ratings):
            return False
        # Minimum average rating filtering
        if filters.min_rating and (not book.avg_rating or book.avg_rating < filters.min_rating):
            return False
        return True

    return [b for b in books if matches(b)]