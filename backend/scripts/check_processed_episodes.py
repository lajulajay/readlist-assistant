#!/usr/bin/env python3
"""
Check which episodes were processed with LLM vs manual parsing.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_db
from app.models import ProcessedEpisodeDB

def check_processed_episodes():
    """Check processed episodes and their parser types."""
    
    db = next(get_db())
    try:
        episodes = db.query(ProcessedEpisodeDB).all()
        
        print(f"Total processed episodes: {len(episodes)}")
        
        # Count by parser type
        parser_counts = {}
        for episode in episodes:
            parser_type = episode.parsing_method or "unknown"
            parser_counts[parser_type] = parser_counts.get(parser_type, 0) + 1
        
        print(f"\nParser type breakdown:")
        for parser_type, count in parser_counts.items():
            print(f"  {parser_type}: {count}")
        
        # Show episodes processed with LLM
        llm_episodes = [e for e in episodes if e.parsing_method == 'openai_llm']
        print(f"\nEpisodes processed with LLM: {len(llm_episodes)}")
        
        if llm_episodes:
            print("First 5 LLM-processed episodes:")
            for episode in llm_episodes[:5]:
                print(f"  {episode.episode_id}: {episode.episode_title}")
        else:
            print("No episodes were processed with LLM")
        
        # Show episodes processed with manual parsing
        manual_episodes = [e for e in episodes if e.parsing_method == 'manual_split']
        print(f"\nEpisodes processed with manual parsing: {len(manual_episodes)}")
        
        if manual_episodes:
            print("First 5 manual-processed episodes:")
            for episode in manual_episodes[:5]:
                print(f"  {episode.episode_id}: {episode.episode_title}")
    finally:
        db.close()

if __name__ == "__main__":
    check_processed_episodes() 