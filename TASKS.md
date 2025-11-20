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
- [x] Enable LOCAL_TESTING=True in `.env` for cache persistence

**Notes**:
- Python 3.11 detected (3.12+ recommended but 3.11 should work)
- All automated setup tasks completed
- Only remaining task: ffmpeg installation (requires sudo access on user's machine)

### 2. Configuration Module (`spelling_words/config.py`)

**Write tests FIRST** (`tests/test_config.py`):
- [ ] Create test file with TEST INTEGRITY directive at top
- [ ] Test Settings loads from .env correctly
- [ ] Test Settings raises error when required API key missing
- [ ] Test Settings uses default values for optional fields
- [ ] Test get_settings() returns singleton
- [ ] Run tests to verify they fail (red)

**Then implement**:
- [ ] Create `Settings` class inheriting from `pydantic_settings.BaseSettings`
- [ ] Define fields:
  - [ ] `mw_elementary_api_key: str` (required)
  - [ ] `cache_dir: str = ".cache/"` (optional with default)
- [ ] Configure to load from `.env` file: `model_config = SettingsConfigDict(env_file='.env')`
- [ ] Create `get_settings()` function that returns singleton Settings instance
- [ ] Settings will automatically validate and raise clear errors if required fields missing

### 3. Logging Setup (`spelling_words/__init__.py`)

- [ ] Import and configure loguru logger
- [ ] Set default log format with timestamps
- [ ] Configure log level (INFO by default, DEBUG if --verbose)
- [ ] Add exception hook to automatically log uncaught exceptions with full context

### 4. Word List Manager (`spelling_words/word_list.py`)

**Write tests FIRST** (`tests/test_word_list.py`):
- [ ] Create test file with TEST INTEGRITY directive at top
- [ ] Test load_from_file() with valid word list
- [ ] Test load_from_file() raises FileNotFoundError for missing file
- [ ] Test load_from_file() handles encoding correctly
- [ ] Test load_from_file() skips empty lines and strips whitespace
- [ ] Test load_from_file() converts to lowercase
- [ ] Test remove_duplicates() preserves order
- [ ] Test remove_duplicates() logs count
- [ ] Run tests to verify they fail (red)

**Then implement**:
- [ ] Create `WordListManager` class
- [ ] Implement `load_from_file(file_path: str) -> list[str]`:
  - [ ] Read file with proper encoding handling
  - [ ] Strip whitespace, skip empty lines
  - [ ] Convert to lowercase
  - [ ] Validate format (alphabetic + hyphens/apostrophes)
  - [ ] Raise `FileNotFoundError` or `ValueError` as appropriate
- [ ] Implement `remove_duplicates(words: list[str]) -> list[str]`:
  - [ ] Use `dict.fromkeys()` to preserve order
  - [ ] Log count of duplicates removed
- [ ] Use loguru for all logging

### 5. HTTP Session with Caching (`spelling_words/dictionary_client.py`)

- [ ] Import `requests_cache`
- [ ] Create cached session:
  ```python
  session = requests_cache.CachedSession(
      'spelling_words_cache',
      backend='sqlite',
      expire_after=timedelta(days=30)
  )
  ```
- [ ] Use this session for all HTTP requests (API and audio downloads)
- [ ] Caching is automatic - no manual cache checking needed!

### 6. Dictionary API Client (`spelling_words/dictionary_client.py`)

**Write tests FIRST** (`tests/test_dictionary_client.py`):
- [ ] Create test file with TEST INTEGRITY directive at top
- [ ] Test MerriamWebsterClient raises ValueError for empty API key
- [ ] Test get_word_data() with mocked successful response
- [ ] Test get_word_data() returns None for word not found
- [ ] Test get_word_data() retries on timeout
- [ ] Test extract_definition() parses valid data
- [ ] Test extract_definition() raises ValueError for invalid data
- [ ] Test extract_audio_urls() returns correct URLs
- [ ] Test extract_audio_urls() returns empty list when no audio
- [ ] Respect LOCAL_TESTING flag for cache persistence
- [ ] Run tests to verify they fail (red)

**Then implement**:
- [ ] Create `MerriamWebsterClient` class
- [ ] `__init__(api_key: str, session: CachedSession)`:
  - [ ] Validate API key is non-empty (raise `ValueError`)
  - [ ] Store session and base URL
- [ ] Implement `get_word_data(word: str) -> dict | None`:
  - [ ] Make GET request using cached session (automatic caching!)
  - [ ] URL: `f"https://dictionaryapi.com/api/v3/references/sd/json/{word}"`
  - [ ] Timeout: 10 seconds
  - [ ] Retry on `requests.Timeout` (max 3 attempts, exponential backoff)
  - [ ] Return None if word not found (check for suggestions response)
  - [ ] Use loguru for logging
- [ ] Implement `extract_definition(word_data: dict) -> str`:
  - [ ] Parse JSON structure for first definition
  - [ ] Simplify for flashcard use
  - [ ] Raise `ValueError` if no definition found
- [ ] Implement `extract_audio_urls(word_data: dict) -> list[str]`:
  - [ ] Parse JSON for audio references
  - [ ] Build full URLs with proper subdirectory handling
  - [ ] Return empty list if no audio

### 7. Audio Processor (`spelling_words/audio_processor.py`)

**Write tests FIRST** (`tests/test_audio_processor.py`):
- [ ] Create test file with TEST INTEGRITY directive at top
- [ ] Test download_audio() with mocked successful response
- [ ] Test download_audio() retries on timeout
- [ ] Test download_audio() validates Content-Type
- [ ] Test process_audio() converts to MP3 correctly
- [ ] Test process_audio() generates sanitized filename
- [ ] Test process_audio() raises error for invalid audio
- [ ] Respect LOCAL_TESTING flag for cache persistence
- [ ] Run tests to verify they fail (red)

**Then implement**:
- [ ] Create `AudioProcessor` class
- [ ] Implement `download_audio(url: str, session: CachedSession) -> bytes | None`:
  - [ ] Use cached session (automatic caching!)
  - [ ] Retry on timeout (max 3 attempts)
  - [ ] Validate Content-Type header
  - [ ] Return bytes or None
- [ ] Implement `process_audio(audio_bytes: bytes, word: str) -> tuple[str, bytes]`:
  - [ ] Load with pydub `AudioSegment.from_file()`
  - [ ] Convert to MP3 with 128k bitrate
  - [ ] Generate sanitized filename: `f"{word.replace(' ', '_')}.mp3"`
  - [ ] Return (filename, mp3_bytes)
  - [ ] Catch `pydub.exceptions.CouldntDecodeError` and raise specific error

### 8. APKG Manager (`spelling_words/apkg_manager.py`)

**Write tests FIRST** (`tests/test_apkg_manager.py`):
- [ ] Create test file with TEST INTEGRITY directive at top
- [ ] Test create_deck() creates valid deck
- [ ] Test create_note() with all fields
- [ ] Test create_note() validates inputs
- [ ] Test package_apkg() creates valid APKG file
- [ ] Test package_apkg() includes media files
- [ ] Test generated APKG can be loaded by genanki
- [ ] Run tests to verify they fail (red)

**Then implement**:
- [ ] Import genanki
- [ ] Create Anki Model for spelling cards:
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
- [ ] Create `APKGBuilder` class:
  - [ ] `__init__(deck_name: str, output_path: str)`:
    - [ ] Create `genanki.Deck` instance
    - [ ] Initialize media files list
  - [ ] `add_word(word: str, definition: str, audio_filename: str, audio_data: bytes)`:
    - [ ] Create `genanki.Note` with SPELLING_MODEL
    - [ ] Add to deck
    - [ ] Track media file
  - [ ] `build()`:
    - [ ] Create `genanki.Package` with deck and media files
    - [ ] Call `package.write_to_file(output_path)`
    - [ ] That's it! genanki handles everything else.

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
