"""Word List Manager for handling spelling word lists.

This module provides functionality to load word lists from files and process them
for use in Anki flashcard generation.
"""

import re
from pathlib import Path

from loguru import logger


class WordListManager:
    """Manages loading and processing of spelling word lists."""

    # Pattern for valid words: only hyphens and apostrophes allowed as special chars
    # We'll validate that the rest are alphabetic using .isalpha() for Unicode support
    SPECIAL_CHARS_PATTERN = re.compile(r"^[a-zA-Z\u00C0-\u024F\-']+$")

    def load_from_file(self, file_path: str) -> list[str]:
        """Load words from a text file.

        Reads a text file containing one word per line, processes each word by:
        - Converting to lowercase
        - Stripping whitespace
        - Skipping empty lines
        - Validating word format (alphabetic with optional hyphens/apostrophes)

        Args:
            file_path: Path to the word list file

        Returns:
            List of processed words in order

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If a word contains invalid characters

        Example:
            >>> manager = WordListManager()
            >>> words = manager.load_from_file("wordlist.txt")
            >>> print(words)
            ['apple', 'banana', 'cherry']
        """
        path = Path(file_path)

        if not path.exists():
            error_msg = f"Word list file not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Loading word list from: {file_path}")

        words = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    # Strip whitespace
                    word = line.strip()

                    # Skip empty lines
                    if not word:
                        continue

                    # Convert to lowercase
                    word = word.lower()

                    # Validate format
                    if not self.SPECIAL_CHARS_PATTERN.match(word):
                        error_msg = (
                            f"Invalid word format at line {line_num}: '{word}'. "
                            f"Words must contain only letters, hyphens, and apostrophes."
                        )
                        logger.error(error_msg)
                        raise ValueError(error_msg)

                    words.append(word)

        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode file with UTF-8 encoding: {file_path}", exc_info=True)
            encoding_error_msg = f"File encoding error: {e}"
            raise ValueError(encoding_error_msg) from e

        logger.info(f"Loaded {len(words)} words from {file_path}")
        return words

    def remove_duplicates(self, words: list[str]) -> list[str]:
        """Remove duplicate words while preserving order.

        Uses dict.fromkeys() to remove duplicates while maintaining the order
        of first occurrence.

        Args:
            words: List of words (may contain duplicates)

        Returns:
            List of unique words in original order

        Example:
            >>> manager = WordListManager()
            >>> words = ['apple', 'banana', 'apple', 'cherry']
            >>> unique = manager.remove_duplicates(words)
            >>> print(unique)
            ['apple', 'banana', 'cherry']
        """
        original_count = len(words)
        unique_words = list(dict.fromkeys(words))
        duplicates_removed = original_count - len(unique_words)

        if duplicates_removed > 0:
            logger.info(
                f"Removed {duplicates_removed} duplicate word(s). Unique words: {len(unique_words)}"
            )
        else:
            logger.debug("No duplicates found in word list")

        return unique_words
