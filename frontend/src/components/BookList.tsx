/**
 * BookList Component - Main Book Display and Filtering Interface
 * 
 * This component provides the primary interface for viewing, filtering, and
 * navigating through the book recommendations database. It includes advanced
 * filtering, sorting, pagination, and view mode options.
 * 
 * Features:
 * - Grid and list view modes
 * - Advanced filtering (search, genre, ratings)
 * - Multiple sorting options
 * - Pagination with configurable page size
 * - Responsive design for mobile and desktop
 * - Real-time search and filter updates
 * 
 * State Management:
 * - Books data and loading states
 * - Filter and sort preferences
 * - Pagination state
 * - View mode preferences
 * 
 * @author ReadList Assistant Team
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Rating,
  TextField,
  Box,
  MenuItem,
  CircularProgress,
  Grid,
  Pagination,
  ToggleButton,
  ToggleButtonGroup,
  Select,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_ENDPOINTS } from '../config';
import ViewListIcon from '@mui/icons-material/ViewList';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import SortIcon from '@mui/icons-material/Sort';

interface Book {
  id: number;
  title: string;
  author: string;
  summary?: string;
  genres?: string[];
  num_ratings?: number;
  avg_rating?: number;
  source_url?: string;
  goodreads_url?: string;
  episode_id?: string;
  episode_title?: string;
  episode_book_count?: number;
  publication_date?: string;
  num_pages?: number;
  format?: string;
  isbn?: string;
  language?: string;
  created_at?: string;
  updated_at?: string;
}

interface Filters {
  search: string;
  genre: string;
  min_ratings: string;
  min_rating: string;
}

interface SortOption {
  label: string;
  value: string;
}

const sortOptions: SortOption[] = [
  { label: 'Most Popular', value: 'num_ratings_desc' },
  { label: 'Highest Rated', value: 'avg_rating_desc' },
  { label: 'Title A-Z', value: 'title_asc' },
  { label: 'Title Z-A', value: 'title_desc' },
  { label: 'Author A-Z', value: 'author_asc' },
  { label: 'Author Z-A', value: 'author_desc' },
];

const ITEMS_PER_PAGE = 12;

const BookList = () => {
  const navigate = useNavigate();
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [genres, setGenres] = useState<string[]>([]);
  const [totalBooks, setTotalBooks] = useState(0);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Filters>({
    search: '',
    genre: '',
    min_ratings: '',
    min_rating: '',
  });
  const [sortBy, setSortBy] = useState('num_ratings_desc');

  useEffect(() => {
    const fetchGenres = async () => {
      const response = await axios.get(`${API_ENDPOINTS.books}/genres`);
      setGenres(response.data);
    };

    fetchGenres();
  }, []);

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.search) params.append('search', filters.search);
        if (filters.genre) params.append('genre', filters.genre);
        if (filters.min_ratings) params.append('min_ratings', filters.min_ratings);
        if (filters.min_rating) params.append('min_rating', filters.min_rating);
        params.append('sort', sortBy);
        params.append('skip', ((page - 1) * ITEMS_PER_PAGE).toString());
        params.append('limit', ITEMS_PER_PAGE.toString());

        const response = await axios.get(`${API_ENDPOINTS.books}/filter?${params.toString()}`);
        setBooks(response.data.books);
        setTotalBooks(response.data.total);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch books');
        setLoading(false);
      }
    };

    fetchBooks();
  }, [filters, sortBy, page]);

  const handleTextFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFilters(prev => ({ ...prev, [name]: value }));
    setPage(1); // Reset to first page on filter change
  };

  const handleSelectFilterChange = (event: SelectChangeEvent) => {
    const { name, value } = event.target;
    setFilters(prev => ({ ...prev, [name]: value }));
    setPage(1); // Reset to first page on filter change
  };

  const handleSortChange = (event: SelectChangeEvent) => {
    setSortBy(event.target.value);
    setPage(1);
  };

  const handleViewModeChange = (_: React.MouseEvent<HTMLElement>, newMode: 'grid' | 'list' | null) => {
    if (newMode !== null) {
      setViewMode(newMode);
    }
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading && !books.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !books.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              fullWidth
              label="Search"
              name="search"
              value={filters.search}
              onChange={handleTextFilterChange}
              placeholder="Search books..."
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>Genre</InputLabel>
              <Select
              name="genre"
              value={filters.genre}
                label="Genre"
                onChange={handleSelectFilterChange}
            >
              <MenuItem value="">All Genres</MenuItem>
                {genres.map((genre) => (
                  <MenuItem key={genre} value={genre}>
                    {genre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <TextField
              fullWidth
              type="number"
              label="Min Ratings"
              name="min_ratings"
              value={filters.min_ratings}
              onChange={handleTextFilterChange}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <TextField
              fullWidth
              type="number"
              label="Min Rating"
              name="min_rating"
              value={filters.min_rating}
              onChange={handleTextFilterChange}
              inputProps={{ step: 0.1, min: 0, max: 5 }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Sort By</InputLabel>
              <Select
                value={sortBy}
                label="Sort By"
                onChange={handleSortChange}
                startAdornment={
                  <SortIcon sx={{ mr: 1, color: 'action.active' }} />
                }
              >
                {sortOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Box>

      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewModeChange}
          aria-label="view mode"
        >
          <ToggleButton value="grid" aria-label="grid view">
            <Tooltip title="Grid View">
              <ViewModuleIcon />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="list" aria-label="list view">
            <Tooltip title="List View">
              <ViewListIcon />
            </Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {viewMode === 'grid' ? (
      <Grid container spacing={3}>
        {books.map((book) => (
            <Grid item key={book.id} xs={12} sm={6} md={4} lg={3}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                  <Typography gutterBottom variant="h6" component="h2" noWrap>
                  {book.title}
                </Typography>
                  <Typography color="text.secondary" gutterBottom noWrap>
                  by {book.author}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Rating value={book.avg_rating} precision={0.1} readOnly size="small" />
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                      ({typeof book.num_ratings === 'number' ? book.num_ratings.toLocaleString() : 'N/A'})
                  </Typography>
                </Box>
                {book.genres && book.genres.length > 0 && (
                  <Chip 
                    label={book.genres[0]} 
                    size="small" 
                    color="primary" 
                    sx={{ mr: 1, mb: 1 }} 
                  />
                )}
                {book.genres && book.genres.length > 1 && (
                  <Chip 
                    label={`+${book.genres.length - 1} more`} 
                    size="small" 
                    variant="outlined" 
                    sx={{ mr: 1, mb: 1 }} 
                  />
                )}
                {book.episode_id && (
                    <Typography variant="body2" color="text.secondary" gutterBottom noWrap>
                    Featured in: {book.episode_title}
                  </Typography>
                )}
              </CardContent>
              <CardActions>
                  <Button size="small" onClick={() => navigate(`/book/${book.id}`)}>
                  View Details
                </Button>
                {book.source_url && (
                  <Button size="small" href={book.source_url} target="_blank" rel="noopener noreferrer">
                    Source
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
      ) : (
        <Box sx={{ width: '100%', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px' }}>Title</th>
                <th style={{ textAlign: 'left', padding: '8px' }}>Author</th>
                <th style={{ textAlign: 'left', padding: '8px' }}>Genre</th>
                <th style={{ textAlign: 'center', padding: '8px' }}>Rating</th>
                <th style={{ textAlign: 'center', padding: '8px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {books.map((book) => (
                <tr key={book.id}>
                  <td style={{ padding: '8px' }}>{book.title}</td>
                  <td style={{ padding: '8px' }}>{book.author}</td>
                  <td style={{ padding: '8px' }}>{book.genres && book.genres.length > 0 ? book.genres[0] : '-'}</td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Rating value={book.avg_rating} precision={0.1} readOnly size="small" />
                      <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                        ({typeof book.num_ratings === 'number' ? book.num_ratings.toLocaleString() : 'N/A'})
                      </Typography>
                    </Box>
                  </td>
                  <td style={{ padding: '8px', textAlign: 'center' }}>
                    <Button size="small" onClick={() => navigate(`/book/${book.id}`)}>
                      Details
                    </Button>
                    {book.source_url && (
                      <Button size="small" href={book.source_url} target="_blank" rel="noopener noreferrer">
                        Source
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      )}

      {totalBooks > ITEMS_PER_PAGE && (
        <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
          <Pagination
            count={Math.ceil(totalBooks / ITEMS_PER_PAGE)}
            page={page}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
          />
        </Box>
      )}
    </Box>
  );
};

export default BookList; 