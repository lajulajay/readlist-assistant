from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from .scraper import get_ezra_klein_book_recommendations
from .filters import filter_books
from .models import Book, BookFilter

app = FastAPI(title="ReadList Assistant API")

# Allow local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for MVP
BOOK_CACHE: List[Book] = []

@app.on_event("startup")
async def startup_event():
    # Populate BOOK_CACHE on startup
    global BOOK_CACHE
    BOOK_CACHE = await get_ezra_klein_book_recommendations()

@app.get("/books", response_model=List[Book])
async def get_books(
    genre: Optional[str] = Query(None),
    min_ratings: Optional[int] = Query(None),
    min_rating: Optional[float] = Query(None),
):
    """Return filtered list of books."""
    filtered = filter_books(
        BOOK_CACHE,
        BookFilter(
            genre=genre,
            min_ratings=min_ratings,
            min_rating=min_rating,
        ),
    )
    return filtered

@app.post("/refresh", response_model=List[Book])
async def refresh_books():
    """Re-scrape and refresh the book list."""
    global BOOK_CACHE
    BOOK_CACHE = await get_ezra_klein_book_recommendations()
    return BOOK_CACHE