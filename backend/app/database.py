"""
Database Configuration and Connection Management

This module handles database configuration, connection setup, and session management
for the ReadList Assistant application.

Key Components:
- Settings: Environment-based configuration using Pydantic Settings
- Database Engine: SQLAlchemy engine with PostgreSQL connection
- Session Management: Database session factory and dependency injection
- Base Class: SQLAlchemy declarative base for model definitions

Configuration:
- DATABASE_URL: PostgreSQL connection string
- SPOTIFY_CLIENT_ID: Spotify API client ID (required)
- SPOTIFY_CLIENT_SECRET: Spotify API client secret (required)
- Environment variables loaded from .env file

Features:
- Automatic environment variable loading
- Validation of required Spotify credentials
- SQLAlchemy session dependency injection
- Proper connection cleanup and resource management

Author: ReadList Assistant Team
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/readlist_assistant"
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields like EMAIL_TO
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if not self.SPOTIFY_CLIENT_ID or not self.SPOTIFY_CLIENT_SECRET:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in environment or .env file")

settings = Settings()

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 