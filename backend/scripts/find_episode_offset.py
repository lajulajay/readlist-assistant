#!/usr/bin/env python3
import asyncio
import sys
import argparse
from typing import Optional
import aiohttp

API_BASE_URL = "http://localhost:8000"

async def find_episode_offset(episode_id: str) -> Optional[int]:
    """Find the offset for a specific episode ID."""
    async with aiohttp.ClientSession() as session:
        offset = 0
        batch_size = 50  # Use larger batches for faster searching
        
        while True:
            try:
                url = f"{API_BASE_URL}/api/episodes/batch/ids"
                params = {
                    "batch_size": batch_size,
                    "offset": offset
                }
                
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        episode_ids = data.get("episode_ids", [])
                        
                        if not episode_ids:
                            print(f"Episode {episode_id} not found in the first {offset} episodes")
                            return None
                        
                        # Check if our episode is in this batch
                        if episode_id in episode_ids:
                            episode_index = episode_ids.index(episode_id)
                            actual_offset = offset + episode_index
                            print(f"Episode {episode_id} found at offset {actual_offset}")
                            return actual_offset
                        
                        offset += batch_size
                    else:
                        print(f"Error: {response.status}")
                        return None
                        
            except Exception as e:
                print(f"Error: {str(e)}")
                return None

async def main():
    parser = argparse.ArgumentParser(description="Find the offset for a specific episode ID")
    parser.add_argument("episode_id", help="Spotify episode ID to find")
    args = parser.parse_args()
    
    offset = await find_episode_offset(args.episode_id)
    if offset is not None:
        print(f"\nTo start populate_db.py from this episode, use:")
        print(f"python scripts/populate_db.py --start-from {offset}")

if __name__ == "__main__":
    asyncio.run(main()) 