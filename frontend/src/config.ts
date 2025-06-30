/**
 * Configuration Settings for ReadList Assistant Frontend
 * 
 * This file contains all configuration constants, API endpoints, and
 * environment-specific settings used throughout the frontend application.
 * 
 * Configuration Areas:
 * - API base URL and endpoint definitions
 * - Environment detection and flags
 * - Development vs production settings
 * 
 * API Endpoints:
 * - Books: Main book listing and filtering endpoint
 * - Individual book details endpoint
 * - All endpoints use the configured API_BASE_URL
 * 
 * Environment Variables:
 * - REACT_APP_API_BASE_URL: Backend API base URL
 * - NODE_ENV: Development/production environment flag
 * 
 * @author ReadList Assistant Team
 */

// API Configuration - Base URL for backend communication
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// API Endpoints - All backend API routes
export const API_ENDPOINTS = {
  books: `${API_BASE_URL}/api/books`, // Main books endpoint for listing and filtering
  book: (id: number) => `${API_BASE_URL}/api/books/${id}`, // Individual book details
};

// Environment Configuration - Runtime environment detection
export const ENV = {
  isDevelopment: process.env.NODE_ENV === 'development', // Development mode flag
  isProduction: process.env.NODE_ENV === 'production',   // Production mode flag
}; 