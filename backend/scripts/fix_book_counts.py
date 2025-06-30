#!/usr/bin/env python3
"""
Fix book count mismatches in processed_episodes table.
Updates books_found to match actual book counts in the books table.
"""

import sys
from datetime import datetime
from sqlalchemy import select, func, text, update
from app.database import SessionLocal
from app.models import BookDB, ProcessedEpisodeDB
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the backend directory
backend_env_path = Path(__file__).parent.parent / '.env'
if backend_env_path.exists():
    load_dotenv(dotenv_path=backend_env_path)

def fix_book_counts():
    """Fix book count mismatches in processed_episodes table."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("FIXING BOOK COUNT MISMATCHES")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Find episodes with book count mismatches
        mismatches = db.execute(text("""
            SELECT 
                pe.episode_id,
                pe.books_found as expected_count,
                COUNT(b.id) as actual_count
            FROM processed_episodes pe
            LEFT JOIN books b ON pe.episode_id = b.episode_id
            GROUP BY pe.episode_id, pe.books_found
            HAVING pe.books_found != COUNT(b.id)
            ORDER BY pe.episode_id
        """)).fetchall()
        
        print(f"Found {len(mismatches)} episodes with book count mismatches:")
        print("-" * 60)
        
        total_fixed = 0
        for episode_id, expected, actual in mismatches:
            print(f"Episode {episode_id}: expected {expected}, found {actual}")
            
            # Update the books_found count
            update_stmt = update(ProcessedEpisodeDB).where(
                ProcessedEpisodeDB.episode_id == episode_id
            ).values(books_found=actual)
            
            result = db.execute(update_stmt)
            if result.rowcount > 0:
                total_fixed += 1
                print(f"  ✅ Fixed: updated books_found to {actual}")
            else:
                print(f"  ❌ Failed to update")
        
        # Commit all changes
        db.commit()
        
        print()
        print(f"✅ Successfully fixed {total_fixed} out of {len(mismatches)} mismatches")
        
        # Verify the fix
        print()
        print("VERIFICATION:")
        print("-" * 40)
        
        remaining_mismatches = db.execute(text("""
            SELECT 
                pe.episode_id,
                pe.books_found as expected_count,
                COUNT(b.id) as actual_count
            FROM processed_episodes pe
            LEFT JOIN books b ON pe.episode_id = b.episode_id
            GROUP BY pe.episode_id, pe.books_found
            HAVING pe.books_found != COUNT(b.id)
        """)).fetchall()
        
        if remaining_mismatches:
            print(f"❌ {len(remaining_mismatches)} mismatches still remain:")
            for episode_id, expected, actual in remaining_mismatches[:10]:
                print(f"  - {episode_id}: expected {expected}, found {actual}")
            if len(remaining_mismatches) > 10:
                print(f"  ... and {len(remaining_mismatches) - 10} more")
        else:
            print("✅ All book count mismatches have been fixed!")
        
        # Check for episodes with false positive book counts
        print()
        print("CHECKING FOR FALSE POSITIVES:")
        print("-" * 40)
        
        false_positives = db.execute(text("""
            SELECT pe.episode_id, pe.books_found
            FROM processed_episodes pe
            LEFT JOIN books b ON pe.episode_id = b.episode_id
            WHERE pe.books_found > 0 AND b.id IS NULL
        """)).fetchall()
        
        if false_positives:
            print(f"Found {len(false_positives)} episodes with false positive book counts:")
            for episode_id, books_found in false_positives[:10]:
                print(f"  - {episode_id}: books_found = {books_found}")
            if len(false_positives) > 10:
                print(f"  ... and {len(false_positives) - 10} more")
            
            # Fix false positives
            print()
            print("Fixing false positives...")
            false_positive_fixed = 0
            for episode_id, books_found in false_positives:
                update_stmt = update(ProcessedEpisodeDB).where(
                    ProcessedEpisodeDB.episode_id == episode_id
                ).values(books_found=0)
                
                result = db.execute(update_stmt)
                if result.rowcount > 0:
                    false_positive_fixed += 1
            
            db.commit()
            print(f"✅ Fixed {false_positive_fixed} false positive book counts")
        else:
            print("✅ No false positive book counts found")
        
        print()
        print("=" * 80)
        print("FIX COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(fix_book_counts()) 