from typing import List
from .models import Book

async def get_ezra_klein_book_recommendations() -> List[Book]:
    # Placeholder: you’d implement scraping logic here.
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