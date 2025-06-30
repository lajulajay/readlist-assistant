# Scripts Directory

This directory contains various scripts for managing the readlist assistant backend.

## Essential Scripts (Keep)

### Core Functionality
- `populate_db.py` - Main script to populate the database with book recommendations from episodes
- `check_db.py` - Check database status and statistics
- `check_processed_episodes.py` - Check which episodes were processed and their parser types
- `process_specific_episodes.py` - Process specific episodes by ID
- `refresh_db.sh` - Shell script to refresh the database (includes email notifications)

### Utility Scripts
- `find_episode_offset.py` - Find the offset of a specific episode ID
- `find_episodes_by_title.py` - Find episodes by title search

## Temporary/Debug Scripts (Can be removed)

### Testing Scripts
- `test_llm_forced.py` - Test LLM parsing by forcing it (temporary validation)
- `test_llm_parsing.py` - Test LLM parsing on specific episodes (temporary validation)
- `test_manual_split.py` - Test manual split fallback (temporary validation)
- `test_hybrid_parsing.py` - Test hybrid parsing approach (temporary validation)
- `test_episode_parsing.py` - Test episode parsing (temporary validation)
- `test_regex.py` - Test regex patterns (temporary validation)

### Debug Scripts
- `debug_episode_content.py` - Debug episode content and sections (temporary)
- `debug_parsing_issues.py` - Debug parsing issues (temporary)
- `debug_manual_split.py` - Debug manual split logic (temporary)
- `debug_split.py` - Debug split logic (temporary)
- `identify_failed_episodes.py` - Identify failed episodes (temporary)

## Usage

### Main Population Script
```bash
# Populate database starting from offset 0
python scripts/populate_db.py

# Populate database starting from specific offset
python scripts/populate_db.py --start-offset 10
```

### Check Database Status
```bash
# Check overall database status
python scripts/check_db.py

# Check processed episodes
python scripts/check_processed_episodes.py
```

### Process Specific Episodes
```bash
# Process specific episodes
python scripts/process_specific_episodes.py <episode_id1> <episode_id2>
```

## Notes

- The hybrid parsing system uses manual split fallback first, then LLM backup when needed
- All episodes are tracked in the `processed_episodes` table regardless of whether books were found
- The system supports both "Book Recommendations:" and "Recommendations:" section headers 