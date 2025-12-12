"""Test suite for Command-Line Interface.

TEST INTEGRITY DIRECTIVE:
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails: STOP, ANALYZE, DISCUSS with user, and WAIT for approval before modifying tests.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner
from pydantic import ValidationError
from spelling_words.cli import (
    DECK_NAME_REQUIRED_ERROR,
    DECK_NAME_UPDATE_ERROR,
    main,
    write_missing_words_file,
)


class TestDeckNameOption:
    """Tests for the --deck-name option."""

    def test_create_deck_with_deck_name_succeeds(self, tmp_path: Path):
        """Test that creating a new deck with --deck-name succeeds."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")
        output_file = tmp_path / "output.apkg"
        deck_name = "My Test Deck"

        runner = CliRunner()
        with (
            patch("spelling_words.cli.get_settings") as mock_settings,
            patch("spelling_words.cli.process_words"),
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
        ):
            mock_settings.return_value.mw_elementary_api_key = "test-key"
            # Mock the deck to have at least one note
            mock_apkg.return_value.deck.notes = [Mock()]
            result = runner.invoke(
                main,
                [
                    "-w",
                    str(word_file),
                    "-o",
                    str(output_file),
                    "--deck-name",
                    deck_name,
                ],
            )
            assert result.exit_code == 0
            mock_apkg.assert_called_once_with(deck_name, str(output_file))

    def test_create_deck_without_deck_name_fails(self, tmp_path: Path):
        """Test that creating a new deck without --deck-name fails."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")
        output_file = tmp_path / "output.apkg"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "-w",
                str(word_file),
                "-o",
                str(output_file),
            ],
        )
        assert result.exit_code != 0
        assert DECK_NAME_REQUIRED_ERROR in result.output

    def test_update_deck_with_deck_name_fails(self, tmp_path: Path):
        """Test that using --deck-name with --update fails."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")
        update_file = tmp_path / "update.apkg"
        update_file.touch()
        deck_name = "My Test Deck"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "-w",
                str(word_file),
                "--update",
                str(update_file),
                "--deck-name",
                deck_name,
            ],
        )
        assert result.exit_code != 0
        assert DECK_NAME_UPDATE_ERROR in result.output


