#!/usr/bin/env python3
"""
ReadList Assistant - Database Population Script

This script populates the database with book recommendations from Spotify podcast episodes.
It uses the hybrid parsing system to extract books from episode descriptions and enriches
them with Goodreads data.

Key Features:
- Batch processing of episodes with configurable batch size
- Hybrid parsing system (manual split + OpenAI LLM backup)
- Episode tracking and duplicate prevention
- Retry logic with exponential backoff
- Rate limiting and error handling
- Progress tracking and statistics
- Support for resuming from specific offsets

Parsing System:
- Manual split fallback: Fast, accurate parsing (94.7% accuracy)
- OpenAI LLM backup: AI-powered parsing for edge cases
- Episode tracking: All episodes processed, regardless of book count
- Flexible section detection: Multiple recommendation header formats

Usage:
- python scripts/populate_db.py                    # Start from most recent episodes
- python scripts/populate_db.py --start-offset 10  # Start from offset 10

Configuration:
- BATCH_SIZE: Number of episodes to process per batch (default: 3)
- DELAY_BETWEEN_BATCHES: Seconds between batches (default: 30)
- DELAY_BETWEEN_EPISODES: Seconds between individual episodes (default: 5)
- REQUEST_TIMEOUT: API request timeout in seconds (default: 300)

Author: ReadList Assistant Team
"""

import asyncio
import logging
import sys
import traceback
import argparse
from typing import List, Optional, Set
import aiohttp
import json
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"
BATCH_SIZE = 3  # Reduced from 5 to 3
DELAY_BETWEEN_BATCHES = 30  # Reduced from 120 to 30 seconds for testing
DELAY_BETWEEN_EPISODES = 5  # New: shorter delay between individual episodes
REQUEST_TIMEOUT = 300  # 5 minutes
MAX_RETRIES = 3
DB_NAME = "readlist_assistant"

def get_processed_episodes() -> Set[str]:
    """Get a set of episode IDs that have already been successfully processed (found books)."""
    try:
        conn = psycopg2.connect(dbname=DB_NAME)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT episode_id 
                FROM processed_episodes 
                WHERE episode_id IS NOT NULL AND success = true
            """)
            episodes = {row['episode_id'] for row in cur.fetchall()}
            logger.info(f"Found {len(episodes)} episodes that were successfully processed (found books)")
            return episodes
    except Exception as e:
        logger.error(f"Error getting processed episodes: {str(e)}")
        return set()
    finally:
        if 'conn' in locals():
            conn.close()

def get_failed_episodes_stats() -> dict:
    """Get statistics about episodes that failed to find books."""
    try:
        conn = psycopg2.connect(dbname=DB_NAME)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) as total_failed,
                       COUNT(CASE WHEN parsing_method = 'none' THEN 1 END) as none_method,
                       COUNT(CASE WHEN parsing_method = 'manual_split' THEN 1 END) as manual_split,
                       COUNT(CASE WHEN parsing_method = 'openai_llm' THEN 1 END) as openai_llm
                FROM processed_episodes 
                WHERE success = false
            """)
            stats = cur.fetchone()
            return {
                'total_failed': stats['total_failed'],
                'none_method': stats['none_method'],
                'manual_split': stats['manual_split'],
                'openai_llm': stats['openai_llm']
            }
    except Exception as e:
        logger.error(f"Error getting failed episodes stats: {str(e)}")
        return {'total_failed': 0, 'none_method': 0, 'manual_split': 0, 'openai_llm': 0}
    finally:
        if 'conn' in locals():
            conn.close()

def is_rate_limit_error(exception):
    """Check if an exception is related to rate limiting."""
    if isinstance(exception, aiohttp.ClientResponseError):
        return exception.status in (429, 503)  # Too Many Requests or Service Unavailable
    if isinstance(exception, asyncio.TimeoutError):
        return True
    return False

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    retry_error_callback=lambda retry_state: logger.error(f"Failed after {retry_state.attempt_number} attempts")
)
async def process_episode(session, episode_id: str) -> dict:
    """Process a single episode with retry logic."""
    url = f"{API_BASE_URL}/api/episodes/{episode_id}/books"
    
    logger.info(f"Processing episode {episode_id}")
    
    try:
        async with session.post(url, timeout=REQUEST_TIMEOUT) as response:
            response_text = await response.text()
            logger.debug(f"Response status: {response.status}")
            logger.debug(f"Response text: {response_text[:200]}...")  # Log first 200 chars
            
            if response.status == 429:  # Too Many Requests
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=429,
                    message="Rate limited"
                )
            
            response.raise_for_status()
            result = await response.json()
            
            # Log parsing results
            books_count = len(result)
            if books_count > 0:
                logger.info(f"✅ Episode {episode_id}: Successfully extracted {books_count} books")
                # Log first few books for debugging
                for i, book in enumerate(result[:3]):
                    logger.debug(f"  Book {i+1}: {book.get('title', 'N/A')} by {book.get('author', 'N/A')}")
                if books_count > 3:
                    logger.debug(f"  ... and {books_count - 3} more books")
            else:
                logger.warning(f"⚠️ Episode {episode_id}: No books extracted")
            
            return result
            
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error processing episode {episode_id}: {str(e)}")
        raise
    except asyncio.TimeoutError as e:
        logger.error(f"Timeout processing episode {episode_id}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing episode {episode_id}: {str(e)}", exc_info=True)
        raise

