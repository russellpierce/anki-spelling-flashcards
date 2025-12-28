"""Cache management utilities for HTTP request caching.

This module provides utilities for managing the requests_cache SQLite cache,
including busting cache entries for specific words.
"""

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import requests_cache
from loguru import logger


class CacheManager:
    """Manager for HTTP request cache operations."""

    CACHE_NAME = "spelling_words_cache"
    CACHE_BACKEND = "sqlite"
    CACHE_EXPIRE_AFTER = timedelta(days=30)

    def __init__(self):
        """Initialize the cache manager with a cached session."""
        self.session = requests_cache.CachedSession(
            self.CACHE_NAME,
            backend=self.CACHE_BACKEND,
            expire_after=self.CACHE_EXPIRE_AFTER,
        )

    def bust_word_cache(self, word: str) -> int:
        """Remove all cache entries related to a specific word.

        This includes:
        - Dictionary API lookups (elementary and collegiate)
        - Audio download URLs containing the word

        Args:
            word: The word to remove from cache

        Returns:
            Number of cache entries deleted

        Raises:
            ValueError: If word is empty or whitespace
        """
        if not word or not word.strip():
            msg = "word cannot be empty"
            raise ValueError(msg)

        word = word.strip()
        deleted_count = 0

        logger.debug(f"Busting cache for word: '{word}'")

        # Get all URLs from cache
        cache = self.session.cache
        urls_to_delete = []

        # Iterate through all cached responses
        for key in cache.responses:
            # Parse the URL from the key
            # In requests-cache, keys are typically URLs or contain URLs
            url = key if isinstance(key, str) else str(key)

            # Check if this URL is related to the word
            if self._is_word_related_url(url, word):
                urls_to_delete.append(key)
                logger.debug(f"Found cache entry to delete: {url}")

        # Delete the identified URLs
        for key in urls_to_delete:
            try:
                cache.delete(keys=key)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache entry {key}: {e}")

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} cache entries for word '{word}'")
        else:
            logger.info(f"No cache entries found for word '{word}'")

        return deleted_count

    def _is_word_related_url(self, url: str, word: str) -> bool:
        """Check if a URL is related to a specific word.

        Args:
            url: The URL to check
            word: The word to match against

        Returns:
            True if the URL is related to the word, False otherwise
        """
        # Parse the URL
        parsed = urlparse(url)
        path = parsed.path.lower()
        word_lower = word.lower()

        # Check if word appears in the path (for dictionary API lookups)
        # e.g., /api/v3/references/sd2/json/apple
        if f"/{word_lower}" in path or path.endswith(word_lower):
            return True

        # Check if word appears in query parameters
        # This might catch some audio URLs depending on structure
        query_params = parse_qs(parsed.query)
        for param_values in query_params.values():
            for value in param_values:
                if word_lower in value.lower():
                    return True

        # Check if the audio filename contains the word
        # Audio URLs often have the word in the filename
        # e.g., https://.../audio/.../apple_001.mp3
        return word_lower in url.lower()

    def clear_all_cache(self) -> None:
        """Clear all cache entries.

        This removes all cached HTTP responses.
        """
        logger.debug("Clearing all cache entries")
        self.session.cache.clear()
        logger.info("All cache entries cleared")

    def get_cache_info(self) -> dict:
        """Get information about the cache.

        Returns:
            Dictionary with cache statistics
        """
        cache = self.session.cache
        response_count = len(cache.responses)

        return {
            "cache_name": self.CACHE_NAME,
            "backend": self.CACHE_BACKEND,
            "response_count": response_count,
            "expire_after": str(self.CACHE_EXPIRE_AFTER),
        }
