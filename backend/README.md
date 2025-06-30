# ReadList Assistant Backend

FastAPI-based backend for the ReadList Assistant book recommendation system.

## Features

- **Hybrid Parsing System**: Manual split fallback + OpenAI LLM backup
- **Spotify Integration**: Episode retrieval and book recommendation extraction
- **Goodreads Enrichment**: Book metadata and rating data
- **Episode Tracking**: Comprehensive processing statistics
- **RESTful API**: Full CRUD operations for books and episodes
- **Database Management**: PostgreSQL with SQLAlchemy ORM

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Database ORM with PostgreSQL
- **Alembic**: Database migrations
- **Pydantic**: Data validation and serialization
- **aiohttp**: Async HTTP client for external APIs
- **OpenAI API**: LLM-powered parsing backup

## Setup

1. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
app/
├── main.py           # FastAPI application and endpoints
├── models.py         # Database models and Pydantic schemas
├── crud.py           # Database operations
├── database.py       # Database configuration
├── spotify.py        # Spotify API integration and parsing
├── goodreads.py      # Goodreads API integration
├── scraper.py        # Web scraping functionality
└── filters.py        # Book filtering logic

scripts/
├── populate_db.py    # Database population script
├── refresh_db.sh     # Automated refresh script
├── audit_db.py       # Database audit and validation
└── README.md         # Scripts documentation
```

## API Endpoints

### Books
- `GET /api/books/` - List all books
- `GET /api/books/{id}` - Get book details
- `GET /api/books/filter` - Filter and search books
- `GET /api/books/genres` - Get available genres

### Episodes
- `POST /api/episodes/latest/books` - Process latest episode
- `POST /api/episodes/{id}/books` - Process specific episode
- `POST /api/episodes/batch/process` - Batch process episodes
- `GET /api/episodes/processing-stats` - Processing statistics

## Hybrid Parsing System

The backend uses a sophisticated hybrid parsing approach:

1. **Manual Split Fallback** (Primary)
   - Fast, accurate parsing using custom logic
   - 94.7% accuracy on tested episodes
   - No external API calls required

2. **OpenAI LLM Backup** (Secondary)
   - AI-powered parsing for edge cases
   - Used when manual parsing fails or finds <5 books
   - Requires `OPENAI_API_KEY` in environment

## Environment Variables

Required:
- `SPOTIFY_CLIENT_ID`: Spotify API client ID
- `SPOTIFY_CLIENT_SECRET`: Spotify API client secret
- `DATABASE_URL`: PostgreSQL connection string

Optional:
- `OPENAI_API_KEY`: OpenAI API key for LLM parsing
- `EMAIL_TO`: Email address for notifications

## Development

- **Hot Reload**: Automatic server restart on code changes
- **API Documentation**: Available at `/docs` (Swagger UI)
- **Database Migrations**: Use Alembic for schema changes
- **Logging**: Comprehensive logging throughout the application

## Production Deployment

1. Set up PostgreSQL database
2. Configure environment variables
3. Run database migrations
4. Start with production WSGI server (e.g., Gunicorn)

## Author

ReadList Assistant Team