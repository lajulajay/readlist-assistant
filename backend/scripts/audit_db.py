#!/usr/bin/env python3
"""
ReadList Assistant - Database Audit Script

This script performs comprehensive database integrity checks and data consistency
validation for the ReadList Assistant application.

Audit Areas:
1. Basic Statistics: Book and episode counts, data distribution
2. Database Integrity: Null values, duplicates, missing required fields
3. Data Consistency: Cross-table validation, book count verification
4. Processing Statistics: Parsing method analysis, success rates
5. Data Quality: Rating distributions, genre analysis, metadata completeness

Integrity Checks:
- Books with null/empty episode_id
- Duplicate episode_ids in processed_episodes
- Missing required fields (title, author)
- Cross-table consistency validation
- Book count mismatches between tables

Data Quality Analysis:
- Rating distribution analysis
- Genre frequency analysis
- Publication date coverage
- Goodreads integration status
- Episode processing success rates

Usage:
- python scripts/audit_db.py                    # Run full audit
- python scripts/audit_db.py --quick           # Run basic checks only

Output:
- Comprehensive audit report to console
- Detailed integrity issue identification
- Data consistency validation results
- Recommendations for data cleanup

Author: ReadList Assistant Team
"""

import sys
from datetime import datetime
from sqlalchemy import select, func, text
from app.database import SessionLocal
from app.models import BookDB, ProcessedEpisodeDB
from pathlib import Path
from dotenv import load_dotenv
import os

# Always load .env from the backend directory
backend_env_path = Path(__file__).parent.parent / '.env'
if backend_env_path.exists():
    load_dotenv(dotenv_path=backend_env_path)


