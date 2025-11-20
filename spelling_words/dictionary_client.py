"""Dictionary API Client for Merriam-Webster Elementary Dictionary.

This module provides a client for fetching word definitions and audio URLs
from the Merriam-Webster Elementary Dictionary API with automatic HTTP caching.
"""

import time

import requests
from loguru import logger
from requests_cache import CachedSession


class MerriamWebsterClient:
    """Client for Merriam-Webster Elementary Dictionary API.

    This client fetches word definitions and pronunciation audio URLs from the
    Merriam-Webster Elementary Dictionary API. It uses a cached session to
    minimize redundant API calls and implements retry logic for network errors.

    Attributes:
        api_key: Merriam-Webster API key
        session: Cached HTTP session for making requests
        base_url: Base URL for the Merriam-Webster Elementary Dictionary API
    """

    BASE_URL = "https://dictionaryapi.com/api/v3/references/sd/json"
    AUDIO_BASE_URL = "https://media.merriam-webster.com/audio/prons/en/us/mp3"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self, api_key: str, session: CachedSession):
        """Initialize the Merriam-Webster client.

        Args:
            api_key: Merriam-Webster Elementary Dictionary API key
            session: CachedSession instance for making HTTP requests

        Raises:
            ValueError: If api_key is empty or whitespace-only
        """
        if not api_key or not api_key.strip():
            msg = "API key cannot be empty"
            logger.error(msg)
            raise ValueError(msg)

        self.api_key = api_key.strip()
        self.session = session
        logger.debug(f"Initialized MerriamWebsterClient with API key: {self.api_key[:8]}...")

    def get_word_data(self, word: str) -> dict | None:
        """Fetch word data from Merriam-Webster API.

        Makes a GET request to the API with retry logic for timeouts.
        Returns None if the word is not found (API returns suggestions instead).

        Args:
            word: The word to look up

        Returns:
            Word data as a dictionary, or None if word not found

        Raises:
            ValueError: If word is empty
            requests.Timeout: If all retries fail due to timeout
            requests.HTTPError: If API returns non-200 status code
        """
        if not word or not word.strip():
            msg = "word cannot be empty"
            logger.error(msg)
            raise ValueError(msg)

        word = word.strip()
        url = f"{self.BASE_URL}/{word}"
        params = {"key": self.api_key}

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"Fetching word data for '{word}' (attempt {attempt + 1}/{self.MAX_RETRIES})")
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                # Check if word was found
                # If not found, API returns list of string suggestions instead of list of dicts
                if data and isinstance(data[0], str):
                    logger.info(f"Word '{word}' not found in dictionary. Suggestions: {data}")
                    return None

                logger.info(f"Successfully fetched data for word '{word}'")
                return data

            except requests.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Timeout fetching '{word}' on attempt {attempt + 1}, "
                        f"retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to fetch '{word}' after {self.MAX_RETRIES} attempts", exc_info=True)
                    raise

            except requests.HTTPError:
                logger.error(f"HTTP error fetching data for '{word}'", exc_info=True)
                raise

    def extract_definition(self, word_data: dict) -> str:
        """Extract the first definition from word data.

        Args:
            word_data: Word data dictionary from API

        Returns:
            The first definition as a string

        Raises:
            ValueError: If no definition found in data
        """
        if not word_data or not isinstance(word_data, list) or len(word_data) == 0:
            msg = "No definition found in word data"
            logger.error(msg)
            raise ValueError(msg)

        # Get first entry's shortdef
        entry = word_data[0]
        if "shortdef" not in entry or not entry["shortdef"]:
            msg = "No definition found in word data"
            logger.error(msg)
            raise ValueError(msg)

        definition = entry["shortdef"][0]
        logger.debug(f"Extracted definition: {definition}")
        return definition

    def extract_audio_urls(self, word_data: dict) -> list[str]:
        """Extract audio pronunciation URLs from word data.

        Constructs full URLs for all pronunciation audio files. Handles
        special subdirectory rules according to Merriam-Webster API:
        - Audio starting with "bix" -> subdirectory "bix"
        - Audio starting with "gg" -> subdirectory "gg"
        - Audio starting with number/punctuation -> subdirectory "number"
        - Otherwise -> subdirectory is first character

        Args:
            word_data: Word data dictionary from API

        Returns:
            List of audio URLs (may be empty if no audio available)
        """
        if not word_data or not isinstance(word_data, list) or len(word_data) == 0:
            return []

        urls = []
        entry = word_data[0]

        # Navigate to pronunciations
        if "hwi" not in entry or "prs" not in entry["hwi"]:
            logger.debug("No pronunciation data found")
            return []

        pronunciations = entry["hwi"]["prs"]

        for pron in pronunciations:
            if "sound" not in pron or "audio" not in pron["sound"]:
                continue

            audio_file = pron["sound"]["audio"]
            if not audio_file:
                continue

            # Determine subdirectory based on MW API rules
            subdirectory = self._get_audio_subdirectory(audio_file)

            # Construct full URL
            url = f"{self.AUDIO_BASE_URL}/{subdirectory}/{audio_file}.mp3"
            urls.append(url)
            logger.debug(f"Extracted audio URL: {url}")

        if not urls:
            logger.debug("No audio URLs found in word data")

        return urls

    def _get_audio_subdirectory(self, audio_file: str) -> str:
        """Determine the subdirectory for an audio file based on MW API rules.

        Args:
            audio_file: The audio filename (without extension)

        Returns:
            The subdirectory name
        """
        if audio_file.startswith("bix"):
            return "bix"
        if audio_file.startswith("gg"):
            return "gg"
        if audio_file[0].isdigit() or not audio_file[0].isalpha():
            return "number"
        return audio_file[0]
