"""Profanity filter for username validation using Purgomalum API."""
import re
import json
import os
import logging
from typing import List, Tuple, Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

FILTER_CONFIG_FILE = "profanity_config.json"

# Purgomalum API endpoint (free, no auth required)
PURGOMALUM_API = "https://www.purgomalum.com/service/containsprofanity"

# Minimal fallback list if API is unavailable (only the most egregious words)
FALLBACK_BLOCKED_WORDS = [
    "fuck", "shit", "bitch", "nigger", "cunt", "asshole", "bastard"
]


class ProfanityFilter:
    """Filter for detecting offensive language in usernames using online API."""

    def __init__(self):
        self.custom_blocked_words = self._load_config()
        self.api_timeout = 2.0  # Timeout for API calls in seconds
        self.use_api = True

    def _load_config(self) -> List[str]:
        """Load custom blocked words from config file."""
        try:
            if os.path.exists(FILTER_CONFIG_FILE):
                with open(FILTER_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get('custom_blocked_words', [])
        except Exception as e:
            logger.error(f"Error loading profanity config: {e}")

        return []

    def _save_config(self) -> bool:
        """Save custom blocked words to config file."""
        try:
            config = {'custom_blocked_words': self.custom_blocked_words}
            with open(FILTER_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving profanity config: {e}")
            return False

    async def _check_api(self, text: str) -> Optional[bool]:
        """Check text using Purgomalum API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    PURGOMALUM_API,
                    params={'text': text},
                    timeout=aiohttp.ClientTimeout(total=self.api_timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.text()
                        # Purgomalum returns "true" or "false" as text
                        return result.strip().lower() == 'true'
                    else:
                        logger.warning(f"Purgomalum API returned status {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("Purgomalum API timeout")
            return None
        except Exception as e:
            logger.error(f"Error calling Purgomalum API: {e}")
            return None

    def _check_fallback(self, text: str) -> Tuple[bool, str]:
        """Fallback check using local word list."""
        if not text:
            return False, ""

        text_lower = text.lower()

        # Check custom blocked words first
        for word in self.custom_blocked_words:
            if word.lower() in text_lower:
                return True, word

        # Check fallback list
        for word in FALLBACK_BLOCKED_WORDS:
            if word in text_lower:
                return True, word

        return False, ""

    async def contains_profanity(self, text: str) -> Tuple[bool, str]:
        """
        Check if text contains profanity using API with fallback.

        Returns:
            Tuple of (contains_profanity, matched_word)
        """
        if not text:
            return False, ""

        # First check custom blocked words (instant)
        for word in self.custom_blocked_words:
            if word.lower() in text.lower():
                return True, f"custom:{word}"

        # Try API if enabled
        if self.use_api:
            api_result = await self._check_api(text)
            if api_result is not None:
                if api_result:
                    return True, "online-filter"
                else:
                    return False, ""

        # Fallback to local check if API failed or disabled
        is_profane, word = self._check_fallback(text)
        if is_profane:
            return True, f"fallback:{word}"

        return False, ""

    def get_blocked_words(self) -> List[str]:
        """Get list of custom blocked words."""
        return self.custom_blocked_words.copy()

    def add_blocked_word(self, word: str) -> bool:
        """Add a word to the custom blocked list."""
        word = word.lower().strip()
        if word and word not in self.custom_blocked_words:
            self.custom_blocked_words.append(word)
            return self._save_config()
        return False

    def remove_blocked_word(self, word: str) -> bool:
        """Remove a word from the custom blocked list."""
        word = word.lower().strip()
        if word in self.custom_blocked_words:
            self.custom_blocked_words.remove(word)
            return self._save_config()
        return False

    def reset_to_defaults(self) -> bool:
        """Clear all custom blocked words."""
        self.custom_blocked_words = []
        return self._save_config()

    def toggle_api(self, enabled: bool):
        """Enable or disable API usage."""
        self.use_api = enabled


# Global instance
profanity_filter = ProfanityFilter()
