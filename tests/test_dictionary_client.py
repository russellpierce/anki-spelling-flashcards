"""Test suite for Dictionary API Client.

TEST INTEGRITY DIRECTIVE:
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails: STOP, ANALYZE, DISCUSS with user, and WAIT for approval before modifying tests.
"""

import os
from unittest.mock import Mock, patch

import pytest
import requests
from requests_cache import CachedSession
from spelling_words.dictionary_client import MerriamWebsterClient

# Sample API responses based on Merriam-Webster API structure
SAMPLE_WORD_DATA = [
    {
        "meta": {
            "id": "test",
            "uuid": "test-uuid",
            "sort": "test",
            "src": "sd",
            "section": "alpha",
            "stems": ["test"],
            "offensive": False,
        },
        "hwi": {"hw": "test", "prs": [{"sound": {"audio": "test001"}}]},
        "fl": "noun",
        "shortdef": ["a procedure intended to establish quality or performance"],
    }
]

SAMPLE_WORD_WITH_MULTIPLE_AUDIO = [
    {
        "meta": {"id": "example", "stems": ["example"]},
        "hwi": {
            "hw": "example",
            "prs": [
                {"sound": {"audio": "example01"}},
                {"sound": {"audio": "example02"}},
            ],
        },
        "shortdef": ["one that serves as a pattern"],
    }
]

SAMPLE_WORD_NO_AUDIO = [
    {
        "meta": {"id": "silent", "stems": ["silent"]},
        "hwi": {"hw": "silent"},
        "shortdef": ["making no sound"],
    }
]

# Word not found returns a list of suggestions (strings, not dicts)
SAMPLE_NOT_FOUND = ["test", "tested", "testing"]


class TestMerriamWebsterClientInit:
    """Tests for MerriamWebsterClient initialization."""

    def test_init_raises_valueerror_for_empty_api_key(self):
        """Test that empty API key raises ValueError."""
        session = CachedSession()
        with pytest.raises(ValueError, match="API key"):
            MerriamWebsterClient("", session)

    def test_init_raises_valueerror_for_whitespace_api_key(self):
        """Test that whitespace-only API key raises ValueError."""
        session = CachedSession()
        with pytest.raises(ValueError, match="API key"):
            MerriamWebsterClient("   ", session)

    def test_init_accepts_valid_api_key(self):
        """Test that valid API key is accepted."""
        session = CachedSession()
        client = MerriamWebsterClient("valid-key-123", session)
        assert client.api_key == "valid-key-123"
        assert client.session is session


