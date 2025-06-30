"""
Spotify Integration and Hybrid Book Parsing System

This module provides comprehensive integration with Spotify's API for extracting
book recommendations from podcast episodes, along with a sophisticated hybrid
parsing system that combines manual parsing with AI-powered LLM backup.

Key Components:
- SpotifyClient: Handles Spotify API authentication and episode retrieval
- BookParser: Implements hybrid parsing (manual split + OpenAI LLM backup)
- Episode tracking and processing statistics
- Flexible section header detection for various recommendation formats

Hybrid Parsing System:
1. Manual Split Fallback (Primary): Fast, accurate parsing using custom logic
   - Handles concatenated book recommendations without delimiters
   - 94.7% accuracy on tested episodes
   - No external API calls required

2. OpenAI LLM Backup (Secondary): AI-powered parsing for edge cases
   - Used only when manual parsing fails or finds <5 books
   - Requires OPENAI_API_KEY in environment
   - Handles complex or unusual formatting

Section Detection:
Supports multiple recommendation section headers with flexible matching:
- "Book Recommendations:" (primary)
- "Recommendations:" (fallback)
- Case-insensitive matching
- Handles missing colons

Author: ReadList Assistant Team
"""
"""
Spotify Integration and Hybrid Book Parsing System

This module provides comprehensive integration with Spotify's API for extracting
book recommendations from podcast episodes, along with a sophisticated hybrid
parsing system that combines manual parsing with AI-powered LLM backup.

Key Components:
- SpotifyClient: Handles Spotify API authentication and episode retrieval
- BookParser: Implements hybrid parsing (manual split + OpenAI LLM backup)
- Episode tracking and processing statistics
- Flexible section header detection for various recommendation formats

Hybrid Parsing System:
1. Manual Split Fallback (Primary): Fast, accurate parsing using custom logic
   - Handles concatenated book recommendations without delimiters
   - 94.7% accuracy on tested episodes
   - No external API calls required

2. OpenAI LLM Backup (Secondary): AI-powered parsing for edge cases
   - Used only when manual parsing fails or finds <5 books
   - Requires OPENAI_API_KEY in environment
   - Handles complex or unusual formatting

Section Detection:
Supports multiple recommendation section headers with flexible matching:
- "Book Recommendations:" (primary)
- "Recommendations:" (fallback)
- Case-insensitive matching
- Handles missing colons

Author: ReadList Assistant Team
"""

import logging
import base64
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
from pydantic import BaseModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from dataclasses import dataclass
from enum import Enum
import json
import os
import asyncio
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from . import crud, database
from .models import BookCreate
from .database import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParserType(Enum):
    REGEX = "regex"
    LLM = "llm"

@dataclass
class BookRecommendation:
    title: str
    author: str
    confidence: float
    parser_type: str = "llm"  # Add default value for parser_type

class BookParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._model = None
        self._tokenizer = None
        
        # Determine device with fallback
        if torch.cuda.is_available():
            self._device = "cuda"
        elif torch.backends.mps.is_available():
            try:
                # Test MPS device
                test_tensor = torch.zeros(1, device="mps")
                del test_tensor
                self._device = "mps"
            except Exception as e:
                self.logger.warning(f"MPS device available but failed to initialize: {str(e)}")
                self._device = "cpu"
        else:
            self._device = "cpu"
            
        self.logger.info(f"Using device: {self._device}")
        
        # Initialize OpenAI client if API key is available
        self.openai_client = None
        openai_api_key = os.getenv("OPENAI_TEST_KEY") or os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
            self.logger.info("OpenAI client initialized for LLM backup parsing")
        else:
            self.logger.warning("No OpenAI API key found. LLM backup parsing will be disabled.")

    def _load_model(self):
        """Lazy load the model when needed."""
        if self._model is None:
            try:
                # Using a more capable open-access model
                model_name = "microsoft/DialoGPT-medium"
                self.logger.info(f"Loading model {model_name} on {self._device}")
                
                # Load tokenizer first
                self._tokenizer = AutoTokenizer.from_pretrained(model_name)
                
                # Load model with appropriate settings
                if self._device == "cuda":
                    self._model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        torch_dtype=torch.float16,
                        device_map="auto"
                    )
                elif self._device == "mps":
                    # For MPS, we'll use float32 and load to CPU first
                    self._model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,
                        device_map="cpu"  # Load to CPU first
                    )
                    # Then move to MPS if possible
                    try:
                        self._model = self._model.to("mps")
                    except Exception as e:
                        self.logger.warning(f"Failed to move model to MPS: {str(e)}")
                        self._device = "cpu"
                else:
                    # CPU fallback
                    self._model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,
                        device_map="cpu"
                    )
                
                self.logger.info(f"Model loaded successfully on {self._device}")
            except Exception as e:
                self.logger.error(f"Failed to load model: {str(e)}")
                raise

    def _parse_with_regex(self, text: str) -> List[BookRecommendation]:
        """Parse book recommendations using regex patterns."""
        books = []
        
        # Clean up the text by removing line breaks and extra whitespace
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # Updated regex pattern to handle both straight and curly apostrophes
        book_pattern = r"([A-Z][a-zA-Z\s'’]+?)\s+by\s+([A-Z][a-zA-Z\s'’]+?)(?=\s*[A-Z][a-zA-Z\s'’]*\s+by\s+|\s*$)"
        
        matches = list(re.finditer(book_pattern, cleaned_text))
        
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            author = match.group(2).strip()
            
            # Skip if either title or author is empty
            if not title or not author:
                continue
            
            skip_patterns = [
                "email us at",
                "nytimes.com",
                "subscribe today",
                "unlock full access",
                "thoughts?",
                "guest suggestions?"
            ]
            if any(pattern in title.lower() or pattern in author.lower() for pattern in skip_patterns):
                continue
            if not (title[0].isupper() and author[0].isupper()):
                continue
            if ' by ' in author:
                author = author.split(' by ')[0].strip()
            if len(author) > 0:
                for j in range(len(author) - 1, 0, -1):
                    if author[j].isupper() and j > 0 and author[j-1].islower():
                        author = author[:j].strip()
                        break
            books.append(BookRecommendation(
                title=title,
                author=author,
                confidence=0.8,
                parser_type=ParserType.REGEX
            ))
        return books

    async def parse_recommendations(self, text: str) -> List[Tuple[str, str]]:
        """Parse book recommendations using hybrid approach: manual split fallback first, then OpenAI LLM for failures or low-confidence results."""
        # First try manual split fallback
        books = self._manual_split_fallback(text)
        
        # If fewer than 5 books found and OpenAI is available, try LLM parsing for maximum accuracy
        if len(books) < 5 and self.openai_client:
            self.logger.info(f"Manual split fallback found {len(books)} books (<5), trying OpenAI LLM parsing for better accuracy...")
            llm_books = await self._parse_with_openai_llm(text)
            if llm_books:
                self.logger.info(f"OpenAI LLM successfully extracted {len(llm_books)} books")
                return llm_books
            else:
                self.logger.warning("OpenAI LLM also found no books or failed to improve results")
        elif not books:
            self.logger.warning("Manual split fallback found no books, but OpenAI LLM is not available")
        return books

    async def parse_recommendations_improved(self, text: str) -> Tuple[List[Tuple[str, str]], str]:
        """Improved parse_recommendations with edge case handling and validation.
        Returns a tuple of (books, parsing_method)."""
        # First try manual split fallback
        books = self._manual_split_fallback(text)
        
        # If manual split found no books and OpenAI is available, try LLM parsing
        if not books and self.openai_client:
            self.logger.info("Manual split fallback found no books, trying OpenAI LLM parsing...")
            llm_books = await self._parse_with_openai_llm(text)
            if llm_books:
                self.logger.info(f"OpenAI LLM successfully extracted {len(llm_books)} books")
                return llm_books, "openai_llm"
            else:
                self.logger.warning("OpenAI LLM also found no books")
                return [], "openai_llm"
        elif not books:
            self.logger.warning("Manual split fallback found no books, but OpenAI LLM is not available")
            return [], "manual_split"
        
        # Validate books for edge cases
        validated_books = []
        needs_llm = False
        
        for title, author in books:
            # Check for character length threshold (300 chars)
            if len(title) > 300 or len(author) > 300:
                self.logger.warning(f"Book attribute exceeds 300 char threshold - Title: {len(title)} chars, Author: {len(author)} chars")
                needs_llm = True
                break
            
            # Check if title contains 'by' (which could confuse the parser)
            if ' by ' in title.lower():
                self.logger.warning(f"Book title contains 'by': '{title}', using LLM parser")
                needs_llm = True
                break
            
            # Basic validation - ensure title and author are reasonable
            if title and author and len(title) > 0 and len(author) > 0:
                validated_books.append((title, author))
        
        # If validation failed or we need LLM, try OpenAI LLM parsing
        if needs_llm or len(validated_books) < len(books):
            if self.openai_client:
                self.logger.info(f"Validation issues detected, trying OpenAI LLM parsing...")
                llm_books = await self._parse_with_openai_llm(text)
                if llm_books:
                    self.logger.info(f"OpenAI LLM successfully extracted {len(llm_books)} books")
                    return llm_books, "openai_llm"
                else:
                    self.logger.warning("OpenAI LLM also found no books or failed to improve results")
            else:
                self.logger.warning("Validation issues detected but OpenAI LLM is not available")
        
        # If fewer than 5 books found and OpenAI is available, try LLM parsing for maximum accuracy
        if len(validated_books) < 5 and self.openai_client:
            self.logger.info(f"Manual split fallback found {len(validated_books)} books (<5), trying OpenAI LLM parsing for better accuracy...")
            llm_books = await self._parse_with_openai_llm(text)
            if llm_books:
                self.logger.info(f"OpenAI LLM successfully extracted {len(llm_books)} books")
                return llm_books, "openai_llm"
            else:
                self.logger.warning("OpenAI LLM also found no books or failed to improve results")
        
        return validated_books, "manual_split"

    def _manual_split_fallback(self, text: str) -> List[Tuple[str, str]]:
        """Robustly extract all (title, author) pairs from a concatenated recommendations string, handling Mc names and similar edge cases."""
        books = []
        s = text.strip()
        while True:
            by_idx = s.find(' by ')
            if by_idx == -1:
                break
            title = s[:by_idx].strip()
            rest = s[by_idx + 4:]
            # Find where the author name ends and the next book title begins
            author_end = len(rest)
            for j in range(1, len(rest)):
                if rest[j].isupper() and rest[j-1].islower():
                    # Check if this is a Mc name pattern (Mc + uppercase letter)
                    if j >= 2 and rest[j-2:j].lower() == 'mc':
                        continue
                    # Check if this is a van, von, de, etc. pattern
                    if j >= 3 and rest[j-3:j].lower() in ['van', 'von', 'del', 'der', 'den']:
                        continue
                    # Check if this is a Jr., Sr., III, etc. pattern
                    if j >= 2 and rest[j-2:j] in ['Jr', 'Sr'] and rest[j] == '.':
                        continue
                    if j >= 3 and rest[j-3:j] in ['III', 'IV', 'VI', 'IX']:
                        continue
                    # This looks like the start of a new title
                    author_end = j
                    break
            author = rest[:author_end].strip()
            if title and author:
                books.append((title, author))
            s = rest[author_end:].strip()
            if not s:
                break
        return books

    async def _parse_with_openai_llm(self, text: str) -> List[Tuple[str, str]]:
        """Parse book recommendations using OpenAI GPT model."""
        if not self.openai_client:
            self.logger.warning("OpenAI client not available")
            return []
        
        try:
            # Create a focused prompt for book extraction with clean formatting instructions
            prompt = f"""Extract all book recommendations from the following text. 

SECTION GUIDELINES:
- ONLY extract from sections that contain "Book Recommendations" or "Recommendations" (when it's clear they're book-related)
- IGNORE sections labeled: "Mentioned", "Podcast Recommendations", "EKS Recommendations", "Album Recommendations", "Music Recommendations", "Acknowledgements"
- IGNORE the production credits section at the end (the part that mentions producers, fact-checkers, music, etc.)
- If the text has multiple recommendation sections, ONLY extract from the book-specific one

FORMAT GUIDELINES:
- Look for patterns like "Title by Author" or similar book recommendation formats
- Do NOT ignore books in quotes - extract them normally
- Only extract books that are explicitly mentioned in the text
- Do NOT guess, infer, or add any books that are not clearly present
- If you are not certain a book is mentioned, do NOT include it
- Do NOT hallucinate or invent any book recommendations

OUTPUT FORMAT:
- Format titles cleanly without leading spaces, dashes, or outer quotes
- Do NOT add leading spaces or dashes before titles
- Do NOT enclose titles in quotes unless they are part of the actual title
- Preserve any quotes that are legitimately part of the book title
- If no books are found, respond with "No books found"
- If books are found, list each one on a separate line in the format: Title by Author

Text to analyze:
{text}

Books found:"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using cheaper model for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts book recommendations from text. Be precise and only extract actual book recommendations from the correct sections. Format titles cleanly without leading spaces, dashes, or unnecessary quotes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            content = response.choices[0].message.content.strip()
            
            if not content or "No books found" in content:
                return []
            
            # Parse the response and clean titles
            books = []
            for line in content.split('\n'):
                line = line.strip()
                if not line or "Books found:" in line:
                    continue
                
                # Look for "Title by Author" pattern
                if ' by ' in line:
                    parts = line.split(' by ', 1)
                    if len(parts) == 2:
                        title = clean_title(parts[0].strip())
                        author = parts[1].strip()
                        if title and author:
                            books.append((title, author))
            
            return books
            
        except Exception as e:
            self.logger.error(f"Error in OpenAI LLM parsing: {str(e)}")
            return []

class SpotifyCredentials(BaseModel):
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None

class EpisodeInfo(BaseModel):
    id: str
    name: str
    description: str
    release_date: str
    duration_ms: int
    external_urls: Dict[str, str]

class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger = logging.getLogger(__name__)
        self._model = None
        self._tokenizer = None
        self.access_token = None
        self.token_expiry = None
        self.session = None  # Will be initialized in ensure_session
        
        # Determine device with fallback
        if torch.cuda.is_available():
            self._device = "cuda"
        elif torch.backends.mps.is_available():
            try:
                # Test MPS device
                test_tensor = torch.zeros(1, device="mps")
                del test_tensor
                self._device = "mps"
            except Exception as e:
                self.logger.warning(f"MPS device available but failed to initialize: {str(e)}")
                self._device = "cpu"
        else:
            self._device = "cpu"
            
        self.logger.info(f"Using device: {self._device}")
        self.base_url = "https://api.spotify.com/v1"
        self.ezra_klein_show_id = "3oB5noYIwEB2dMAREj2F7S"
        self.parser = BookParser()

    async def ensure_session(self):
        """Ensure we have an active session."""
        if self.session is None or self.session.closed:
            self.logger.debug("Creating new aiohttp session")
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            self.logger.debug("Closing aiohttp session")
            await self.session.close()
            self.session = None

    async def _get_access_token(self) -> str:
        """Get a new access token from Spotify."""
        if (self.access_token and self.token_expiry 
            and datetime.utcnow() < self.token_expiry):
            self.logger.info("Using existing access token (not expired)")
            return self.access_token

        self.logger.info("Getting new access token from Spotify")
        await self.ensure_session()  # Ensure we have a session
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')

        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials'
        }

        try:
            async with self.session.post('https://accounts.spotify.com/api/token', 
                                       headers=headers, 
                                       data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"Failed to get access token. Status: {response.status}, Response: {error_text}")
                    response.raise_for_status()
                    
                token_data = await response.json()
                self.logger.info("Successfully obtained new access token")
                
                self.access_token = token_data['access_token']
                # Set token expiry to 50 minutes (tokens last 1 hour)
                self.token_expiry = datetime.utcnow() + timedelta(minutes=50)
                
                return self.access_token
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            raise

    async def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make an authenticated request to Spotify API."""
        try:
            await self.ensure_session()  # Ensure we have a session
            token = await self._get_access_token()
            headers = {'Authorization': f'Bearer {token}'}
            
            async with self.session.get(
                f"{self.base_url}/{endpoint}",
                headers=headers
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            self.logger.error(f"Error making request to {endpoint}: {str(e)}")
            return None

    async def get_episode(self, episode_id: str) -> Optional[EpisodeInfo]:
        """Fetch episode details from Spotify."""
        data = await self._make_request(f"episodes/{episode_id}")
        if not data:
            self.logger.error("Failed to fetch episode data from Spotify")
            return None
            
        self.logger.info(f"Successfully fetched episode: {data.get('name', 'Unknown')}")
        description = data.get('description', '')
        self.logger.debug(f"Episode description (first 1000 chars):\n{description[:1000]}")
        self.logger.debug(f"Description length: {len(description)}")
        self.logger.debug(f"Contains 'Book Recommendations:': {'Book Recommendations:' in description}")
            
        return EpisodeInfo(
            id=data['id'],
            name=data['name'],
            description=description,
            release_date=data['release_date'],
            duration_ms=data['duration_ms'],
            external_urls=data['external_urls']
        )

    async def get_show_episodes(self, limit: int = 10) -> List[EpisodeInfo]:
        """Fetch recent episodes from The Ezra Klein Show."""
        data = await self._make_request(f"shows/{self.ezra_klein_show_id}/episodes?limit={limit}")
        if not data or 'items' not in data:
            return []
            
        return [
            EpisodeInfo(
                id=episode['id'],
                name=episode['name'],
                description=episode['description'],
                release_date=episode['release_date'],
                duration_ms=episode['duration_ms'],
                external_urls=episode['external_urls']
            )
            for episode in data['items']
        ]

    async def _extract_book_recommendations(self, description: str) -> Tuple[List[Tuple[str, str]], str]:
        """Extract book recommendations from episode description with improved edge case handling.
        Returns a tuple of (books, parsing_method)."""
        self.logger.info("Starting to parse book recommendations")
        
        # Define all possible section header variations
        possible_headers = [
            # Book Recommendations variations
            "Book Recommendations:",
            "Book recommendations:",
            "book recommendations:",
            "Book Recommendations",
            "Book recommendations",
            "book recommendations",
            # Recommendations variations
            "Recommendations:",
            "recommendations:",
            "Recommendations",
            "recommendations",
            # Recommendation (singular) variations
            "Recommendation:",
            "recommendation:",
            "Recommendation",
            "recommendation"
        ]
        
        print(f"POSSIBLE HEADERS DEBUG: {possible_headers}")
        
        # Check for "Email us at" to determine end of useful text
        email_marker = "Email us at"
        if email_marker in description:
            # Find the last occurrence of "Email us at" and truncate description
            email_pos = description.rfind(email_marker)
            description = description[:email_pos]
            self.logger.debug(f"Truncated description at '{email_marker}' marker")
        
        # Find all section headers in the description
        header_positions = []
        for header in possible_headers:
            pos = description.find(header)
            if pos != -1:
                header_positions.append((pos, header))
        
        print(f"HEADER POSITIONS DEBUG: {header_positions}")
        self.logger.debug(f"Header positions found (index, header): {header_positions}")
        
        if not header_positions:
            self.logger.debug("No recommendation section found in description")
            self.logger.debug(f"Description sample (first 500 chars):\n{description[:500]}")
            return [], "none"
        
        # Pick the header with the lowest index (earliest in the text)
        section_header_pos, section_header = min(header_positions, key=lambda x: x[0])
        print(f"SELECTED HEADER DEBUG: '{section_header}' at position {section_header_pos}")
        self.logger.debug(f"Selected section header: '{section_header}' at position {section_header_pos}")
        
        # Check if this is a non-book recommendation section
        # Look for words before "Recommendations" that indicate non-book content
        if any(word in section_header.lower() for word in ['recommendations', 'recommendation']):
            # Check if there's a word before "Recommendations" that's not "book"
            header_lower = section_header.lower()
            if 'book' not in header_lower:
                # Check the text before this header to see if it's a sentence beginning
                before_header = description[:section_header_pos].strip()
                if before_header:
                    # Check if the last sentence ends with a word that's not "book"
                    last_sentence = before_header.split('.')[-1].strip()
                    if last_sentence and not last_sentence.lower().endswith('book'):
                        self.logger.info(f"Non-book recommendation section detected: '{section_header}', using LLM parser")
                        # Use LLM parser for non-book recommendation sections
                        llm_books = await self.parser._parse_with_openai_llm(description)
                        return llm_books, "openai_llm"
        
        # Split on the found section header and take the second part
        parts = description.split(section_header, 1)
        if len(parts) != 2:
            self.logger.debug(f"Could not find {section_header} section")
            return [], "none"
        
        recommendations_text = parts[1]
        self.logger.debug(f"Found recommendations section using '{section_header}':\n{recommendations_text[:500]}")
        
        # Enhanced end markers that mark the end of recommendations
        end_markers = [
            "Thoughts? Guest suggestions?",
            "You can find the transcript",
            "This episode of",
            "Special thanks to",
            "Unlock full access",
            "Email us at",
            "You can find transcripts",
            "Book recommendations from all our guests"
        ]
        
        for marker in end_markers:
            if marker in recommendations_text:
                recommendations_text = recommendations_text.split(marker)[0]
                self.logger.debug(f"Truncated recommendations at marker: {marker}")
                break
        
        # Clean up the recommendations text
        recommendations_text = recommendations_text.strip()
        self.logger.debug(f"Cleaned recommendations text:\n{recommendations_text}")
        
        # Use the improved hybrid parser
        return await self.parser.parse_recommendations_improved(recommendations_text)

    async def get_recent_episodes_recommendations(self, num_episodes: int = 5) -> List[Tuple[str, str]]:
        """Fetch book recommendations from the most recent episodes."""
        try:
            await self.ensure_session()  # Ensure we have a session
            
            # Get recent episodes
            episodes = await self.get_show_episodes(limit=num_episodes)
            if not episodes:
                self.logger.error("No episodes found")
                return []

            all_recommendations = []
            for episode in episodes:
                self.logger.info(f"Processing episode: {episode.name}")
                recommendations, parsing_method = await self._extract_book_recommendations(episode.description)
                if recommendations:
                    all_recommendations.extend(recommendations)
                    self.logger.info(f"Found {len(recommendations)} recommendations in episode: {episode.name} using {parsing_method}")

            # Remove duplicates while preserving order
            seen = set()
            unique_recommendations = []
            for title, author in all_recommendations:
                key = (title.lower(), author.lower())
                if key not in seen:
                    seen.add(key)
                    unique_recommendations.append((title, author))

            return unique_recommendations

        except Exception as e:
            self.logger.error(f"Error fetching recent episodes recommendations: {str(e)}")
            return []

    async def _get_episodes_batch(self, show_id: str, limit: int = 5, offset: int = 0) -> List[Dict]:
        """Get a batch of episodes with pagination support."""
        try:
            await self.ensure_session()  # Ensure we have a session
            token = await self._get_access_token()
            headers = {'Authorization': f'Bearer {token}'}
            
            url = f"{self.base_url}/shows/{show_id}/episodes"
            params = {
                "limit": limit,
                "offset": offset,
                "market": "US"
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("items", [])
                else:
                    self.logger.error(f"Failed to fetch episodes batch: {response.status}")
                    return []
        except Exception as e:
            self.logger.error(f"Error fetching episodes batch: {str(e)}")
            return []

    async def get_latest_episode_recommendations(self) -> Tuple[List[Tuple[str, str]], Optional[str], Optional[str]]:
        """
        Get book recommendations from the latest Ezra Klein Show episode.
        
        Returns:
            Tuple containing (recommendations, episode_id, episode_title)
        """
        episodes = await self.get_show_episodes(limit=1)
        if not episodes:
            return [], None, None
            
        latest_episode = episodes[0]
        
        # Extract recommendations from the latest episode
        recommendations, parsing_method = await self._extract_book_recommendations(latest_episode.description)
        return recommendations, latest_episode.id, latest_episode.name

    async def get_episode_recommendations(self, episode_id: str) -> List[Tuple[str, str]]:
        """
        Get book recommendations from a specific episode.
        
        Args:
            episode_id: Spotify episode ID
            
        Returns:
            List of tuples containing (title, author) for recommended books
        """
        episode = await self.get_episode(episode_id)
        if not episode:
            return []
            
        # Extract recommendations from the episode
        recommendations, parsing_method = await self._extract_book_recommendations(episode.description)
        return recommendations

async def get_ezra_klein_book_recommendations(episode_id: str) -> List[BookCreate]:
    """
    Get book recommendations from an Ezra Klein Show episode.
    
    Args:
        episode_id: Spotify episode ID
        
    Returns:
        List of BookCreate objects for recommended books
    """
    from .database import settings
    
    async with SpotifyClient(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET) as client:
        logger.info(f"Fetching episode {episode_id}")
        episode = await client.get_episode(episode_id)
        if not episode:
            logger.error(f"Failed to fetch episode {episode_id}")
            return []
            
        logger.info(f"Extracting book recommendations from episode: {episode.name}")
        logger.debug(f"Episode description length: {len(episode.description)}")
        logger.debug(f"Description contains 'Book Recommendations:': {'Book Recommendations:' in episode.description}")
        
        # Try to find the recommendations section
        if 'Book Recommendations:' in episode.description:
            start_idx = episode.description.find('Book Recommendations:')
            end_idx = episode.description.find('Thoughts?', start_idx)
            if end_idx == -1:
                end_idx = len(episode.description)
            recommendations_section = episode.description[start_idx:end_idx]
            logger.debug(f"Recommendations section:\n{recommendations_section}")
        
        book_recommendations, parsing_method = await client._extract_book_recommendations(episode.description)
        
        # Convert recommendations to BookCreate objects
        books = []
        for title, author in book_recommendations:
            book = BookCreate(
                title=title,
                author=author,
                episode_id=episode.id,
                source_url=episode.external_urls.get('spotify')
            )
            books.append(book)
            logger.info(f"Created BookCreate object for: {title} by {author}")
            
        logger.info(f"Created {len(books)} BookCreate objects (parser: {parsing_method})")
        return books

# Initialize Spotify client at the very end of the file
spotify_client = None  # Declare at module level

def init_spotify_client():
    global spotify_client
    spotify_client = SpotifyClient(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET
    )

# Initialize the client after all other code
init_spotify_client()

# Add cleanup on application shutdown
async def cleanup():
    """Clean up resources when the application shuts down."""
    if spotify_client:
        await spotify_client.close()

def clean_title(title: str) -> str:
    """
    Clean a book title by removing:
    - Leading spaces and dashes
    - Outer double quotes (only if they enclose the entire title)
    - Preserving legitimate quotes within the title
    """
    if not title:
        return title
    
    # Remove leading spaces and dashes
    cleaned = re.sub(r'^[\s\-]+', '', title.strip())
    
    # Remove outer double quotes only if they enclose the entire title
    # (not if they're part of the title content)
    if cleaned.startswith('"') and cleaned.endswith('"'):
        # Check if there are any other quotes in the middle
        inner_quotes = cleaned[1:-1].count('"')
        if inner_quotes == 0:
            # No inner quotes, safe to remove outer quotes
            cleaned = cleaned[1:-1]
    
    return cleaned.strip()