"""Test suite for Word List Manager.

TEST INTEGRITY DIRECTIVE:
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails: STOP, ANALYZE, DISCUSS with user, and WAIT for approval before modifying tests.
"""

from io import StringIO
from pathlib import Path

import pytest
from loguru import logger
from spelling_words.word_list import WordListManager


class TestLoadFromFile:
    """Tests for WordListManager.load_from_file()."""

    def test_load_valid_word_list(self, tmp_path):
        """Test loading a valid word list."""
        # Create test file
        word_file = tmp_path / "words.txt"
        word_file.write_text("apple\nbanana\ncherry\n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 3
        assert words == ["apple", "banana", "cherry"]

    def test_load_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        manager = WordListManager()
        with pytest.raises(FileNotFoundError):
            manager.load_from_file("/nonexistent/path/words.txt")

    def test_load_handles_encoding(self, tmp_path):
        """Test that file is read with UTF-8 encoding."""
        word_file = tmp_path / "words_utf8.txt"
        # Write with UTF-8 encoding (café has special character)
        word_file.write_text("café\nnaïve\nrésumé\n", encoding="utf-8")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 3
        assert "café" in words
        assert "naïve" in words
        assert "résumé" in words

    def test_load_skips_empty_lines(self, tmp_path):
        """Test that empty lines are skipped."""
        word_file = tmp_path / "words_with_empty.txt"
        word_file.write_text("apple\n\nbanana\n\n\ncherry\n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 3
        assert words == ["apple", "banana", "cherry"]

    def test_load_strips_whitespace(self, tmp_path):
        """Test that leading/trailing whitespace is stripped."""
        word_file = tmp_path / "words_with_whitespace.txt"
        word_file.write_text("  apple  \n\tbanana\t\n  cherry\n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 3
        assert words == ["apple", "banana", "cherry"]

    def test_load_converts_to_lowercase(self, tmp_path):
        """Test that words are converted to lowercase."""
        word_file = tmp_path / "words_mixed_case.txt"
        word_file.write_text("APPLE\nBanana\nChErRy\n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 3
        assert words == ["apple", "banana", "cherry"]

    def test_load_handles_hyphens_and_apostrophes(self, tmp_path):
        """Test that hyphens and apostrophes are allowed in words."""
        word_file = tmp_path / "words_special.txt"
        word_file.write_text("mother-in-law\ndon't\nself-aware\n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 3
        assert "mother-in-law" in words
        assert "don't" in words
        assert "self-aware" in words

    def test_load_validates_format(self, tmp_path):
        """Test that invalid word format raises ValueError."""
        word_file = tmp_path / "words_invalid.txt"
        word_file.write_text("apple\nbanana123\ncherry\n")

        manager = WordListManager()
        with pytest.raises(ValueError, match="Invalid word format"):
            manager.load_from_file(str(word_file))

    def test_load_combined_functionality(self, tmp_path):
        """Test combined functionality: whitespace, empty lines, case conversion."""
        word_file = tmp_path / "words_combined.txt"
        word_file.write_text("  APPLE  \n\nBaNaNa\n  \n\t\ncherry  \nMOTHER-IN-LAW\n  don't  \n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))

        assert len(words) == 5
        assert words == ["apple", "banana", "cherry", "mother-in-law", "don't"]


class TestRemoveDuplicates:
    """Tests for WordListManager.remove_duplicates()."""

    def test_remove_duplicates_preserves_order(self):
        """Test that duplicates are removed while preserving first occurrence order."""
        manager = WordListManager()
        words = ["apple", "banana", "apple", "cherry", "banana", "date"]
        result = manager.remove_duplicates(words)

        assert result == ["apple", "banana", "cherry", "date"]

    def test_remove_duplicates_empty_list(self):
        """Test remove_duplicates with empty list."""
        manager = WordListManager()
        result = manager.remove_duplicates([])

        assert result == []

    def test_remove_duplicates_no_duplicates(self):
        """Test remove_duplicates when there are no duplicates."""
        manager = WordListManager()
        words = ["apple", "banana", "cherry"]
        result = manager.remove_duplicates(words)

        assert result == ["apple", "banana", "cherry"]

    def test_remove_duplicates_all_duplicates(self):
        """Test remove_duplicates when all words are the same."""
        manager = WordListManager()
        words = ["apple", "apple", "apple", "apple"]
        result = manager.remove_duplicates(words)

        assert result == ["apple"]

    def test_remove_duplicates_logs_count(self):
        """Test that remove_duplicates logs the count of duplicates removed."""
        # Capture loguru output
        log_output = StringIO()
        handler_id = logger.add(log_output, format="{message}", level="INFO")

        try:
            manager = WordListManager()
            words = ["apple", "banana", "apple", "cherry", "banana"]
            manager.remove_duplicates(words)

            # Check that logging occurred
            log_text = log_output.getvalue()
            assert "duplicate" in log_text.lower()
            assert "2" in log_text  # Should mention 2 duplicates removed
        finally:
            # Clean up the handler
            logger.remove(handler_id)


class TestWordListManagerIntegration:
    """Integration tests for WordListManager."""

    def test_load_and_deduplicate_workflow(self, tmp_path):
        """Test the typical workflow: load file then remove duplicates."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("APPLE\nbanana\n  APPLE  \nCherry\n\nbanana\ndate\n")

        manager = WordListManager()
        words = manager.load_from_file(str(word_file))
        unique_words = manager.remove_duplicates(words)

        assert unique_words == ["apple", "banana", "cherry", "date"]

    def test_uses_fixture_test_words(self):
        """Test using the actual fixture file from the project."""
        manager = WordListManager()
        fixture_path = Path(__file__).parent / "fixtures" / "test_words.txt"

        words = manager.load_from_file(str(fixture_path))

        # Based on tests/fixtures/test_words.txt content
        assert len(words) == 10
        assert "tag" in words
        assert "send" in words
        assert "deck" in words
        assert all(word.islower() for word in words)
