# MVP Implementation Tasks

This document contains detailed implementation tasks for the Minimum Viable Product (MVP) of the Spelling Words Anki package.

## MVP Goal

Create basic APKG files with audio and definitions for spelling test preparation.

## Success Criteria

- Can process a list of 100 or more common spelling words
- Generates valid APKG file loadable in AnkiDroid
- Cards display audio and definition correctly
- Reduces redundant downloads and API calls via aggressive local caching for any 2xx returned call. Persist to disk.
- If not operating in an environment where .env shows LOCAL_TESTING=True, only allow for one API call per test as cache won't persist across testing runs.

## Implementation Tasks

### 1. Project Setup

**Status**: Setup complete except for ffmpeg (requires sudo on user's machine)

- [x] Verify `pyproject.toml` exists and has all required dependencies
- [x] Verify `.pre-commit-config.yaml` exists and is configured
- [x] Verify `.gitignore` includes necessary patterns
- [x] Verify ffmpeg is documented in README_LLM.md
- [x] Create project directory structure:
  ```
  spelling_words/
  ├── __init__.py      ✅ Created
  ├── __main__.py      ✅ Created
  ├── cli.py           (Step 9)
  ├── config.py        (Step 2)
  ├── word_list.py     (Step 4)
  ├── dictionary_client.py  (Step 6)
  ├── audio_processor.py    (Step 7)
  └── apkg_manager.py       (Step 8)
  tests/
  ├── __init__.py      ✅ Created with TEST INTEGRITY directive
  └── fixtures/
      └── test_words.txt  ✅ Created with 10 test words
  ```
- [x] Install dependencies: `uv sync --all-extras`
- [ ] **USER ACTION REQUIRED**: Install ffmpeg: `sudo apt-get install -y ffmpeg`
- [x] Install pre-commit hooks: `uv run pre-commit install`
- [x] Verify pre-commit hooks work: `uv run pre-commit run --all-files`
- [x] Run setup verification script: `./scripts/verify_setup.sh`
- [x] Configure MW_ELEMENTARY_API_KEY in `.env` file
- [x] Set LOCAL_TESTING=False in `.env` to limit API calls during testing

**Notes**:
- Python 3.11 detected (3.12+ recommended but 3.11 should work)
- LOCAL_TESTING=False prevents excessive API calls during development
- All automated setup tasks completed
- Only remaining task: ffmpeg installation (requires sudo access on user's machine)

### 2. Configuration Module (`spelling_words/config.py`)

**Status**: ✅ COMPLETE - All tests passing (10/10)

**Write tests FIRST** (`tests/test_config.py`):
- [x] Create test file with TEST INTEGRITY directive at top
- [x] Test Settings loads from .env correctly
- [x] Test Settings raises error when required API key missing
- [x] Test Settings uses default values for optional fields
- [x] Test get_settings() returns singleton
- [x] Run tests to verify they fail (red)

**Then implement**:
- [x] Create `Settings` class inheriting from `pydantic_settings.BaseSettings`
- [x] Define fields:
  - [x] `mw_elementary_api_key: str` (required)
  - [x] `cache_dir: str = ".cache/"` (optional with default)
- [x] Configure to load from `.env` file: `model_config = SettingsConfigDict(env_file='.env')`
- [x] Create `get_settings()` function that returns singleton Settings instance
- [x] Settings will automatically validate and raise clear errors if required fields missing

### 3. Logging Setup (`spelling_words/__init__.py`)

**Status**: ✅ COMPLETE - All tests passing (8/8)

**Write tests FIRST** (`tests/test_logging.py`):
- [x] Create test file with TEST INTEGRITY directive at top
- [x] Test logger configuration initializes correctly
- [x] Test log format includes timestamps
- [x] Test log level defaults to INFO
- [x] Test log level can be set to DEBUG
- [x] Test exception hook logs uncaught exceptions
- [x] Run tests to verify they fail (red)

**Then implement**:
- [x] Import and configure loguru logger
- [x] Set default log format with timestamps
- [x] Configure log level (INFO by default, DEBUG if --verbose)
- [x] Add exception hook to automatically log uncaught exceptions with full context

**Implementation notes**:
- Uses loguru for flexible logging with colorized stderr output
- File rotation (10 MB) and retention (1 week) configured
- Formats include timestamps, log levels, and source location (name:function:line)
- Coverage: 88% (only KeyboardInterrupt handler path uncovered)

### 4. Word List Manager (`spelling_words/word_list.py`)

**Status**: ✅ COMPLETE - All tests passing (16/16)

**Write tests FIRST** (`tests/test_word_list.py`):
- [x] Create test file with TEST INTEGRITY directive at top
- [x] Test load_from_file() with valid word list
- [x] Test load_from_file() raises FileNotFoundError for missing file
- [x] Test load_from_file() handles encoding correctly
- [x] Test load_from_file() skips empty lines and strips whitespace
- [x] Test load_from_file() converts to lowercase
- [x] Test remove_duplicates() preserves order
- [x] Test remove_duplicates() logs count
- [x] Run tests to verify they fail (red)

**Then implement**:
- [x] Create `WordListManager` class
- [x] Implement `load_from_file(file_path: str) -> list[str]`:
  - [x] Read file with proper encoding handling
  - [x] Strip whitespace, skip empty lines
  - [x] Convert to lowercase
  - [x] Validate format (alphabetic + hyphens/apostrophes)
  - [x] Raise `FileNotFoundError` or `ValueError` as appropriate
- [x] Implement `remove_duplicates(words: list[str]) -> list[str]`:
  - [x] Use `dict.fromkeys()` to preserve order
  - [x] Log count of duplicates removed
- [x] Use loguru for all logging

### 5. HTTP Session with Caching (`spelling_words/dictionary_client.py`)

**Status**: ✅ COMPLETE - Integrated into Dictionary Client and CLI

- [x] Import `requests_cache`
- [x] Create cached session:
  ```python
  session = requests_cache.CachedSession(
      'spelling_words_cache',
      backend='sqlite',
      expire_after=timedelta(days=30)
  )
  ```
- [x] Use this session for all HTTP requests (API and audio downloads)
- [x] Caching is automatic - no manual cache checking needed!

**Implementation notes**:
- Session is passed to client classes as a dependency
- Actual session creation happens in CLI module
- Supports LOCAL_TESTING flag for cache behavior

### 6. Dictionary API Client (`spelling_words/dictionary_client.py`)

**Status**: ✅ COMPLETE - All tests passing (19/19)

**Write tests FIRST** (`tests/test_dictionary_client.py`):
- [x] Create test file with TEST INTEGRITY directive at top
- [x] Test MerriamWebsterClient raises ValueError for empty API key
- [x] Test get_word_data() with mocked successful response
- [x] Test get_word_data() returns None for word not found
- [x] Test get_word_data() retries on timeout
- [x] Test extract_definition() parses valid data
- [x] Test extract_definition() raises ValueError for invalid data
- [x] Test extract_audio_urls() returns correct URLs
- [x] Test extract_audio_urls() returns empty list when no audio
- [x] Respect LOCAL_TESTING flag for cache persistence
- [x] Run tests to verify they fail (red)

**Then implement**:
- [x] Create `MerriamWebsterClient` class
- [x] `__init__(api_key: str, session: CachedSession)`:
  - [x] Validate API key is non-empty (raise `ValueError`)
  - [x] Store session and base URL
- [x] Implement `get_word_data(word: str) -> dict | None`:
  - [x] Make GET request using cached session (automatic caching!)
  - [x] URL: `f"https://dictionaryapi.com/api/v3/references/sd/json/{word}"`
  - [x] Timeout: 10 seconds
  - [x] Retry on `requests.Timeout` (max 3 attempts, exponential backoff)
  - [x] Return None if word not found (check for suggestions response)
  - [x] Use loguru for logging
- [x] Implement `extract_definition(word_data: dict) -> str`:
  - [x] Parse JSON structure for first definition
  - [x] Simplify for flashcard use
  - [x] Raise `ValueError` if no definition found
- [x] Implement `extract_audio_urls(word_data: dict) -> list[str]`:
  - [x] Parse JSON for audio references
  - [x] Build full URLs with proper subdirectory handling
  - [x] Return empty list if no audio

**Implementation notes**:
- Coverage: 96% (4 lines uncovered, mostly edge cases in subdirectory logic)
- Implements exponential backoff for retries
- Handles special MW API subdirectory rules (bix, gg, number)

### 7. Audio Processor (`spelling_words/audio_processor.py`)

**Status**: ✅ COMPLETE - All tests passing (17/17)

**Write tests FIRST** (`tests/test_audio_processor.py`):
- [x] Create test file with TEST INTEGRITY directive at top
- [x] Test download_audio() with mocked successful response
- [x] Test download_audio() retries on timeout
- [x] Test download_audio() validates Content-Type
- [x] Test process_audio() converts to MP3 correctly
- [x] Test process_audio() generates sanitized filename
- [x] Test process_audio() raises error for invalid audio
- [x] Respect LOCAL_TESTING flag for cache persistence
- [x] Run tests to verify they fail (red)

**Then implement**:
- [x] Create `AudioProcessor` class
- [x] Implement `download_audio(url: str, session: CachedSession) -> bytes | None`:
  - [x] Use cached session (automatic caching!)
  - [x] Retry on timeout (max 3 attempts)
  - [x] Validate Content-Type header
  - [x] Return bytes or None
- [x] Implement `process_audio(audio_bytes: bytes, word: str) -> tuple[str, bytes]`:
  - [x] Load with pydub `AudioSegment.from_file()`
  - [x] Convert to MP3 with 128k bitrate
  - [x] Generate sanitized filename: `f"{word.replace(' ', '_')}.mp3"`
  - [x] Return (filename, mp3_bytes)
  - [x] Catch `pydub.exceptions.CouldntDecodeError` and raise specific error

**Implementation notes**:
- Coverage: 100% (54/54 lines covered)
- Includes comprehensive error handling with retry logic
- Validates Content-Type headers to ensure audio files
- Supports multiple audio formats (mp3, wav, ogg)
- Exponential backoff for retries (1s, 2s intervals)
- Returns None for 404 errors, raises for other HTTP errors

### 8. APKG Manager (`spelling_words/apkg_manager.py`)

**Status**: ✅ COMPLETE - All tests passing (23/23)

**Write tests FIRST** (`tests/test_apkg_manager.py`):
- [x] Create test file with TEST INTEGRITY directive at top
- [x] Test create_deck() creates valid deck
- [x] Test create_note() with all fields
- [x] Test create_note() validates inputs
- [x] Test package_apkg() creates valid APKG file
- [x] Test package_apkg() includes media files
- [x] Test generated APKG can be loaded by genanki
- [x] Run tests to verify they fail (red)

**Then implement**:
- [x] Import genanki
- [x] Create Anki Model for spelling cards:
  ```python
  SPELLING_MODEL = genanki.Model(
      1607392319,  # Random model ID
      'Spelling Word Model',
      fields=[
          {'name': 'Audio'},
          {'name': 'Definition'},
          {'name': 'Word'},
      ],
      templates=[
          {
              'name': 'Spelling Card',
              'qfmt': '{{Audio}}<br><br>{{Definition}}',  # Front
              'afmt': '{{FrontSide}}<hr>{{Word}}',         # Back
          },
      ])
  ```
- [x] Create `APKGBuilder` class:
  - [x] `__init__(deck_name: str, output_path: str)`:
    - [x] Create `genanki.Deck` instance
    - [x] Initialize media files list
  - [x] `add_word(word: str, definition: str, audio_filename: str, audio_data: bytes)`:
    - [x] Create `genanki.Note` with SPELLING_MODEL
    - [x] Add to deck
    - [x] Track media file
  - [x] `build()`:
    - [x] Create `genanki.Package` with deck and media files
    - [x] Call `package.write_to_file(output_path)`
    - [x] That's it! genanki handles everything else.

**Implementation notes**:
- Coverage: 100% (60/60 lines covered)
- Uses genanki library to handle APKG file creation
- Validates all inputs (word, definition, audio filename, audio data)
- Supports MP3, OGG, and WAV audio formats
- Creates parent directories automatically if they don't exist
- Uses temporary directory for media file handling
- Card template: Front shows audio + definition, back shows word

### 9. Command-Line Interface (`spelling_words/cli.py`)

**Write tests FIRST** (`tests/test_cli.py`):
- [ ] Create test file with TEST INTEGRITY directive at top
- [ ] Test CLI accepts word list file argument
- [ ] Test CLI accepts output APKG filename
- [ ] Test CLI handles --verbose flag
- [ ] Test CLI validates inputs
- [ ] Test CLI error handling
- [ ] Use click.testing.CliRunner for testing
- [ ] Run tests to verify they fail (red)

**Then implement**:
- [ ] Use `@click.command()` decorator pattern
- [ ] Define options:
  - [ ] `@click.option('--words', '-w', required=True, help='Path to word list file')`
  - [ ] `@click.option('--output', '-o', default='output.apkg', help='Output APKG path')`
  - [ ] `@click.option('--verbose', '-v', is_flag=True, help='Enable debug logging')`
- [ ] Implement main workflow:
  - [ ] Load settings with `get_settings()`
  - [ ] Configure loguru log level based on --verbose
  - [ ] Create cached session with requests_cache
  - [ ] Initialize components (WordListManager, MerriamWebsterClient, AudioProcessor, APKGBuilder)
  - [ ] Load and deduplicate word list
  - [ ] Use `rich.progress.track()` for progress bar:
    ```python
    from rich.progress import track
    for word in track(words, description="Processing words..."):
        # process word
    ```
  - [ ] For each word (with error handling):
    - [ ] Fetch word data
    - [ ] Extract definition and audio URLs
    - [ ] Download and process first audio
    - [ ] Add to APKG builder
    - [ ] Use `try/except` to log and skip failures
  - [ ] Build APKG file
  - [ ] Use `rich.console.Console()` to print summary with colors
- [ ] Handle missing .env with friendly error message

### 10. Package Entry Points

- [ ] `spelling_words/__init__.py`:
  - [ ] Set `__version__ = "0.1.0"`
  - [ ] Configure loguru
  - [ ] Export main classes
- [ ] `spelling_words/__main__.py`:
  - [ ] Import and call CLI main function
  - [ ] Enables `python -m spelling_words`

### 11. Testing and Validation

- [ ] Create `tests/fixtures/test_words.txt` with 5-10 common words
- [ ] Manual testing sequence:
  - [ ] Run: `uv run python -m spelling_words -w tests/fixtures/test_words.txt -o test.apkg`
  - [ ] Verify APKG created
  - [ ] Check cache directory has SQLite database
  - [ ] Run again - should be much faster (cached)
  - [ ] Load test.apkg in AnkiDroid
  - [ ] Verify cards show audio, definition, and word
  - [ ] Test with 100+ word list for scalability
- [ ] Verify no secrets in git history

### 12. Documentation

- [ ] Create `README_LLM.md` with:
  - [ ] Installation: uv setup, ffmpeg requirement
  - [ ] Configuration: .env setup with API keys
  - [ ] Usage examples
  - [ ] Development setup
- [ ] Add docstrings to all functions (Google-style)
- [ ] Add inline comments for complex logic (audio URL parsing, etc.)
