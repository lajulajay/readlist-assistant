#!/usr/bin/env python3
import asyncio
import logging
import sys
import argparse
from typing import List
import aiohttp
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 300  # 5 minutes
DELAY_BETWEEN_EPISODES = 10  # seconds

async def process_specific_episode(session, episode_id: str) -> dict:
    """Process a specific episode by ID."""
    url = f"{API_BASE_URL}/api/episodes/{episode_id}/books"
    
    logger.info(f"Processing episode {episode_id}")
    
    try:
        async with session.post(url, timeout=REQUEST_TIMEOUT) as response:
            response_text = await response.text()
            logger.debug(f"Response status: {response.status}")
            
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
            logger.info(f"Found {len(result)} books in episode {episode_id}")
            return result
            
    except Exception as e:
        logger.error(f"Error processing episode {episode_id}: {str(e)}")
        return []

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

async def main():
    """Main function to process specific episodes."""
    parser = argparse.ArgumentParser(description="Process specific episodes by their IDs")
    parser.add_argument("episode_ids", nargs="+", help="List of episode IDs to process")
    parser.add_argument("--delay", type=int, default=DELAY_BETWEEN_EPISODES, 
                       help=f"Delay between episodes in seconds (default: {DELAY_BETWEEN_EPISODES})")
    args = parser.parse_args()
    
    start_time = time.time()
    total_books = 0
    episodes_processed = 0
    
    logger.info(f"Starting to process {len(args.episode_ids)} specific episodes...")
    
    async with aiohttp.ClientSession() as session:
        # Test connection first
        if not await test_connection(session):
            logger.error("Could not connect to API. Exiting...")
            return
        
        for episode_id in args.episode_ids:
            try:
                logger.info(f"Processing episode {episode_id} ({episodes_processed + 1}/{len(args.episode_ids)})")
                result = await process_specific_episode(session, episode_id)
                
                books_in_episode = len(result)
                total_books += books_in_episode
                episodes_processed += 1
                
                logger.info(f"Episode {episode_id} complete. Found {books_in_episode} books.")
                logger.info(f"Total books so far: {total_books}")
                
                # Add delay between episodes
                if episodes_processed < len(args.episode_ids):
                    logger.info(f"Waiting {args.delay} seconds before next episode...")
                    await asyncio.sleep(args.delay)
                    
            except Exception as e:
                logger.error(f"Error processing episode {episode_id}: {str(e)}")
                continue
    
    duration = time.time() - start_time
    logger.info(f"Processing complete!")
    logger.info(f"Total episodes processed: {episodes_processed}")
    logger.info(f"Total books found: {total_books}")
    logger.info(f"Total duration: {duration:.2f} seconds")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1) 