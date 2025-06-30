/**
 * ReadList Assistant - Main React Application
 * 
 * This is the root component of the ReadList Assistant frontend application.
 * It provides the main layout, routing, and theme configuration for the book
 * recommendation management system.
 * 
 * Features:
 * - Material-UI theme configuration
 * - React Router for navigation
 * - Responsive layout with navigation bar
 * - Book list and detail views
 * 
 * @author ReadList Assistant Team
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { Box, Container } from '@mui/material';
import Navbar from './components/Navbar';
import BookList from './components/BookList';
import BookDetail from './components/BookDetail';

// Create a Material-UI theme instance with custom styling
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2', // Blue primary color
    },
    secondary: {
      main: '#dc004e', // Pink secondary color
    },
    background: {
      default: '#f5f5f5', // Light gray background
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
});

/**
 * Main App component that renders the application layout and routing
 */
function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar />
          <Container component="main" sx={{ mt: 4, mb: 4, flex: 1 }}>
            <Routes>
              <Route path="/" element={<BookList />} />
              <Route path="/book/:id" element={<BookDetail />} />
            </Routes>
          </Container>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;