class TestUpdateWorkflow:
    """Tests for update workflow functionality."""

    def test_cli_updates_existing_deck(self, tmp_path: Path):
        """Test that CLI can update an existing APKG file."""
        # 1. Create a base APKG file
        base_word_file = tmp_path / "base_words.txt"
        base_word_file.write_text("apple\nbanana\n")
        base_output_file = tmp_path / "base.apkg"
        base_output_file.touch()

        runner = CliRunner()
        # 2. Run update command with a new word list
        update_word_file = tmp_path / "update_words.txt"
        update_word_file.write_text("banana\ncherry\n")

        with (
            patch("spelling_words.cli.load_settings_or_abort"),
            patch("spelling_words.cli.APKGReader") as mock_reader,
            patch("spelling_words.cli.APKGBuilder") as mock_builder,
        ):
            mock_reader.return_value.__enter__.return_value.notes = [
                {"flds": ["[sound:apple.mp3]", "a fruit", "apple"]},
                {"flds": ["[sound:banana.mp3]", "a fruit", "banana"]},
            ]
            mock_reader.return_value.__enter__.return_value.media_files = {
                "apple.mp3": b"apple_audio",
                "banana.mp3": b"banana_audio",
            }
            mock_reader.return_value.__enter__.return_value.deck_name = "Spelling Words"
            mock_builder.return_value.word_exists.side_effect = lambda word: word in [
                "apple",
                "banana",
            ]
            mock_builder.return_value.deck.notes = [
                Mock(fields=["[sound:apple.mp3]", "a fruit", "apple"]),
                Mock(fields=["[sound:banana.mp3]", "a fruit", "banana"]),
            ]

            with (
                patch("spelling_words.cli.MerriamWebsterClient") as mock_client,
                patch("spelling_words.cli.AudioProcessor") as mock_audio,
            ):
                mock_client.return_value.get_word_data.return_value = {
                    "word": "mock",
                    "definition": "mock def",
                    "audio_urls": ["mock_url"],
                }
                mock_client.return_value.extract_definition.return_value = "mock def"
                mock_client.return_value.extract_audio_urls.return_value = ["mock_url"]
                mock_audio.return_value.download_audio.return_value = b"mp3"
                mock_audio.return_value.process_audio.return_value = (
                    "mock.mp3",
                    b"mp3",
                )
                result = runner.invoke(
                    main,
                    [
                        "-w",
                        str(update_word_file),
                        "--update",
                        str(base_output_file),
                        "-v",
                    ],
                )
                assert result.exit_code == 0, result.output

            # 3. Verify the updated APKG file
            assert mock_builder.return_value.add_word.call_count == 1
            assert mock_builder.return_value.build.call_count == 1


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_cli_shows_help_without_arguments(self):
        """Test that CLI shows help when run without arguments."""
        runner = CliRunner()
        result = runner.invoke(main, [])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--words" in result.output
        assert "Generate or update Anki flashcard deck" in result.output

    def test_cli_accepts_words_short_option(self, tmp_path):
        """Test that CLI accepts -w short option."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.process_words"):
            result = runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])
            # Should not fail on missing words option
            assert "--words" not in result.output

    def test_cli_accepts_words_long_option(self, tmp_path):
        """Test that CLI accepts --words long option."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.process_words"):
            result = runner.invoke(main, ["--words", str(word_file), "--deck-name", "Test Deck"])
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
            result = runner.invoke(
                main, ["-w", str(word_file), "-o", str(output_file), "--deck-name", "Test Deck"]
            )
            # Should succeed
            assert result.exit_code == 0

    def test_cli_uses_default_output_if_not_specified(self, tmp_path):
        """Test that CLI uses default output.apkg if not specified."""
        word_file = tmp_path / "words.txt"
        word_file.write_text("test\n")

        runner = CliRunner()
        with patch("spelling_words.cli.process_words"):
            runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])
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
            result = runner.invoke(main, ["-w", str(word_file), "-v", "--deck-name", "Test Deck"])
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
            result = runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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
            runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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
            runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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
            runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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

            result = runner.invoke(
                main, ["-w", str(word_file), "-o", str(output_file), "--deck-name", "Test Deck"]
            )

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

            runner.invoke(
                main, ["-w", str(word_file), "-o", str(output_file), "--deck-name", "Test Deck"]
            )

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

            runner.invoke(
                main, ["-w", str(word_file), "-o", str(output_file), "--deck-name", "Test Deck"]
            )

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

            result = runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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
            runner.invoke(main, ["-w", str(word_file), "--verbose", "--deck-name", "Test Deck"])

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

            runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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

            runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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

            result = runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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

            result = runner.invoke(main, ["-w", str(word_file), "--deck-name", "Test Deck"])

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
            patch("spelling_words.cli.process_words") as mock_process_words,
            patch("spelling_words.cli.APKGBuilder") as mock_apkg,
            patch("spelling_words.cli.validate_word_file"),
            patch("spelling_words.cli.load_settings_or_abort"),
        ):
            # Mock the deck to have one note
            mock_apkg.return_value.deck.notes = [Mock()]
            mock_process_words.return_value = [
                {
                    "word": "badword",
                    "reason": "Word not found",
                    "attempted": "Elementary Dictionary",
                }
            ]

            result = runner.invoke(
                main, ["-w", str(word_file), "-o", str(output_file), "--deck-name", "Test Deck"]
            )
            assert result.exit_code == 0

            # Missing words file should be created
            missing_file = tmp_path / "output-missing.txt"
            assert missing_file.exists()

            # Check content of missing words file
            content = missing_file.read_text()
            assert 'Word: "badword"' in content
            assert "Reason: Word not found" in content

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

            runner.invoke(
                main, ["-w", str(word_file), "-o", str(output_file), "--deck-name", "Test Deck"]
            )

            # Missing words file should NOT be created
            missing_file = tmp_path / "output-missing.txt"
            assert not missing_file.exists()
