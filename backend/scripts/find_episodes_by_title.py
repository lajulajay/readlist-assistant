#!/usr/bin/env python3
import asyncio
import logging
import sys
import argparse
from typing import List, Dict
import aiohttp

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

async def get_episode_details(session, episode_id: str) -> Dict:
    """Get episode details including title."""
    url = f"{API_BASE_URL}/api/episodes/{episode_id}/books"
    
    try:
        async with session.post(url, timeout=30) as response:
            if response.status == 200:
                result = await response.json()
                if result and len(result) > 0:
                    return {
                        "id": episode_id,
                        "title": result[0].get("episode_title", "Unknown"),
                        "book_count": len(result)
                    }
    except Exception as e:
        logger.debug(f"Error getting details for episode {episode_id}: {str(e)}")
    
    return None

async def search_episodes_by_keywords(session, keywords: List[str], max_episodes: int = 100):
    """Search for episodes containing specific keywords in their titles."""
    found_episodes = []
    
    # Search through episodes in batches
    offset = 0
    batch_size = 10
    
    while len(found_episodes) < max_episodes:
        try:
            # Get episode IDs for this batch
            url = f"{API_BASE_URL}/api/episodes/batch/ids"
            params = {"batch_size": batch_size, "offset": offset}
            
            async with session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    episode_ids = data.get("episode_ids", [])
                    
                    if not episode_ids:
                        break  # No more episodes
                    
                    # Get details for each episode in this batch
                    for episode_id in episode_ids:
                        episode_details = await get_episode_details(session, episode_id)
                        if episode_details:
                            # Check if any keyword matches the title
                            title_lower = episode_details["title"].lower()
                            for keyword in keywords:
                                if keyword.lower() in title_lower:
                                    found_episodes.append(episode_details)
                                    logger.info(f"Found: {episode_details['title']} (ID: {episode_id}, Books: {episode_details['book_count']})")
                                    break
                    
                    offset += batch_size
                else:
                    logger.warning(f"Failed to get episodes at offset {offset}")
                    break
                    
        except Exception as e:
            logger.error(f"Error searching episodes: {str(e)}")
            break
    
    return found_episodes

async def main():
    """Main function to search for episodes by keywords."""
    parser = argparse.ArgumentParser(description="Search for episodes by title keywords")
    parser.add_argument("keywords", nargs="+", help="Keywords to search for in episode titles")
    parser.add_argument("--max-episodes", type=int, default=100, help="Maximum episodes to search through")
    args = parser.parse_args()
    
    logger.info(f"Searching for episodes containing keywords: {args.keywords}")
    
    async with aiohttp.ClientSession() as session:
        found_episodes = await search_episodes_by_keywords(session, args.keywords, args.max_episodes)
        
        if found_episodes:
            logger.info(f"\nFound {len(found_episodes)} matching episodes:")
            for episode in found_episodes:
                logger.info(f"  - {episode['title']}")
                logger.info(f"    ID: {episode['id']}")
                logger.info(f"    Books: {episode['book_count']}")
                logger.info("")
        else:
            logger.info("No matching episodes found.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Search stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1) 