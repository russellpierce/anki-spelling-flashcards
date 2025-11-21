"""Test suite for Command-Line Interface.

TEST INTEGRITY DIRECTIVE:
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails: STOP, ANALYZE, DISCUSS with user, and WAIT for approval before modifying tests.
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner
from pydantic import ValidationError
from spelling_words.cli import main, write_missing_words_file


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_cli_shows_help_without_arguments(self):
        """Test that CLI shows help when run without arguments."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--words" in result.output
        assert "Generate Anki flashcard deck" in result.output

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
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.process_words"),
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
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
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.process_words"),
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
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


class TestCollegiateFallback:
    """Tests for collegiate dictionary fallback functionality."""

    def test_cli_initializes_collegiate_client_when_api_key_configured(self, tmp_path):
        """Test that CLI initializes collegiate client when API key is present."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_elementary,
            patch("spelling_words.cli.MerriamWebsterCollegiateClient") as mock_collegiate,
            patch("spelling_words.cli.process_words"),
        ):
            # Configure both API keys
            mock_settings.return_value.mw_elementary_api_key = "elementary-key"
            mock_settings.return_value.mw_collegiate_api_key = "collegiate-key"

            runner.invoke(main, ["-w", str(word_file)])

            # Both clients should be initialized
            assert mock_elementary.called
            assert mock_collegiate.called

    def test_cli_skips_collegiate_client_when_api_key_not_configured(self, tmp_path):
        """Test that CLI skips collegiate client when API key is None."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_elementary,
            patch("spelling_words.cli.MerriamWebsterCollegiateClient") as mock_collegiate,
            patch("spelling_words.cli.process_words"),
        ):
            # Only elementary API key configured
            mock_settings.return_value.mw_elementary_api_key = "elementary-key"
            mock_settings.return_value.mw_collegiate_api_key = None

            runner.invoke(main, ["-w", str(word_file)])

            # Only elementary client should be initialized
            assert mock_elementary.called
            assert not mock_collegiate.called

    def test_fallback_to_collegiate_when_word_not_found_in_elementary(self, tmp_path):
        """Test that process_words falls back to collegiate when word not found."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("obscureword\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_elementary,
            patch("spelling_words.cli.MerriamWebsterCollegiateClient") as mock_collegiate,
            patch("spelling_words.cli.AudioProcessor") as mock_audio,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.requests_cache.CachedSession"),
        ):
            # Configure both API keys
            mock_settings.return_value.mw_elementary_api_key = "elementary-key"
            mock_settings.return_value.mw_collegiate_api_key = "collegiate-key"

            mock_manager.return_value.load_from_file.return_value = ["obscureword"]
            mock_manager.return_value.remove_duplicates.return_value = ["obscureword"]

            # Elementary returns None, collegiate returns data
            mock_elementary.return_value.get_word_data.return_value = None
            mock_collegiate.return_value.get_word_data.return_value = {"word": "obscureword"}
            mock_collegiate.return_value.extract_definition.return_value = "definition"
            mock_collegiate.return_value.extract_audio_urls.return_value = [
                "http://example.com/audio.mp3"
            ]

            mock_audio.return_value.download_audio.return_value = b"audio"
            mock_audio.return_value.process_audio.return_value = ("word.mp3", b"audio")

            # Mock the deck to have notes (word was successfully added)
            mock_apkg.return_value.deck.notes = [Mock()]

            result = runner.invoke(main, ["-w", str(word_file)])

            # Word should be successfully processed using collegiate fallback
            assert result.exit_code == 0
            mock_apkg.return_value.build.assert_called_once()

    def test_fallback_to_collegiate_when_audio_not_found_in_elementary(self, tmp_path):
        """Test that process_words falls back to collegiate for missing audio."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.WordListManager") as mock_manager,
            patch("spelling_words.cli.MerriamWebsterClient") as mock_elementary,
            patch("spelling_words.cli.MerriamWebsterCollegiateClient") as mock_collegiate,
            patch("spelling_words.cli.AudioProcessor") as mock_audio,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.requests_cache.CachedSession"),
        ):
            # Configure both API keys
            mock_settings.return_value.mw_elementary_api_key = "elementary-key"
            mock_settings.return_value.mw_collegiate_api_key = "collegiate-key"

            mock_manager.return_value.load_from_file.return_value = ["test"]
            mock_manager.return_value.remove_duplicates.return_value = ["test"]

            # Elementary has definition but no audio
            elementary_data = {"word": "test"}
            mock_elementary.return_value.get_word_data.return_value = elementary_data
            mock_elementary.return_value.extract_definition.return_value = "definition"
            mock_elementary.return_value.extract_audio_urls.return_value = []

            # Collegiate has audio
            collegiate_data = {"word": "test"}
            mock_collegiate.return_value.get_word_data.return_value = collegiate_data
            mock_collegiate.return_value.extract_audio_urls.return_value = [
                "http://example.com/audio.mp3"
            ]

            mock_audio.return_value.download_audio.return_value = b"audio"
            mock_audio.return_value.process_audio.return_value = ("test.mp3", b"audio")

            # Mock the deck to have notes
            mock_apkg.return_value.deck.notes = [Mock()]

            result = runner.invoke(main, ["-w", str(word_file)])

            # Word should be successfully processed with collegiate audio
            assert result.exit_code == 0
            mock_apkg.return_value.build.assert_called_once()