async def test_connection(session) -> bool:
    """Test if the API is accessible."""
    try:
        async with session.get(f"{API_BASE_URL}/docs", timeout=10) as response:
            response.raise_for_status()
            logger.info("Successfully connected to API")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to API: {str(e)}")
        return False

async def get_batch_episode_ids(session, offset: int, batch_size: int) -> List[str]:
    """Get episode IDs for a batch without processing them."""
    url = f"{API_BASE_URL}/api/episodes/batch/ids"
    params = {
        "batch_size": batch_size,
        "offset": offset
    }
    
    try:
        async with session.get(url, params=params, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("episode_ids", [])
            else:
                logger.warning(f"Failed to get episode IDs for batch at offset {offset}: {response.status}")
                return []
    except Exception as e:
        logger.warning(f"Error getting episode IDs for batch at offset {offset}: {str(e)}")
        return []

async def main(start_from_offset: int = 0):
    """Main function to populate the database with book recommendations."""
    start_time = time.time()
    total_books = 0
    episodes_processed = 0
    episodes_with_books = 0
    episodes_without_books = 0
    
    logger.info("Starting database population process...")
    if start_from_offset > 0:
        logger.info(f"Starting from episode offset: {start_from_offset}")
    
    # Get already processed episodes
    processed_episodes = get_processed_episodes()
    
    # Get failed episodes statistics
    failed_stats = get_failed_episodes_stats()
    logger.info(f"Found {failed_stats['total_failed']} episodes that previously failed to find books:")
    logger.info(f"  - {failed_stats['none_method']} episodes with 'none' parsing method")
    logger.info(f"  - {failed_stats['manual_split']} episodes with 'manual_split' parsing method")
    logger.info(f"  - {failed_stats['openai_llm']} episodes with 'openai_llm' parsing method")
    logger.info(f"These episodes will be re-processed with improved parsing logic.")
    
    async with aiohttp.ClientSession() as session:
        # Test connection first
        if not await test_connection(session):
            logger.error("Could not connect to API. Exiting...")
            return
        
        offset = start_from_offset
        while True:
            try:
                logger.info(f"Processing batch at offset {offset}")
                
                # Get episode IDs for this batch
                batch_episodes = await get_batch_episode_ids(session, offset, BATCH_SIZE)
                if not batch_episodes:
                    logger.info("No more episodes to process")
                    break
                
                # Check if all episodes in this batch are already processed
                unprocessed_episodes = [ep for ep in batch_episodes if ep not in processed_episodes]
                if not unprocessed_episodes:
                    logger.info(f"All episodes in batch at offset {offset} already processed, skipping...")
                    offset += BATCH_SIZE
                    continue
                
                logger.info(f"Found {len(unprocessed_episodes)} unprocessed episodes in this batch")
                
                # Process each episode individually
                for episode_id in unprocessed_episodes:
                    try:
                        logger.info(f"Processing episode {episode_id} ({episodes_processed + 1} total)")
                        result = await process_episode(session, episode_id)
                        
                        books_in_episode = len(result)
                        total_books += books_in_episode
                        episodes_processed += 1
                        
                        if books_in_episode > 0:
                            episodes_with_books += 1
                        else:
                            episodes_without_books += 1
                        
                        logger.info(f"Episode {episode_id} complete. Found {books_in_episode} books.")
                        logger.info(f"Total books so far: {total_books}")
                        logger.info(f"Success rate: {episodes_with_books}/{episodes_processed} episodes with books ({episodes_with_books/episodes_processed*100:.1f}%)")
                        
                        # Add delay between episodes to avoid rate limiting
                        if episodes_processed % 3 == 0:  # Every 3 episodes
                            logger.info(f"Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
                            await asyncio.sleep(DELAY_BETWEEN_BATCHES)
                        else:
                            await asyncio.sleep(DELAY_BETWEEN_EPISODES)  # Short delay between episodes
                            
                    except Exception as e:
                        logger.error(f"Error processing episode {episode_id}: {str(e)}")
                        continue
                
                offset += BATCH_SIZE
                
            except KeyboardInterrupt:
                logger.info("Process interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                logger.info("Waiting 60 seconds before retrying...")
                await asyncio.sleep(60)
                continue
    
    duration = time.time() - start_time
    logger.info(f"Database population complete!")
    logger.info(f"Total episodes processed: {episodes_processed}")
    logger.info(f"Episodes with books: {episodes_with_books}")
    logger.info(f"Episodes without books: {episodes_without_books}")
    logger.info(f"Success rate: {episodes_with_books}/{episodes_processed} episodes with books ({episodes_with_books/episodes_processed*100:.1f}%)" if episodes_processed > 0 else "N/A")
    logger.info(f"Total books found: {total_books}")
    logger.info(f"Average books per episode: {total_books/episodes_processed:.1f}" if episodes_processed > 0 else "N/A")
    logger.info(f"Total duration: {duration:.2f} seconds")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Populate the database with book recommendations.")
        parser.add_argument("--start-from", type=int, default=0, help="Start from a specific episode offset")
        args = parser.parse_args()
        asyncio.run(main(args.start_from))
    except KeyboardInterrupt:
        logger.info("Process stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1) 