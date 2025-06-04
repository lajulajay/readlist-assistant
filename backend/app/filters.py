from typing import List
from .models import Book, BookFilter

def filter_books(books: List[Book], filters: BookFilter) -> List[Book]:
    def matches(book: Book) -> bool:
        if filters.genre and (not book.genre or filters.genre.lower() not in book.genre.lower()):
            return False
        if filters.min_ratings and (not book.num_ratings or book.num_ratings < filters.min_ratings):
            return False
        if filters.min_rating and (not book.avg_rating or book.avg_rating < filters.min_rating):
            return False
        return True

    return [b for b in books if matches(b)]