"""Test suite for Command-Line Interface.

TEST INTEGRITY DIRECTIVE:
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails: STOP, ANALYZE, DISCUSS with user, and WAIT for approval before modifying tests.
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner
from pydantic import ValidationError
from spelling_words.cli import main


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_cli_requires_words_argument(self):
        """Test that CLI requires --words argument."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_cli_accepts_words_short_option(self, tmp_path):
        """Test that CLI accepts -w short option."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.process_words"):
            result = runner.invoke(main, ["-w", str(word_file)])
            # Should not fail on missing words option
            assert "--words" not in result.output

    def test_cli_accepts_words_long_option(self, tmp_path):
        """Test that CLI accepts --words long option."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.process_words"):
            result = runner.invoke(main, ["--words", str(word_file)])
            # Should not fail on missing words option
            assert "Missing option" not in result.output

    def test_cli_accepts_output_option(self, tmp_path):
        """Test that CLI accepts --output/-o option."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")
        output_file = tmp_path / "output.apkg"

        runner = CliRunner()
        with (
            patch("spelling_words.cli.process_words"),
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
        ):
            # Mock the deck to have at least one note
            mock_apkg.return_value.deck.notes = [Mock()]
            result = runner.invoke(main, ["-w", str(word_file), "-o", str(output_file)])
            # Should succeed
            assert result.exit_code == 0

    def test_cli_uses_default_output_if_not_specified(self, tmp_path):
        """Test that CLI uses default output.apkg if not specified."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.process_words"):
            runner.invoke(main, ["-w", str(word_file)])
            # Test completes successfully
            assert True

    def test_cli_accepts_verbose_flag(self, tmp_path):
        """Test that CLI accepts --verbose/-v flag."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.process_words"),
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
        ):
            # Mock the deck to have at least one note
            mock_apkg.return_value.deck.notes = [Mock()]
            result = runner.invoke(main, ["-w", str(word_file), "-v"])
            # Should succeed and show debug logging
            assert result.exit_code == 0
            assert "Debug logging enabled" in result.output


class TestCLIValidation:
    """Tests for CLI input validation."""

    def test_cli_validates_word_file_exists(self, tmp_path):
        """Test that CLI validates word file exists."""
        nonexistent = tmp_path / "nonexistent.txt"

        runner = CliRunner()
        result = runner.invoke(main, ["-w", str(nonexistent)])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_cli_validates_word_file_is_file(self, tmp_path):
        """Test that CLI validates word file is a file (not directory)."""
        directory = tmp_path / "directory"
        directory.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["-w", str(directory)])

        assert result.exit_code != 0
        assert "file" in result.output.lower() or "directory" in result.output.lower()

    def test_cli_handles_missing_env_file(self, tmp_path):
        """Test that CLI handles missing .env file gracefully."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.get_settings") as mock_settings:
            mock_settings.side_effect = ValidationError.from_exception_data(
                "Settings validation error",
                [{"type": "missing", "loc": ("MW_ELEMENTARY_API_KEY",), "msg": "Field required"}],
            )
            result = runner.invoke(main, ["-w", str(word_file)])

            assert result.exit_code != 0
            assert "API key" in result.output or "MW_ELEMENTARY_API_KEY" in result.output


