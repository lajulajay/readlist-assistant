# ReadList Assistant

Semi-automated assistant to curate books of interest.
Curate, filter, and explore book recommendations from trusted sources (e.g., Ezra Klein's podcast) with enrichment from Goodreads and a simple web UI.

---

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** and **npm** or **yarn**
- **PostgreSQL** (local instance)

---

## Project Structure

```
readlist-assistant/
├── backend/   # FastAPI backend with hybrid parsing system
├── frontend/  # React frontend
└── scripts/   # Utility scripts (e.g., refresh)
```

---

## Backend Setup

1. **Navigate to backend:**
   ```sh
   cd backend
   ```

2. **Create a virtual environment and activate it:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
   (Or use `pip install -r requirements.in` if you want to regenerate requirements.txt.)

4. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your credentials:
     - `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` (required)
     - `OPENAI_API_KEY` (optional, for LLM backup parsing)
     - `EMAIL_TO` (optional, for email notifications)

5. **Run database migrations:**
   ```sh
   alembic upgrade head
   ```

6. **Run the backend server:**
   ```sh
   uvicorn app.main:app --reload
   ```
   The API will be available at [http://localhost:8000](http://localhost:8000).

---

## Frontend Setup

1. **Navigate to frontend:**
   ```sh
   cd ../frontend
   ```

2. **Install dependencies:**
   ```sh
   npm install
   # or
   yarn install
   ```

3. **Start the frontend:**
   ```sh
   npm start
   # or
   yarn start
   ```
   The UI will open at [http://localhost:3000](http://localhost:3000).

---

## Hybrid Parsing System

The backend uses a sophisticated hybrid parsing system for extracting book recommendations:

1. **Manual Split Fallback** (Primary): Fast and accurate parsing using custom logic
   - Handles concatenated book recommendations without delimiters
   - 94.7% accuracy on tested episodes
   - No external API calls required

2. **OpenAI LLM Backup** (Secondary): AI-powered parsing for edge cases
   - Used only when manual parsing fails to find books
   - Requires `OPENAI_API_KEY` in environment
   - Handles complex or unusual formatting

3. **Section Detection**: Supports multiple recommendation section headers:
   - "Book Recommendations:"
   - "Recommendations:"

4. **Episode Tracking**: All processed episodes are tracked in the database, regardless of whether books were found.

---

## Database Population

### Automated Population
```bash
# Populate database starting from offset 0 (most recent episodes)
python scripts/populate_db.py

# Populate database starting from specific offset
python scripts/populate_db.py --start-offset 10
```

### Manual Processing
```bash
# Process specific episodes
python scripts/process_specific_episodes.py <episode_id1> <episode_id2>
```

### Database Status
```bash
# Check overall database status
python scripts/check_db.py

# Check processed episodes and parser types
python scripts/check_processed_episodes.py
```

---

## Automated Database Refresh (Cron Job)

- The backend includes a script to refresh the book database with the latest podcast recommendations.
- See `backend/scripts/refresh_db.sh` for details.
- You can schedule this script to run weekly using `cron` on your server or local machine.
- The script will:
  - Activate the backend environment
  - Start the backend if not running
  - Call the refresh endpoint
  - Email you the result (configure the email in the script)

---

## Usage

- The web UI loads the list of book recommendations and lets you filter by genre, minimum number of ratings, and minimum average rating.
- Click "View Details" for more information about a book.
- The backend supports filtering, sorting, and pagination via the `/api/books/filter` endpoint.
- The database is refreshed automatically via the cron job, or you can trigger it manually by running the refresh script.

---

## Troubleshooting

- If you encounter CORS issues, ensure the backend's CORS middleware allows requests from your frontend's URL.
- For API rate limits or scraping captchas, consider caching or using a proxy.
- Ensure your PostgreSQL instance is running and accessible at the configured URL.
- Check `.env` for required environment variables (Spotify, Goodreads, etc.).
- If LLM parsing isn't working, verify your `OPENAI_API_KEY` is set correctly.

---

## Next Steps

- Improve the podcast notes scraper in `backend/app/scraper.py`.
- Integrate additional book metadata sources if desired.
- Enhance the UI for richer filtering and book details.
- Deploy backend/frontend (e.g., Vercel, Netlify, or a VPS).