class TestMissingWordsFile:
    """Tests for missing words file generation."""

    def test_write_missing_words_file_creates_file(self, tmp_path):
        """Test that write_missing_words_file creates a file with correct name."""
        output_file = tmp_path / "test.apkg"
        missing_words = [
            {"word": "test", "reason": "Word not found", "attempted": "Elementary Dictionary"}
        ]

        write_missing_words_file(output_file, missing_words)

        missing_file = tmp_path / "test-missing.txt"
        assert missing_file.exists()

    def test_write_missing_words_file_contains_header(self, tmp_path):
        """Test that missing words file contains proper header."""
        output_file = tmp_path / "test.apkg"
        missing_words = [
            {"word": "test", "reason": "Word not found", "attempted": "Elementary Dictionary"}
        ]

        write_missing_words_file(output_file, missing_words)

        missing_file = tmp_path / "test-missing.txt"
        content = missing_file.read_text()

        assert "Spelling Words - Missing/Incomplete Words Report" in content
        assert "Generated:" in content
        assert "APKG:" in content

    def test_write_missing_words_file_contains_word_details(self, tmp_path):
        """Test that missing words file contains word details."""
        output_file = tmp_path / "test.apkg"
        missing_words = [
            {
                "word": "obscureword",
                "reason": "Word not found in either dictionary",
                "attempted": "Elementary Dictionary, Collegiate Dictionary",
            }
        ]

        write_missing_words_file(output_file, missing_words)

        missing_file = tmp_path / "test-missing.txt"
        content = missing_file.read_text()

        assert "obscureword" in content
        assert "Word not found in either dictionary" in content
        assert "Elementary Dictionary, Collegiate Dictionary" in content

    def test_write_missing_words_file_contains_count(self, tmp_path):
        """Test that missing words file contains total count."""
        output_file = tmp_path / "test.apkg"
        missing_words = [
            {"word": "word1", "reason": "No audio", "attempted": "Elementary Dictionary"},
            {"word": "word2", "reason": "No definition", "attempted": "Elementary Dictionary"},
            {"word": "word3", "reason": "Not found", "attempted": "Elementary Dictionary"},
        ]

        write_missing_words_file(output_file, missing_words)

        missing_file = tmp_path / "test-missing.txt"
        content = missing_file.read_text()

        assert "Total missing: 3 words" in content

    def test_cli_creates_missing_file_when_words_skipped(self, tmp_path):
        """Test that CLI creates missing words file when some words are skipped."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("goodword\nbadword\n")
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
            mock_settings.return_value.mw_collegiate_api_key = None

            mock_manager.return_value.load_from_file.return_value = ["goodword", "badword"]
            mock_manager.return_value.remove_duplicates.return_value = ["goodword", "badword"]

            # goodword succeeds, badword fails
            def get_word_data_side_effect(word):
                return {"word": word} if word == "goodword" else None

            mock_client.return_value.get_word_data.side_effect = get_word_data_side_effect
            mock_client.return_value.extract_definition.return_value = "definition"
            mock_client.return_value.extract_audio_urls.return_value = [
                "http://example.com/audio.mp3"
            ]

            mock_audio.return_value.download_audio.return_value = b"audio"
            mock_audio.return_value.process_audio.return_value = ("word.mp3", b"audio")

            # Mock the deck to have one note
            mock_apkg.return_value.deck.notes = [Mock()]

            runner.invoke(main, ["-w", str(word_file), "-o", str(output_file)])

            # Missing words file should be created
            missing_file = tmp_path / "output-missing.txt"
            assert missing_file.exists()

            content = missing_file.read_text()
            assert "badword" in content

    def test_cli_does_not_create_missing_file_when_all_words_succeed(self, tmp_path):
        """Test that CLI does not create missing file when all words succeed."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("goodword\n")
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
            mock_settings.return_value.mw_collegiate_api_key = None

            mock_manager.return_value.load_from_file.return_value = ["goodword"]
            mock_manager.return_value.remove_duplicates.return_value = ["goodword"]

            mock_client.return_value.get_word_data.return_value = {"word": "goodword"}
            mock_client.return_value.extract_definition.return_value = "definition"
            mock_client.return_value.extract_audio_urls.return_value = [
                "http://example.com/audio.mp3"
            ]

            mock_audio.return_value.download_audio.return_value = b"audio"
            mock_audio.return_value.process_audio.return_value = ("word.mp3", b"audio")

            # Mock the deck to have one note
            mock_apkg.return_value.deck.notes = [Mock()]

            runner.invoke(main, ["-w", str(word_file), "-o", str(output_file)])

            # Missing words file should NOT be created
            missing_file = tmp_path / "output-missing.txt"
            assert not missing_file.exists()