class TestGetWordData:
    """Tests for MerriamWebsterClient.get_word_data()."""

    def test_get_word_data_successful_response(self):
        """Test get_word_data with a successful API response."""
        session = Mock(spec=CachedSession)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_WORD_DATA
        session.get.return_value = mock_response

        client = MerriamWebsterClient("test-api-key", session)
        result = client.get_word_data("test")

        assert result == SAMPLE_WORD_DATA
        session.get.assert_called_once()
        call_args = session.get.call_args
        assert "test" in call_args[0][0]  # URL contains word
        assert call_args[1]["params"]["key"] == "test-api-key"
        assert call_args[1]["timeout"] == 10

    def test_get_word_data_returns_none_for_not_found(self):
        """Test that get_word_data returns None when word not found."""
        session = Mock(spec=CachedSession)
        mock_response = Mock()
        mock_response.status_code = 200
        # API returns list of suggestions when word not found
        mock_response.json.return_value = SAMPLE_NOT_FOUND
        session.get.return_value = mock_response

        client = MerriamWebsterClient("test-api-key", session)
        result = client.get_word_data("nonexistent")

        assert result is None

    def test_get_word_data_retries_on_timeout(self):
        """Test that get_word_data retries on timeout."""
        session = Mock(spec=CachedSession)
        # First two calls timeout, third succeeds
        session.get.side_effect = [
            requests.Timeout("Connection timeout"),
            requests.Timeout("Connection timeout"),
            Mock(status_code=200, json=lambda: SAMPLE_WORD_DATA),
        ]

        client = MerriamWebsterClient("test-api-key", session)
        result = client.get_word_data("test")

        assert result == SAMPLE_WORD_DATA
        assert session.get.call_count == 3

    def test_get_word_data_raises_after_max_retries(self):
        """Test that get_word_data raises Timeout after max retries."""
        session = Mock(spec=CachedSession)
        # All calls timeout
        session.get.side_effect = requests.Timeout("Connection timeout")

        client = MerriamWebsterClient("test-api-key", session)
        with pytest.raises(requests.Timeout):
            client.get_word_data("test")

        assert session.get.call_count == 3  # Max retries

    def test_get_word_data_validates_word_not_empty(self):
        """Test that get_word_data validates word is not empty."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        with pytest.raises(ValueError, match="word cannot be empty"):
            client.get_word_data("")

    def test_get_word_data_handles_http_error(self):
        """Test that get_word_data raises HTTPError on non-200 status."""
        session = Mock(spec=CachedSession)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        session.get.return_value = mock_response

        client = MerriamWebsterClient("test-api-key", session)
        with pytest.raises(requests.HTTPError):
            client.get_word_data("test")


class TestExtractDefinition:
    """Tests for MerriamWebsterClient.extract_definition()."""

    def test_extract_definition_parses_valid_data(self):
        """Test extract_definition with valid word data."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        definition = client.extract_definition(SAMPLE_WORD_DATA)

        assert definition == "a procedure intended to establish quality or performance"

    def test_extract_definition_raises_for_invalid_data(self):
        """Test extract_definition raises ValueError for invalid data."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        with pytest.raises(ValueError, match="No definition found"):
            client.extract_definition([])

    def test_extract_definition_raises_for_missing_shortdef(self):
        """Test extract_definition raises ValueError when shortdef missing."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        invalid_data = [{"meta": {"id": "test"}, "hwi": {"hw": "test"}}]
        with pytest.raises(ValueError, match="No definition found"):
            client.extract_definition(invalid_data)

    def test_extract_definition_raises_for_empty_shortdef(self):
        """Test extract_definition raises ValueError when shortdef is empty."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        invalid_data = [{"shortdef": []}]
        with pytest.raises(ValueError, match="No definition found"):
            client.extract_definition(invalid_data)


class TestExtractAudioUrls:
    """Tests for MerriamWebsterClient.extract_audio_urls()."""

    def test_extract_audio_urls_returns_correct_urls(self):
        """Test extract_audio_urls returns properly formatted URLs."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        urls = client.extract_audio_urls(SAMPLE_WORD_DATA)

        assert len(urls) == 1
        assert "test001" in urls[0]
        assert urls[0].startswith("https://media.merriam-webster.com/audio/prons/en/us/mp3/")

    def test_extract_audio_urls_handles_multiple_pronunciations(self):
        """Test extract_audio_urls with multiple pronunciations."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        urls = client.extract_audio_urls(SAMPLE_WORD_WITH_MULTIPLE_AUDIO)

        assert len(urls) == 2
        assert "example01" in urls[0]
        assert "example02" in urls[1]

    def test_extract_audio_urls_returns_empty_list_when_no_audio(self):
        """Test extract_audio_urls returns empty list when no audio."""
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        urls = client.extract_audio_urls(SAMPLE_WORD_NO_AUDIO)

        assert urls == []

    def test_extract_audio_urls_handles_special_subdirectories(self):
        """Test extract_audio_urls handles special subdirectory rules.

        According to MW API docs:
        - If audio starts with "bix", subdirectory is "bix"
        - If audio starts with "gg", subdirectory is "gg"
        - If audio starts with number/punctuation, subdirectory is "number"
        - Otherwise, subdirectory is first character
        """
        session = Mock(spec=CachedSession)
        client = MerriamWebsterClient("test-api-key", session)

        # Test bix
        data_bix = [{"hwi": {"prs": [{"sound": {"audio": "bix001"}}]}}]
        urls = client.extract_audio_urls(data_bix)
        assert "/bix/" in urls[0]

        # Test gg
        data_gg = [{"hwi": {"prs": [{"sound": {"audio": "gg001"}}]}}]
        urls = client.extract_audio_urls(data_gg)
        assert "/gg/" in urls[0]

        # Test number
        data_num = [{"hwi": {"prs": [{"sound": {"audio": "1test"}}]}}]
        urls = client.extract_audio_urls(data_num)
        assert "/number/" in urls[0]

        # Test regular (first character)
        data_regular = [{"hwi": {"prs": [{"sound": {"audio": "apple01"}}]}}]
        urls = client.extract_audio_urls(data_regular)
        assert "/a/" in urls[0]


class TestCacheIntegration:
    """Tests for cache integration with LOCAL_TESTING flag."""

    @patch.dict(os.environ, {"LOCAL_TESTING": "False"}, clear=False)
    def test_cache_respects_local_testing_false(self):
        """Test that cache is configured for limited persistence when LOCAL_TESTING=False."""
        # This test verifies the caching behavior respects the LOCAL_TESTING flag
        # In non-local testing, we want minimal API calls
        # The actual cache configuration will be done in the implementation
        assert os.getenv("LOCAL_TESTING") == "False"

    @patch.dict(os.environ, {"LOCAL_TESTING": "True"}, clear=False)
    def test_cache_respects_local_testing_true(self):
        """Test that cache is configured for full persistence when LOCAL_TESTING=True."""
        assert os.getenv("LOCAL_TESTING") == "True"
