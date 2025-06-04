# ReadList Assistant

Semi-automated assistant to curate books of interest...
Curate, filter, and explore book recommendations from trusted sources (e.g., Ezra Klein’s podcast) with enrichment from Goodreads and a simple web UI.

---

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** and **npm** or **yarn**

---

## Project Structure

```
readlist-assistant/
├── backend/   # FastAPI backend
└── frontend/  # React frontend
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
   pip install fastapi uvicorn[standard] requests beautifulsoup4 pydantic
   ```

4. **Run the backend server:**
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

2. **Initialize React app (if not already done):**
   ```sh
   npx create-react-app . --template typescript
   ```

3. **Install dependencies:**
   ```sh
   npm install axios
   # or
   yarn add axios
   ```

4. **Add provided files (`src/App.tsx`, `src/components/BookTable.tsx`, `src/components/FilterBar.tsx`).**

5. **Start the frontend:**
   ```sh
   npm start
   # or
   yarn start
   ```
   The UI will open at [http://localhost:3000](http://localhost:3000).

---

## Usage

- The web UI loads the list of book recommendations and lets you filter by genre, minimum number of ratings, and minimum average rating.
- Use the backend `/refresh` endpoint (POST) to rescrape and refresh the data (e.g., via a button or scheduled job).

---

## Next Steps

- Implement the real podcast notes scraper in `backend/app/scraper.py`.
- Integrate Goodreads or another book metadata API.
- Improve the UI for richer filtering and book details.
- Deploy backend/frontend (e.g., Vercel, Netlify, or a VPS).

---

## Troubleshooting

- If you encounter CORS issues, ensure the backend's CORS middleware allows requests from your frontend's URL.
- For API rate limits or scraping captchas, consider caching or using a proxy.

---