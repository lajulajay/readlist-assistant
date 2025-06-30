/**
 * BookDetail Component - Individual Book Information Display
 * 
 * This component displays detailed information about a specific book,
 * including metadata, ratings, episode information, and external links.
 * 
 * Features:
 * - Comprehensive book metadata display
 * - Rating and review count visualization
 * - Genre tags and categorization
 * - Episode tracking information
 * - External links to source and Goodreads
 * - Responsive layout with image support
 * - Navigation back to book list
 * 
 * Data Display:
 * - Title, author, and summary
 * - Publication details (date, pages, format)
 * - Rating statistics and genre tags
 * - Episode source information
 * - ISBN and language metadata
 * 
 * @author ReadList Assistant Team
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Rating,
  Chip,
  Grid as MuiGrid,
  CircularProgress,
  Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import axios from 'axios';
import { API_ENDPOINTS } from '../config';

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

const isImageUrl = (url: string) => {
  const ext = url.split('.').pop()?.toLowerCase();
  return ext && [ 'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg' ].includes(ext);
};

const BookDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBook = async () => {
      try {
        const response = await axios.get(API_ENDPOINTS.book(Number(id)));
        setBook(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch book details');
        setLoading(false);
      }
    };

    fetchBook();
  }, [id]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !book) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" minHeight="60vh">
        <Typography color="error" gutterBottom>
          {error || 'Book not found'}
        </Typography>
        <Button
          variant="contained"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/')}
        >
          Back to List
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Button
        variant="outlined"
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/')}
        sx={{ mb: 3 }}
      >
        Back to List
      </Button>

      <MuiGrid container spacing={4}>
        <MuiGrid item xs={12} md={4} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            {book.source_url && isImageUrl(book.source_url) && (
              <Box
                component="img"
                src={book.source_url}
                alt={book.title}
                sx={{
                  width: '100%',
                  height: 'auto',
                  objectFit: 'cover',
                }}
              />
            )}
          </Card>
        </MuiGrid>

        <MuiGrid item xs={12} md={8} sx={{ display: 'flex' }}>
          <Card sx={{ width: '100%' }}>
            <CardContent>
              <Typography variant="h4" component="h1" gutterBottom>
                {book.title}
              </Typography>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                by {book.author}
              </Typography>

              <Box sx={{ my: 2 }}>
                {book.genres && book.genres.map((genre) => (
                  <Chip key={genre} label={genre} color="primary" sx={{ mr: 1 }} />
                ))}
                <Rating value={book.avg_rating} precision={0.1} readOnly />
                <Typography variant="body2" color="text.secondary" component="span" sx={{ ml: 1 }}>
                  ({book.num_ratings} ratings)
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {book.summary && (
                <Typography variant="body1" paragraph>
                  {book.summary}
                </Typography>
              )}

              {book.episode_id && (
                <>
                  <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                    Featured in Episode
                  </Typography>
                  <Typography variant="subtitle1" gutterBottom>
                    {book.episode_title}
                  </Typography>
                </>
              )}

              {book.source_url && (
                <Box sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    href={book.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View Source
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </MuiGrid>
      </MuiGrid>
    </Box>
  );
};

export default BookDetail; 