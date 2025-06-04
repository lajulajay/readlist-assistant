import React, { useEffect, useState } from "react";
import axios from "axios";
import BookTable from "./components/BookTable";
import FilterBar from "./components/FilterBar";

export interface Book {
  title: string;
  author: string;
  summary?: string;
  genre?: string;
  num_ratings?: number;
  avg_rating?: number;
  source_url?: string;
}

const API_URL = "http://localhost:8000";

function App() {
  const [books, setBooks] = useState<Book[]>([]);
  const [filters, setFilters] = useState({
    genre: "",
    minRatings: "",
    minRating: ""
  });

  const fetchBooks = async () => {
    const params: any = {};
    if (filters.genre) params.genre = filters.genre;
    if (filters.minRatings) params.min_ratings = filters.minRatings;
    if (filters.minRating) params.min_rating = filters.minRating;
    const res = await axios.get<Book[]>(`${API_URL}/books`, { params });
    setBooks(res.data);
  };

  useEffect(() => {
    fetchBooks();
    // eslint-disable-next-line
  }, [filters]);

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto" }}>
      <h1>ReadList Assistant</h1>
      <FilterBar filters={filters} setFilters={setFilters} />
      <BookTable books={books} />
    </div>
  );
}

export default App;