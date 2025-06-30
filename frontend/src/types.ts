/**
 * TypeScript Type Definitions for ReadList Assistant
 * 
 * This file contains the core TypeScript interfaces and type definitions
 * used throughout the frontend application for type safety and data validation.
 * 
 * Key Types:
 * - Book: Core book entity with all metadata fields
 * - Filter interfaces for search and filtering
 * - API response types for backend communication
 * 
 * @author ReadList Assistant Team
 */

export interface Book {
  id: number;
  title: string;
  author: string;
  description: string;
  rating: number;
  created_at: string;
  updated_at: string;
  source_url?: string;
  summary?: string;
  genre?: string;
  num_ratings?: number;
  avg_rating?: number;
} 