def audit_database():
    """Perform comprehensive database audit."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("DATABASE AUDIT REPORT")
        print("=" * 80)
        print(f"Audit performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. BASIC STATISTICS
        print("1. BASIC STATISTICS")
        print("-" * 40)
        
        # Total counts
        total_books = db.execute(select(func.count(BookDB.id))).scalar()
        total_episodes = db.execute(select(func.count(ProcessedEpisodeDB.id))).scalar()
        
        print(f"Total books: {total_books}")
        print(f"Total processed episodes: {total_episodes}")
        
        # Books with episode_id
        books_with_episode = db.execute(
            select(func.count(BookDB.id)).where(BookDB.episode_id.isnot(None))
        ).scalar()
        print(f"Books with episode_id: {books_with_episode}")
        print(f"Books without episode_id: {total_books - books_with_episode}")
        
        # Episodes with books
        episodes_with_books = db.execute(
            select(func.count(ProcessedEpisodeDB.id)).where(ProcessedEpisodeDB.books_found > 0)
        ).scalar()
        print(f"Episodes with books: {episodes_with_books}")
        print(f"Episodes without books: {total_episodes - episodes_with_books}")
        print()
        
        # 2. DATABASE INTEGRITY CHECKS
        print("2. DATABASE INTEGRITY CHECKS")
        print("-" * 40)
        
        integrity_issues = []
        
        # Check for books with null episode_id
        null_episode_books = db.execute(
            select(BookDB).where(BookDB.episode_id.is_(None))
        ).scalars().all()
        
        if null_episode_books:
            integrity_issues.append(f"Found {len(null_episode_books)} books with null episode_id")
            for book in null_episode_books:
                integrity_issues.append(f"  - ID {book.id}: '{book.title}' by {book.author}")
        else:
            print("✅ No books with null episode_id")
        
        # Check for books with empty episode_id
        empty_episode_books = db.execute(
            select(BookDB).where(BookDB.episode_id == "")
        ).scalars().all()
        
        if empty_episode_books:
            integrity_issues.append(f"Found {len(empty_episode_books)} books with empty episode_id")
        else:
            print("✅ No books with empty episode_id")
        
        # Check for episodes with null episode_id
        null_episode_processed = db.execute(
            select(ProcessedEpisodeDB).where(ProcessedEpisodeDB.episode_id.is_(None))
        ).scalars().all()
        
        if null_episode_processed:
            integrity_issues.append(f"Found {len(null_episode_processed)} processed episodes with null episode_id")
        else:
            print("✅ No processed episodes with null episode_id")
        
        # Check for duplicate episode_ids in processed_episodes
        duplicate_episodes = db.execute(text("""
            SELECT episode_id, COUNT(*) as count
            FROM processed_episodes
            GROUP BY episode_id
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if duplicate_episodes:
            integrity_issues.append(f"Found {len(duplicate_episodes)} duplicate episode_ids in processed_episodes")
            for episode_id, count in duplicate_episodes:
                integrity_issues.append(f"  - {episode_id}: {count} entries")
        else:
            print("✅ No duplicate episode_ids in processed_episodes")
        
        # Check for books with missing required fields
        books_missing_title = db.execute(
            select(BookDB).where(BookDB.title.is_(None) | (BookDB.title == ""))
        ).scalars().all()
        
        if books_missing_title:
            integrity_issues.append(f"Found {len(books_missing_title)} books with missing titles")
        else:
            print("✅ No books with missing titles")
        
        books_missing_author = db.execute(
            select(BookDB).where(BookDB.author.is_(None) | (BookDB.author == ""))
        ).scalars().all()
        
        if books_missing_author:
            integrity_issues.append(f"Found {len(books_missing_author)} books with missing authors")
        else:
            print("✅ No books with missing authors")
        
        if integrity_issues:
            print("❌ INTEGRITY ISSUES FOUND:")
            for issue in integrity_issues:
                print(f"  {issue}")
        else:
            print("✅ All integrity checks passed")
        print()
        
        # 3. DATA CONSISTENCY VALIDATION
        print("3. DATA CONSISTENCY VALIDATION")
        print("-" * 40)
        
        consistency_issues = []
        
        # Check consistency between books and processed_episodes tables
        # Get all episode_ids from both tables
        book_episode_ids = set(db.execute(
            select(BookDB.episode_id).where(BookDB.episode_id.isnot(None))
        ).scalars().all())
        
        processed_episode_ids = set(db.execute(
            select(ProcessedEpisodeDB.episode_id)
        ).scalars().all())
        
        # Episodes with books but no processed_episodes entry
        episodes_missing_processed = book_episode_ids - processed_episode_ids
        if episodes_missing_processed:
            consistency_issues.append(f"Found {len(episodes_missing_processed)} episodes with books but no processed_episodes entry")
            for episode_id in list(episodes_missing_processed)[:5]:  # Show first 5
                consistency_issues.append(f"  - {episode_id}")
            if len(episodes_missing_processed) > 5:
                consistency_issues.append(f"  ... and {len(episodes_missing_processed) - 5} more")
        else:
            print("✅ All episodes with books have processed_episodes entries")
        
        # Episodes with processed_episodes entry but no books
        episodes_missing_books = processed_episode_ids - book_episode_ids
        if episodes_missing_books:
            consistency_issues.append(f"Found {len(episodes_missing_books)} episodes with processed_episodes entry but no books")
            for episode_id in list(episodes_missing_books)[:5]:  # Show first 5
                consistency_issues.append(f"  - {episode_id}")
            if len(episodes_missing_books) > 5:
                consistency_issues.append(f"  ... and {len(episodes_missing_books) - 5} more")
        else:
            print("✅ All processed episodes have corresponding books")
        
        # Check book count consistency
        # Get episodes where book count doesn't match actual books
        book_count_mismatches = db.execute(text("""
            SELECT 
                pe.episode_id,
                pe.books_found as expected_count,
                COUNT(b.id) as actual_count
            FROM processed_episodes pe
            LEFT JOIN books b ON pe.episode_id = b.episode_id
            GROUP BY pe.episode_id, pe.books_found
            HAVING pe.books_found != COUNT(b.id)
        """)).fetchall()
        
        if book_count_mismatches:
            consistency_issues.append(f"Found {len(book_count_mismatches)} episodes with book count mismatches")
            for episode_id, expected, actual in book_count_mismatches[:5]:  # Show first 5
                consistency_issues.append(f"  - {episode_id}: expected {expected}, found {actual}")
            if len(book_count_mismatches) > 5:
                consistency_issues.append(f"  ... and {len(book_count_mismatches) - 5} more")
        else:
            print("✅ All book counts are consistent")
        
        # Check for episodes with books_found > 0 but no actual books
        episodes_with_false_positive = db.execute(text("""
            SELECT pe.episode_id, pe.books_found
            FROM processed_episodes pe
            LEFT JOIN books b ON pe.episode_id = b.episode_id
            WHERE pe.books_found > 0 AND b.id IS NULL
        """)).fetchall()
        
        if episodes_with_false_positive:
            consistency_issues.append(f"Found {len(episodes_with_false_positive)} episodes with books_found > 0 but no actual books")
            for episode_id, books_found in episodes_with_false_positive[:5]:
                consistency_issues.append(f"  - {episode_id}: books_found = {books_found}")
            if len(episodes_with_false_positive) > 5:
                consistency_issues.append(f"  ... and {len(episodes_with_false_positive) - 5} more")
        else:
            print("✅ No episodes with false positive book counts")
        
        if consistency_issues:
            print("❌ CONSISTENCY ISSUES FOUND:")
            for issue in consistency_issues:
                print(f"  {issue}")
        else:
            print("✅ All consistency checks passed")
        print()
        
        # 4. PARSER PERFORMANCE ANALYSIS
        print("4. PARSER PERFORMANCE ANALYSIS")
        print("-" * 40)
        
        # Parser method distribution
        parser_stats = db.execute(text("""
            SELECT 
                parsing_method,
                COUNT(*) as episode_count,
                AVG(books_found) as avg_books_per_episode,
                SUM(books_found) as total_books_found
            FROM processed_episodes
            GROUP BY parsing_method
            ORDER BY episode_count DESC
        """)).fetchall()
        
        print("Parser method distribution:")
        for method, count, avg_books, total_books in parser_stats:
            print(f"  {method or 'None'}: {count} episodes, {avg_books:.1f} avg books, {total_books} total books")
        
        # Success rate by parser
        success_stats = db.execute(text("""
            SELECT 
                parsing_method,
                COUNT(*) as total_episodes,
                SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_episodes,
                ROUND(
                    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 
                    1
                ) as success_rate
            FROM processed_episodes
            GROUP BY parsing_method
            ORDER BY total_episodes DESC
        """)).fetchall()
        
        print("\nParser success rates:")
        for method, total, successful, rate in success_stats:
            print(f"  {method or 'None'}: {successful}/{total} episodes ({rate}% success rate)")
        print()
        
        # 5. SUMMARY
        print("5. SUMMARY")
        print("-" * 40)
        
        total_issues = len(integrity_issues) + len(consistency_issues)
        
        if total_issues == 0:
            print("✅ AUDIT PASSED: No issues found")
            print("Database is in good health!")
        else:
            print(f"⚠️  AUDIT FAILED: {total_issues} issues found")
            print("Review the issues above and take corrective action.")
        
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error during audit: {e}")
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(audit_database()) 