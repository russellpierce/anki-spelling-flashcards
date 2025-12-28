"""
CRITICAL: TEST INTEGRITY DIRECTIVE

NEVER remove, disable, or work around a failing test without explicit user review and approval.
Tests are the specification - a failing test means either the implementation or the test expectations
need to be discussed with the user.
"""

import tempfile
from pathlib import Path

import pytest
import requests_cache
from spelling_words.cache_manager import CacheManager


@pytest.fixture
def temp_cache_dir(monkeypatch):
    """Create a temporary directory for cache files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Change the cache directory for testing
        cache_path = Path(temp_dir) / "test_cache"
        monkeypatch.setattr("spelling_words.cache_manager.CacheManager.CACHE_NAME", str(cache_path))
        yield temp_dir


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create a CacheManager instance with temporary cache."""
    return CacheManager()


def test_cache_manager_initialization(cache_manager):
    """Test that CacheManager initializes correctly."""
    assert cache_manager.session is not None
    assert isinstance(cache_manager.session, requests_cache.CachedSession)


def test_bust_word_cache_empty_word_raises_error(cache_manager):
    """Test that busting cache with empty word raises ValueError."""
    with pytest.raises(ValueError, match="word cannot be empty"):
        cache_manager.bust_word_cache("")

    with pytest.raises(ValueError, match="word cannot be empty"):
        cache_manager.bust_word_cache("   ")


def test_bust_word_cache_no_entries(cache_manager):
    """Test busting cache when no entries exist for the word."""
    deleted_count = cache_manager.bust_word_cache("nonexistent")
    assert deleted_count == 0


def test_is_word_related_url_dictionary_api(cache_manager):
    """Test that dictionary API URLs are correctly identified."""
    url = "https://dictionaryapi.com/api/v3/references/sd2/json/apple?key=test"
    assert cache_manager._is_word_related_url(url, "apple")
    assert not cache_manager._is_word_related_url(url, "banana")


def test_is_word_related_url_audio(cache_manager):
    """Test that audio URLs are correctly identified."""
    url = "https://media.merriam-webster.com/audio/prons/en/us/mp3/a/apple001.mp3"
    assert cache_manager._is_word_related_url(url, "apple")
    assert not cache_manager._is_word_related_url(url, "banana")


def test_is_word_related_url_case_insensitive(cache_manager):
    """Test that URL matching is case insensitive."""
    url = "https://dictionaryapi.com/api/v3/references/sd2/json/APPLE"
    assert cache_manager._is_word_related_url(url, "apple")
    assert cache_manager._is_word_related_url(url, "APPLE")


def test_clear_all_cache(cache_manager):
    """Test that clearing all cache removes all entries."""
    # Clear should work even if cache is empty
    cache_manager.clear_all_cache()

    # Verify cache is empty
    cache = cache_manager.session.cache
    assert len(cache.responses) == 0


def test_get_cache_info(cache_manager):
    """Test that cache info returns expected structure."""
    info = cache_manager.get_cache_info()

    assert isinstance(info, dict)
    assert "cache_name" in info
    assert "backend" in info
    assert "response_count" in info
    assert "expire_after" in info

    # Empty cache should have 0 responses
    assert info["response_count"] == 0