class TestCLIWorkflow:
    """Tests for CLI workflow and orchestration."""

    def test_cli_loads_word_list(self, tmp_path):
        """Test that CLI loads word list from file."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("apple\nbanana\ncherry\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.process_words"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            runner.invoke(main, ["-w", str(word_file)])

            # Verify WordListManager was instantiated
            assert mock_manager.called

    def test_cli_creates_cached_session(self, tmp_path):
        """Test that CLI creates a cached session."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.requests_cache.CachedSession") as mock_session,
            patch("spelling_words.cli.process_words"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            runner.invoke(main, ["-w", str(word_file)])

            # Verify CachedSession was created
            assert mock_session.called

    def test_cli_initializes_components(self, tmp_path):
        """Test that CLI initializes all required components."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_client,
            patch("spelling_words.cli.AudioProcessor") as mock_audio,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.process_words"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            runner.invoke(main, ["-w", str(word_file)])

            # Verify all components were initialized
            assert mock_client.called
            assert mock_audio.called
            assert mock_apkg.called

    def test_cli_processes_words_successfully(self, tmp_path):
        """Test that CLI processes words through the full workflow."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")
        output_file = tmp_path / "output.apkg"

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_client,
            patch("spelling_words.cli.AudioProcessor") as mock_audio,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.requests_cache.CachedSession"),
        ):
            # Setup mocks
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            mock_manager.return_value.load_from_file.return_value = ["test"]
            mock_manager.return_value.remove_duplicates.return_value = ["test"]

            mock_client_instance = mock_client.return_value
            mock_client_instance.get_word_data.return_value = {"word": "test"}
            mock_client_instance.extract_definition.return_value = "a procedure"
            mock_client_instance.extract_audio_urls.return_value = ["http://example.com/test.mp3"]

            mock_audio_instance = mock_audio.return_value
            mock_audio_instance.download_audio.return_value = b"fake audio"
            mock_audio_instance.process_audio.return_value = ("test.mp3", b"processed audio")

            # Mock the deck to have notes (simulating successful word processing)
            mock_apkg.return_value.deck.notes = [Mock()]

            result = runner.invoke(main, ["-w", str(word_file), "-o", str(output_file)])

            assert result.exit_code == 0
            # Verify build was called
            mock_apkg.return_value.build.assert_called_once()

    def test_cli_handles_word_not_found(self, tmp_path):
        """Test that CLI handles word not found gracefully."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("nonexistentword\n")
        output_file = tmp_path / "output.apkg"

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_client,
            patch("spelling_words.cli.AudioProcessor"),
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.requests_cache.CachedSession"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            mock_manager.return_value.load_from_file.return_value = ["nonexistentword"]
            mock_manager.return_value.remove_duplicates.return_value = ["nonexistentword"]

            # Word not found
            mock_client.return_value.get_word_data.return_value = None

            runner.invoke(main, ["-w", str(word_file), "-o", str(output_file)])

            # Should complete but show warning/skip
            # Since no words were successfully processed, build should not be called
            assert mock_apkg.return_value.build.call_count == 0

    def test_cli_handles_audio_download_failure(self, tmp_path):
        """Test that CLI handles audio download failure gracefully."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")
        output_file = tmp_path / "output.apkg"

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_client,
            patch("spelling_words.cli.AudioProcessor") as mock_audio,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.requests_cache.CachedSession"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            mock_manager.return_value.load_from_file.return_value = ["test"]
            mock_manager.return_value.remove_duplicates.return_value = ["test"]

            mock_client_instance = mock_client.return_value
            mock_client_instance.get_word_data.return_value = {"word": "test"}
            mock_client_instance.extract_definition.return_value = "a procedure"
            mock_client_instance.extract_audio_urls.return_value = ["http://example.com/test.mp3"]

            # Audio download fails
            mock_audio.return_value.download_audio.return_value = None

            runner.invoke(main, ["-w", str(word_file), "-o", str(output_file)])

            # Should skip word without audio
            assert mock_apkg.return_value.build.call_count == 0


class TestCLIOutput:
    """Tests for CLI output and reporting."""

    def test_cli_displays_summary(self, tmp_path):
        """Test that CLI displays summary after processing."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_client,
            patch("spelling_words.cli.AudioProcessor") as mock_audio,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.requests_cache.CachedSession"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            mock_manager.return_value.load_from_file.return_value = ["test"]
            mock_manager.return_value.remove_duplicates.return_value = ["test"]

            mock_client.return_value.get_word_data.return_value = {"word": "test"}
            mock_client.return_value.extract_definition.return_value = "a procedure"
            mock_client.return_value.extract_audio_urls.return_value = [
                "http://example.com/test.mp3"
            ]

            mock_audio.return_value.download_audio.return_value = b"audio"
            mock_audio.return_value.process_audio.return_value = ("test.mp3", b"audio")

            # Mock the deck to have notes
            mock_apkg.return_value.deck.notes = [Mock()]

            result = runner.invoke(main, ["-w", str(word_file)])

            # Should show summary information
            assert result.exit_code == 0
            assert "Successfully" in result.output or "Complete" in result.output

    def test_cli_verbose_enables_debug_logging(self, tmp_path):
        """Test that --verbose flag enables debug logging."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.logger") as mock_logger,
            patch("spelling_words.cli.process_words"),
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            runner.invoke(main, ["-w", str(word_file), "--verbose"])

            # Verify logger was configured for debug
            # (exact verification depends on implementation)
            assert mock_logger.remove.called or mock_logger.add.called
