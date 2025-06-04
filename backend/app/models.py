from typing import Optional
from pydantic import BaseModel

class Book(BaseModel):
    title: str
    author: str
    summary: Optional[str]
    genre: Optional[str]
    num_ratings: Optional[int]
    avg_rating: Optional[float]
    source_url: Optional[str]

class BookFilter(BaseModel):
    genre: Optional[str] = None
    min_ratings: Optional[int] = None
    min_rating: Optional[float] = None