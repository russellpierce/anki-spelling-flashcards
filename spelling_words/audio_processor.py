"""Audio processor for downloading and processing audio files.

This module handles downloading audio files from URLs and converting them
to MP3 format for use in Anki flashcards.
"""

import time
from io import BytesIO

import requests
from loguru import logger
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from requests_cache import CachedSession


class AudioProcessor:
    """Handles audio file downloading and processing for Anki cards."""

    def download_audio(
        self, url: str, session: CachedSession, max_retries: int = 3
    ) -> bytes | None:
        """Download audio file from URL with retry logic.

        Args:
            url: URL of the audio file to download
            session: Cached session for HTTP requests
            max_retries: Maximum number of retry attempts on timeout (default: 3)

        Returns:
            Audio file content as bytes, or None if download failed (404 or invalid content type)

        Raises:
            ValueError: If URL is empty or whitespace
            requests.Timeout: If download times out after max retries
            requests.HTTPError: If HTTP error occurs (except 404)
        """
        if not url or not url.strip():
            msg = "URL cannot be empty"
            raise ValueError(msg)

        for attempt in range(max_retries):
            try:
                logger.debug(f"Downloading audio from {url} (attempt {attempt + 1}/{max_retries})")
                response = session.get(url, timeout=10)
                response.raise_for_status()

                # Validate Content-Type header
                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("audio/"):
                    logger.warning(f"Invalid Content-Type for audio: {content_type}")
                    return None

                logger.info(f"Successfully downloaded audio from {url}")
                return response.content

            except requests.Timeout:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, etc.
                    wait_time = 2**attempt
                    logger.warning(
                        f"Timeout on attempt {attempt + 1}/{max_retries}, "
                        f"retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                logger.error(f"Failed to download audio after {max_retries} attempts: {url}")
                raise

            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    logger.info(f"Audio not found (404): {url}")
                    return None
                logger.error(f"HTTP error downloading audio from {url}: {e}")
                raise

        # Explicit return if loop completes without returning
        return None

    def process_audio(self, audio_bytes: bytes, word: str) -> tuple[str, bytes]:
        """Process audio bytes and convert to MP3 format.

        Args:
            audio_bytes: Raw audio file content as bytes
            word: The word (used for filename generation)

        Returns:
            Tuple of (filename, mp3_bytes) where filename is sanitized
            and mp3_bytes is the audio in MP3 format

        Raises:
            ValueError: If audio_bytes is empty, word is empty, or audio data is invalid
        """
        if not audio_bytes:
            msg = "audio_bytes cannot be empty"
            raise ValueError(msg)

        if not word or not word.strip():
            msg = "word cannot be empty"
            raise ValueError(msg)

        try:
            # Load audio from bytes
            logger.debug(f"Processing audio for word: {word}")
            audio = AudioSegment.from_file(BytesIO(audio_bytes))

            # Export to MP3 with 128k bitrate
            mp3_buffer = BytesIO()
            audio.export(mp3_buffer, format="mp3", bitrate="128k")
            mp3_bytes = mp3_buffer.getvalue()

            # Generate sanitized filename
            # Replace spaces with underscores, keep hyphens and apostrophes
            sanitized_word = word.strip().replace(" ", "_")
            filename = f"{sanitized_word}.mp3"

            logger.info(f"Successfully processed audio for '{word}' -> {filename}")
            return filename, mp3_bytes

        except CouldntDecodeError as e:
            logger.error(f"Invalid audio data for word '{word}': {e}")
            msg = f"Invalid audio data for word '{word}'"
            raise ValueError(msg) from e
