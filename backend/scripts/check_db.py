#!/usr/bin/env python3
"""
Script to check the current database state.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import BookDB

def main():
    db = next(get_db())
    try:
        books = db.query(BookDB).all()
        print(f"Total books in database: {len(books)}")
        
        if books:
            print("\nFirst 10 books:")
            for i, book in enumerate(books[:10]):
                print(f"{i+1}. {book.title} by {book.author}")
                print(f"   Episode: {book.episode_id}")
                print(f"   Episode Title: {book.episode_title}")
                print(f"   Episode Book Count: {book.episode_book_count}")
                # print(f"   Source: {book.source}")
                # print(f"   Source URL: {book.source_url}")
                # print(f"   Goodreads URL: {book.goodreads_url}")
                # print(f"   Genres: {book.genres}")
                print(f"   Summary: {book.summary[:100] if book.summary else 'No summary'}...")
                # print(f"   Created: {book.created_at}")
                # print(f"   Updated: {book.updated_at}")
                print()
        
        # Group by episode
        episode_books = {}
        for book in books:
            episode = book.episode_id or "No episode"
            if episode not in episode_books:
                episode_books[episode] = []
            episode_books[episode].append(book)
        
        print(f"\nBooks by episode:")
        for episode, episode_books_list in episode_books.items():
            print(f"\nEpisode: {episode} ({len(episode_books_list)} books)")
            for book in episode_books_list:
                print(f"  - {book.title} by {book.author}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
