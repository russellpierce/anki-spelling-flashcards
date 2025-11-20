"""
Tests for configuration module.

CRITICAL: TEST INTEGRITY DIRECTIVE
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails:
1. STOP - Do not proceed with implementation
2. ANALYZE - Understand why the test is failing
3. DISCUSS - Present the failure to the user
4. WAIT - Get explicit user approval before modifying tests
"""


import pytest
from pydantic import ValidationError
from spelling_words.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings cache before and after each test to ensure test isolation."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSettings:
    """Tests for Settings class."""

    def test_settings_loads_from_env_correctly(self, monkeypatch, tmp_path):
        """Test that Settings loads configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "test-api-key-123")
        monkeypatch.setenv("CACHE_DIR", str(tmp_path / "custom_cache"))

        settings = Settings()

        assert settings.mw_elementary_api_key == "test-api-key-123"
        assert settings.cache_dir == str(tmp_path / "custom_cache")

    def test_settings_raises_error_when_required_api_key_missing(self, monkeypatch):
        """Test that Settings raises ValidationError when required API key is missing."""
        # Clear any existing MW_ELEMENTARY_API_KEY from environment
        monkeypatch.delenv("MW_ELEMENTARY_API_KEY", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify the error is about the missing API key
        assert "mw_elementary_api_key" in str(exc_info.value).lower()

    def test_settings_uses_default_values_for_optional_fields(self, monkeypatch):
        """Test that Settings uses default values for optional configuration fields."""
        # Set only required field
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "test-api-key-456")
        # Make sure CACHE_DIR is not set
        monkeypatch.delenv("CACHE_DIR", raising=False)

        settings = Settings()

        assert settings.mw_elementary_api_key == "test-api-key-456"
        assert settings.cache_dir == ".cache/"  # Default value

    def test_settings_strips_whitespace_from_api_key(self, monkeypatch):
        """Test that Settings strips whitespace from API key."""
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "  test-key-with-spaces  ")

        settings = Settings()

        assert settings.mw_elementary_api_key == "test-key-with-spaces"

    def test_settings_validates_empty_api_key(self, monkeypatch):
        """Test that Settings rejects empty API key after stripping."""
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "   ")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "mw_elementary_api_key" in str(exc_info.value).lower()


class TestGetSettings:
    """Tests for get_settings() singleton function."""

    def test_get_settings_returns_settings_instance(self, monkeypatch):
        """Test that get_settings() returns a Settings instance."""
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "test-api-key-singleton")

        settings = get_settings()

        assert isinstance(settings, Settings)
        assert settings.mw_elementary_api_key == "test-api-key-singleton"

    def test_get_settings_returns_singleton(self, monkeypatch):
        """Test that get_settings() returns the same instance on multiple calls."""
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "test-api-key-singleton-check")

        # Get settings twice
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the exact same object
        assert settings1 is settings2

    def test_get_settings_caches_across_calls(self, monkeypatch):
        """Test that get_settings() caches the settings and doesn't reload from env."""
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "original-key")

        # Get settings once
        settings1 = get_settings()
        assert settings1.mw_elementary_api_key == "original-key"

        # Change environment variable
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "changed-key")

        # Get settings again - should still have original value (cached)
        settings2 = get_settings()
        assert settings2.mw_elementary_api_key == "original-key"
        assert settings1 is settings2


class TestSettingsDotEnvLoading:
    """Tests for .env file loading functionality."""

    def test_settings_loads_from_dotenv_file(self, tmp_path, monkeypatch):
        """Test that Settings can load from a .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("MW_ELEMENTARY_API_KEY=key-from-dotenv\nCACHE_DIR=/tmp/test_cache\n")

        # Change to the temp directory so .env is found
        monkeypatch.chdir(tmp_path)
        # Clear environment variables to ensure we're loading from file
        monkeypatch.delenv("MW_ELEMENTARY_API_KEY", raising=False)
        monkeypatch.delenv("CACHE_DIR", raising=False)

        settings = Settings()

        assert settings.mw_elementary_api_key == "key-from-dotenv"
        assert settings.cache_dir == "/tmp/test_cache"

    def test_env_variables_override_dotenv_file(self, tmp_path, monkeypatch):
        """Test that environment variables take precedence over .env file."""
        # Create a .env file
        env_file = tmp_path / ".env"
        env_file.write_text("MW_ELEMENTARY_API_KEY=key-from-file\n")

        # Set environment variable
        monkeypatch.setenv("MW_ELEMENTARY_API_KEY", "key-from-env")
        monkeypatch.chdir(tmp_path)

        settings = Settings()

        # Environment variable should override .env file
        assert settings.mw_elementary_api_key == "key-from-env"
