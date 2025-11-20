"""APKG Manager for creating Anki flashcard decks.

This module handles the creation of Anki Package (APKG) files using genanki.
"""

import tempfile
from pathlib import Path

import genanki
from loguru import logger

# Define the Anki Model for spelling cards
# Model ID should be a unique random number
SPELLING_MODEL = genanki.Model(
    1607392319,  # Random model ID
    "Spelling Word Model",
    fields=[
        {"name": "Audio"},
        {"name": "Definition"},
        {"name": "Word"},
    ],
    templates=[
        {
            "name": "Spelling Card",
            "qfmt": "{{Audio}}<br><br>{{Definition}}",  # Front: Audio + Definition
            "afmt": "{{FrontSide}}<hr id='answer'>{{Word}}",  # Back: Word
        }
    ],
)


class APKGBuilder:
    """Builder for creating Anki Package (APKG) files with spelling words."""

    def __init__(self, deck_name: str, output_path: str):
        """Initialize the APKG builder.

        Args:
            deck_name: Name of the Anki deck
            output_path: Path where the APKG file will be saved

        Raises:
            ValueError: If deck_name or output_path is empty
        """
        if not deck_name or not deck_name.strip():
            msg = "deck_name cannot be empty"
            raise ValueError(msg)

        if not output_path or not output_path.strip():
            msg = "output_path cannot be empty"
            raise ValueError(msg)

        self.deck_name = deck_name
        self.output_path = output_path

        # Create a genanki Deck with a random ID
        # Use hash of deck name for consistent but unique ID
        deck_id = abs(hash(deck_name)) % (10**10)
        self.deck = genanki.Deck(deck_id, deck_name)

        # Track media files (tuple of filename and data)
        self.media_files = []
        self._media_data = {}  # Map filename -> data

        logger.info(f"Initialized APKGBuilder for deck '{deck_name}'")

    def add_word(self, word: str, definition: str, audio_filename: str, audio_data: bytes) -> None:
        """Add a word to the deck.

        Args:
            word: The spelling word
            definition: Definition of the word
            audio_filename: Filename for the audio (e.g., "word.mp3")
            audio_data: Audio file content as bytes

        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate inputs
        if not word or not word.strip():
            msg = "word cannot be empty"
            raise ValueError(msg)

        if not definition or not definition.strip():
            msg = "definition cannot be empty"
            raise ValueError(msg)

        if not audio_filename or not audio_filename.strip():
            msg = "audio_filename cannot be empty"
            raise ValueError(msg)

        # Validate audio filename extension
        valid_extensions = (".mp3", ".ogg", ".wav")
        if not audio_filename.lower().endswith(valid_extensions):
            msg = f"Invalid audio format: {audio_filename}. Must be one of {valid_extensions}"
            raise ValueError(msg)

        if not audio_data:
            msg = "audio_data cannot be empty"
            raise ValueError(msg)

        # Create a note with the SPELLING_MODEL
        # Fields order: Audio, Definition, Word
        note = genanki.Note(
            model=SPELLING_MODEL,
            fields=[
                f"[sound:{audio_filename}]",  # Audio field with Anki sound syntax
                definition,  # Definition field
                word,  # Word field
            ],
        )

        # Add note to deck
        self.deck.add_note(note)

        # Track media file
        self.media_files.append(audio_filename)
        self._media_data[audio_filename] = audio_data

        logger.debug(f"Added word '{word}' to deck with audio '{audio_filename}'")

    def build(self) -> None:
        """Build and save the APKG file.

        Raises:
            ValueError: If deck has no notes
        """
        if len(self.deck.notes) == 0:
            msg = "Cannot build APKG with no notes. Add at least one word first."
            raise ValueError(msg)

        # Ensure parent directory exists
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a custom Package class to handle media files
        # We need to write media files to temporary location first
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write all media files to temp directory
            media_file_paths = []
            for filename in self.media_files:
                media_path = temp_path / filename
                media_path.write_bytes(self._media_data[filename])
                media_file_paths.append(str(media_path))
                logger.debug(f"Wrote media file to temp: {filename}")

            # Create the package with deck and media files
            package = genanki.Package(self.deck)
            package.media_files = media_file_paths

            # Write the APKG file
            package.write_to_file(str(output_path))

        logger.info(
            f"Successfully built APKG with {len(self.deck.notes)} notes at {self.output_path}"
        )
