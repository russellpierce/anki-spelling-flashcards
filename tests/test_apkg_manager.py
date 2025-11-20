"""Test suite for APKG Manager.

TEST INTEGRITY DIRECTIVE:
NEVER remove, disable, or work around a failing test without explicit user review and approval.
When a test fails: STOP, ANALYZE, DISCUSS with user, and WAIT for approval before modifying tests.
"""

import zipfile

import pytest
from spelling_words.apkg_manager import APKGBuilder


class TestAPKGBuilderInit:
    """Tests for APKGBuilder initialization."""

    def test_init_with_valid_parameters(self, tmp_path):
        """Test APKGBuilder initialization with valid parameters."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        assert builder.deck_name == "Test Deck"
        assert builder.output_path == str(output_path)
        assert builder.deck is not None
        assert len(builder.media_files) == 0

    def test_init_raises_valueerror_for_empty_deck_name(self, tmp_path):
        """Test that empty deck name raises ValueError."""
        output_path = tmp_path / "test.apkg"
        with pytest.raises(ValueError, match="deck_name cannot be empty"):
            APKGBuilder("", str(output_path))

    def test_init_raises_valueerror_for_whitespace_deck_name(self, tmp_path):
        """Test that whitespace-only deck name raises ValueError."""
        output_path = tmp_path / "test.apkg"
        with pytest.raises(ValueError, match="deck_name cannot be empty"):
            APKGBuilder("   ", str(output_path))

    def test_init_raises_valueerror_for_empty_output_path(self):
        """Test that empty output path raises ValueError."""
        with pytest.raises(ValueError, match="output_path cannot be empty"):
            APKGBuilder("Test Deck", "")

    def test_init_raises_valueerror_for_whitespace_output_path(self):
        """Test that whitespace-only output path raises ValueError."""
        with pytest.raises(ValueError, match="output_path cannot be empty"):
            APKGBuilder("Test Deck", "   ")


class TestAddWord:
    """Tests for APKGBuilder.add_word()."""

    def test_add_word_with_valid_parameters(self, tmp_path):
        """Test adding a word with valid parameters."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        audio_data = b"fake audio data"
        builder.add_word("test", "a procedure for testing", "test.mp3", audio_data)

        # Verify note was added to deck
        assert len(builder.deck.notes) == 1
        note = builder.deck.notes[0]
        assert note.fields[0] == "[sound:test.mp3]"  # Audio field
        assert note.fields[1] == "a procedure for testing"  # Definition field
        assert note.fields[2] == "test"  # Word field

        # Verify media file was tracked
        assert len(builder.media_files) == 1
        assert builder.media_files[0] == "test.mp3"

    def test_add_word_validates_empty_word(self, tmp_path):
        """Test that empty word raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="word cannot be empty"):
            builder.add_word("", "definition", "audio.mp3", b"data")

    def test_add_word_validates_whitespace_word(self, tmp_path):
        """Test that whitespace-only word raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="word cannot be empty"):
            builder.add_word("   ", "definition", "audio.mp3", b"data")

    def test_add_word_validates_empty_definition(self, tmp_path):
        """Test that empty definition raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="definition cannot be empty"):
            builder.add_word("test", "", "audio.mp3", b"data")

    def test_add_word_validates_whitespace_definition(self, tmp_path):
        """Test that whitespace-only definition raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="definition cannot be empty"):
            builder.add_word("test", "   ", "audio.mp3", b"data")

    def test_add_word_validates_empty_audio_filename(self, tmp_path):
        """Test that empty audio filename raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="audio_filename cannot be empty"):
            builder.add_word("test", "definition", "", b"data")

    def test_add_word_validates_audio_filename_extension(self, tmp_path):
        """Test that audio filename must have valid extension."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="Invalid audio format"):
            builder.add_word("test", "definition", "audio.txt", b"data")

    def test_add_word_accepts_valid_audio_extensions(self, tmp_path):
        """Test that valid audio extensions are accepted."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        valid_extensions = ["test.mp3", "test.ogg", "test.wav"]
        for filename in valid_extensions:
            builder.add_word("test", "definition", filename, b"data")

        assert len(builder.deck.notes) == 3

    def test_add_word_validates_empty_audio_data(self, tmp_path):
        """Test that empty audio data raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        with pytest.raises(ValueError, match="audio_data cannot be empty"):
            builder.add_word("test", "definition", "audio.mp3", b"")

    def test_add_multiple_words(self, tmp_path):
        """Test adding multiple words to the deck."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        words = [
            ("apple", "a round fruit", "apple.mp3", b"audio1"),
            ("banana", "a long yellow fruit", "banana.mp3", b"audio2"),
            ("cherry", "a small red fruit", "cherry.mp3", b"audio3"),
        ]

        for word, definition, filename, audio_data in words:
            builder.add_word(word, definition, filename, audio_data)

        assert len(builder.deck.notes) == 3
        assert len(builder.media_files) == 3


class TestBuild:
    """Tests for APKGBuilder.build()."""

    def test_build_creates_apkg_file(self, tmp_path):
        """Test that build() creates an APKG file."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        # Add at least one word
        builder.add_word("test", "a procedure", "test.mp3", b"audio data")

        # Build the APKG
        builder.build()

        # Verify file was created
        assert output_path.exists()
        assert output_path.is_file()

    def test_build_creates_valid_zip_file(self, tmp_path):
        """Test that the APKG file is a valid ZIP."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        builder.add_word("test", "a procedure", "test.mp3", b"audio data")
        builder.build()

        # APKG files are ZIP files
        assert zipfile.is_zipfile(output_path)

    def test_build_includes_media_files(self, tmp_path):
        """Test that media files are included in the APKG."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        audio_data = b"fake audio data for testing"
        builder.add_word("test", "a procedure", "test.mp3", audio_data)
        builder.build()

        # Open the APKG and verify media file is present
        with zipfile.ZipFile(output_path, "r") as zf:
            # genanki stores media files with numeric names (0, 1, 2, etc.)
            # and uses a media file to map them
            namelist = zf.namelist()
            # Should contain collection.anki21 (or similar), media, and the audio file
            assert "media" in namelist or any(name.isdigit() for name in namelist), (
                f"Media files not found in {namelist}"
            )

    def test_build_with_empty_deck_raises_error(self, tmp_path):
        """Test that building an empty deck raises ValueError."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        # Don't add any words
        with pytest.raises(ValueError, match="Cannot build APKG with no notes"):
            builder.build()

    def test_build_with_multiple_words_and_media(self, tmp_path):
        """Test building APKG with multiple words and media files."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        # Add multiple words
        words = [
            ("apple", "a fruit", "apple.mp3", b"audio1"),
            ("banana", "a fruit", "banana.mp3", b"audio2"),
            ("cherry", "a fruit", "cherry.mp3", b"audio3"),
        ]

        for word, definition, filename, audio_data in words:
            builder.add_word(word, definition, filename, audio_data)

        builder.build()

        # Verify file was created
        assert output_path.exists()
        assert zipfile.is_zipfile(output_path)

    def test_build_creates_parent_directories(self, tmp_path):
        """Test that build() creates parent directories if they don't exist."""
        output_path = tmp_path / "subdir" / "nested" / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        builder.add_word("test", "a procedure", "test.mp3", b"audio data")
        builder.build()

        # Verify parent directories were created
        assert output_path.parent.exists()
        assert output_path.exists()


class TestAPKGStructure:
    """Tests for the structure of the generated APKG."""

    def test_apkg_can_be_read_by_genanki(self, tmp_path):
        """Test that the generated APKG has the expected structure."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        builder.add_word("test", "a procedure", "test.mp3", b"audio data")
        builder.build()

        # genanki creates APKG files with specific structure
        # Open and verify basic structure
        with zipfile.ZipFile(output_path, "r") as zf:
            namelist = zf.namelist()
            # Should contain at least collection.anki21 or collection.anki2
            assert any("collection" in name for name in namelist), (
                f"Collection file not found in {namelist}"
            )

    def test_card_fields_are_correctly_ordered(self, tmp_path):
        """Test that card fields are in the correct order (Audio, Definition, Word)."""
        output_path = tmp_path / "test.apkg"
        builder = APKGBuilder("Test Deck", str(output_path))

        builder.add_word("hello", "a greeting", "hello.mp3", b"audio")
        builder.build()

        # Check the note fields
        note = builder.deck.notes[0]
        assert note.fields[0] == "[sound:hello.mp3]"  # Audio
        assert note.fields[1] == "a greeting"  # Definition
        assert note.fields[2] == "hello"  # Word
