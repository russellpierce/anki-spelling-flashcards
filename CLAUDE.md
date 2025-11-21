# Claude Development Guide

This document provides guidelines for AI assistants (Claude) working on this project.

## TODO: Check for Updated Dependencies

**IMPORTANT**: At the start of each session, check if there is a newer release of `pydub` on PyPI.

Current version in use: `pydub>=0.25.0` (released 2021)

**Issue**: The current PyPI version (0.25.1) produces SyntaxWarnings in Python 3.12+ due to invalid escape sequences in regex patterns. The fixes are merged in the GitHub master branch but not yet released.

**Action**:
1. Check the latest version: `curl -s https://pypi.org/pypi/pydub/json | python3 -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"`
2. If a version newer than 0.25.1 is available, announce it to the user as potential work to update the dependency
3. Relevant GitHub issues: #801, #809, #814, #828

## Development Environment

### Target Platform

- **Operating System**: Ubuntu 24.04 LTS
- **Python Version**: Python 3.12+ (Ubuntu 24.04 default)
- **Package Manager**: uv

### System Dependencies

Before starting development, ensure these system packages are installed:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

- **ffmpeg**: Required by pydub for audio format conversion

### Python Package Management

This project uses **uv** for Python package management.

#### Installing uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Common uv Commands

```bash
# Create virtual environment and install all dependencies (including dev)
uv sync --all-extras

# Create virtual environment and install only main dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Run Python in the project environment
uv run python <script.py>

# Run a specific command in the environment
uv run <command>
```

## Python Coding Standards

### Exception Handling

#### 1. Only Raise Specific Exception Types

**DO**:
```python
if not os.path.exists(file_path):
    raise FileNotFoundError(f"APKG file not found: {file_path}")

if len(api_key) < 10:
    raise ValueError("API key must be at least 10 characters")

if response.status_code != 200:
    raise requests.HTTPError(f"API request failed with status {response.status_code}")
```

**DON'T**:
```python
if not os.path.exists(file_path):
    raise Exception("File not found")  # Too generic!
```

**Common Specific Exceptions**:
- `ValueError`: Invalid argument values
- `TypeError`: Wrong type passed
- `FileNotFoundError`: File doesn't exist
- `KeyError`: Missing dictionary key
- `requests.HTTPError`: HTTP request failures
- `sqlite3.Error`: Database errors
- `zipfile.BadZipFile`: Corrupted ZIP/APKG files

#### 2. Only Try/Catch Known, Resolvable Exceptions

Only use try/except when you can actually handle the exception meaningfully.

**DO** (resolvable exception):
```python
def download_audio(url: str, max_retries: int = 3) -> bytes:
    """Download audio with retry logic for network issues."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.Timeout:
            if attempt < max_retries - 1:
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                logger.error(f"Failed to download after {max_retries} attempts", exc_info=True)
                raise
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # Word not found is expected, handle gracefully
                logger.info(f"Audio not found at URL: {url}")
                return None
            else:
                # Other HTTP errors should propagate
                raise
```

**DON'T** (catching everything blindly):
```python
def process_word(word: str):
    try:
        # ... lots of code ...
        return result
    except Exception as e:  # Too broad! Hides bugs
        print(f"Something went wrong: {e}")
        return None
```

#### 3. Always Log Errors with Stack Traces

When logging an error that will be raised or cannot be handled, include the full stack trace.

**DO**:
```python
import logging

logger = logging.getLogger(__name__)

try:
    db_connection = sqlite3.connect(db_path)
except sqlite3.Error:
    logger.error(f"Failed to connect to database: {db_path}", exc_info=True)
    raise
```

The `exc_info=True` parameter includes the full stack trace in the log.

**For unrecoverable errors**:
```python
try:
    decompressed = zstd.ZstdDecompressor().decompress(compressed_data)
except zstd.ZstdError:
    logger.error("Failed to decompress APKG data", exc_info=True)
    raise  # Re-raise after logging
```

### Code Organization

#### Function and Class Design

- **Single Responsibility**: Each function/class should do one thing well
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Include docstrings for all public functions and classes

Example:
```python
def concatenate_audio_files(
    audio_files: list[bytes],
    gap_duration_ms: int = 1000
) -> bytes:
    """
    Concatenate multiple audio files with gaps between them.

    Args:
        audio_files: List of audio file contents as bytes
        gap_duration_ms: Duration of silence between audio files in milliseconds

    Returns:
        Combined audio file as bytes (MP3 format)

    Raises:
        ValueError: If audio_files is empty
        pydub.exceptions.CouldntDecodeError: If audio format is unsupported
    """
    if not audio_files:
        raise ValueError("audio_files cannot be empty")

    # Implementation...
```

#### Module Structure

Organize code into logical modules:

```
spelling_words/
├── __init__.py
├── word_list.py          # Word list management
├── dictionary_client.py  # API client for dictionaries
├── audio_processor.py    # Audio download and processing
├── apkg_manager.py       # APKG file operations
├── config.py             # Configuration management
└── cli.py                # Command-line interface
```

### Logging

Use Python's `logging` module, not `print()` statements.

**Setup**:
```python
import logging

# At module level
logger = logging.getLogger(__name__)

# In main or CLI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Usage**:
```python
logger.debug("Processing word: %s", word)
logger.info("Successfully created APKG with %d cards", card_count)
logger.warning("Word '%s' not found in elementary dictionary, trying collegiate", word)
logger.error("Failed to download audio for '%s'", word, exc_info=True)
```

### Environment Variables and Secrets

**NEVER** commit secrets to version control.

**DO**:
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env file

api_key = os.getenv("MW_ELEMENTARY_API_KEY")
if not api_key:
    raise ValueError("MW_ELEMENTARY_API_KEY environment variable not set")
```

**DON'T**:
```python
api_key = "abc123def456"  # Hard-coded secret - NEVER do this!
```

### Input Validation

Validate inputs early and explicitly.

```python
def create_note(word: str, definition: str, audio_filename: str) -> dict:
    """Create an Anki note dictionary."""
    if not word or not word.strip():
        raise ValueError("word cannot be empty")

    if not definition or not definition.strip():
        raise ValueError("definition cannot be empty")

    if not audio_filename.endswith(('.mp3', '.ogg', '.wav')):
        raise ValueError(f"Invalid audio format: {audio_filename}")

    # Proceed with validated inputs...
```

### SQL Safety

Use parameterized queries to prevent SQL injection.

**DO**:
```python
cursor.execute(
    "INSERT INTO notes (id, guid, mid, flds) VALUES (?, ?, ?, ?)",
    (note_id, guid, model_id, fields)
)
```

**DON'T**:
```python
# NEVER concatenate strings into SQL queries!
cursor.execute(f"INSERT INTO notes (id, flds) VALUES ({note_id}, '{fields}')")
```

## Testing Guidelines

### Test-Driven Development Philosophy

**CRITICAL DIRECTIVE: TEST INTEGRITY**

**NEVER remove, disable, or work around a failing test without explicit user review and approval.**

When a test fails:
1. **STOP** - Do not proceed with implementation
2. **ANALYZE** - Understand why the test is failing
3. **DISCUSS** - Present the failure to the user with:
   - Exact error message and stack trace
   - Analysis of the root cause
   - Proposed solutions (fix code vs. fix test)
4. **WAIT** - Get explicit user approval before:
   - Modifying the test expectations
   - Removing or commenting out the test
   - Adding `pytest.skip` or `pytest.xfail`
   - Working around the test

Tests are the specification. A failing test means either:
- The implementation is wrong (most common - fix the code)
- The test expectations are wrong (requires user discussion)
- The requirements have changed (requires user approval)

**Enforcement**: Every test file must include this directive as a comment at the top.

### Development Workflow

For each feature or module:

1. **Write tests FIRST** before writing implementation code
2. Run tests to verify they fail (red)
3. Implement the minimal code to make tests pass (green)
4. Refactor if needed while keeping tests green
5. Commit with passing tests

**Do NOT**:
- Write implementation code before writing tests
- Skip writing tests "to move faster"
- Commit code without corresponding tests

### Test Structure

Use pytest for testing:

```bash
uv add --dev pytest pytest-cov
```

### Test Organization

```
tests/
├── __init__.py
├── test_word_list.py
├── test_dictionary_client.py
├── test_audio_processor.py
└── test_apkg_manager.py
```

### Test Examples

```python
import pytest
from spelling_words.word_list import WordListManager

def test_load_word_list_success():
    """Test loading a valid word list."""
    manager = WordListManager()
    words = manager.load_from_file("tests/fixtures/sample_words.txt")
    assert len(words) == 5
    assert "apple" in words

def test_load_word_list_file_not_found():
    """Test that FileNotFoundError is raised for missing files."""
    manager = WordListManager()
    with pytest.raises(FileNotFoundError):
        manager.load_from_file("nonexistent.txt")

def test_validate_word_empty():
    """Test that empty words raise ValueError."""
    manager = WordListManager()
    with pytest.raises(ValueError, match="word cannot be empty"):
        manager.validate_word("")
```

## Code Quality Tools

### Ruff - Linting and Formatting

This project uses **ruff** for both linting and code formatting. Ruff is an extremely fast Python linter and formatter written in Rust that replaces multiple tools (flake8, black, isort, etc.).

**Running ruff manually**:
```bash
# Check for linting issues
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check and format in one go
uv run ruff check --fix . && uv run ruff format .
```

**Configuration**: Ruff is configured in `pyproject.toml` with:
- Line length: 100 characters
- Python target: 3.12
- Enabled rule sets: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, bugbear, and more
- Auto-fix enabled for most rules

**Key rules enforced**:
- Import sorting (isort)
- PEP 8 naming conventions
- Bugbear patterns (common bugs)
- Use of pathlib over os.path
- Modern Python syntax (pyupgrade)
- Simplified code patterns

### Pre-commit Hooks

This project uses **pre-commit** to automatically run checks before each commit.

**Installation**:
```bash
# Install pre-commit hooks (run once after cloning)
uv run pre-commit install
```

**What runs on each commit**:
1. **Ruff linting** with auto-fix
2. **Ruff formatting**
3. **Trailing whitespace removal**
4. **End-of-file fixer**
5. **YAML syntax check**
6. **Large file check** (max 1MB)
7. **Merge conflict detection**
8. **Private key detection**

**Manual execution**:
```bash
# Run on all files
uv run pre-commit run --all-files

# Run on specific files
uv run pre-commit run --files spelling_words/cli.py

# Skip hooks temporarily (discouraged)
git commit --no-verify
```

**Bypassing hooks**: Only skip pre-commit hooks if absolutely necessary (e.g., emergency hotfix). The `--no-verify` flag should be rare.

## Git Workflow

### Branching

- Work on feature branches following the pattern: `claude/plan-anki-spelling-package-<session-id>`
- Commit frequently with clear, descriptive messages

### Commit Messages

```
Add audio concatenation functionality

- Implement concatenate_audio_files() in audio_processor.py
- Add 1-second gap between pronunciations
- Support MP3 output format
- Include unit tests
```

### Before Committing

Pre-commit hooks will automatically run, but you can also run checks manually:

1. **Format and lint code**: `uv run ruff check --fix . && uv run ruff format .`
2. **Run tests**: `uv run pytest`
3. **Run all pre-commit checks**: `uv run pre-commit run --all-files`
4. **Review changes**: `git diff`

**Note**: If pre-commit hooks are installed, steps 1 and 3 will run automatically on `git commit`.

## Common Patterns

### API Client Pattern

```python
class DictionaryClient:
    """Client for Merriam-Webster Dictionary API."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key
        self.base_url = "https://dictionaryapi.com/api/v3/references/sd/json"

    def get_word_data(self, word: str) -> dict:
        """Fetch word data from API."""
        if not word or not word.strip():
            raise ValueError("word cannot be empty")

        try:
            response = requests.get(
                f"{self.base_url}/{word}",
                params={"key": self.api_key},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            logger.error(f"Timeout fetching data for '{word}'", exc_info=True)
            raise
        except requests.HTTPError:
            logger.error(f"HTTP error fetching data for '{word}'", exc_info=True)
            raise
```

### Resource Management

Use context managers for file and database operations:

```python
# File operations
with zipfile.ZipFile(apkg_path, 'r') as zf:
    compressed_data = zf.read('collection.anki21b')

# Database operations
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes")
    # Changes automatically committed on successful exit
```

## Performance Considerations

### Caching

Cache API responses and downloaded files to avoid redundant requests:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_word_definition(word: str) -> str:
    """Get word definition (cached)."""
    return dictionary_client.get_definition(word)
```

Or use file-based caching for audio:

```python
def get_audio_cached(word: str, cache_dir: Path) -> bytes:
    """Download audio or return from cache."""
    cache_file = cache_dir / f"{word}.mp3"
    if cache_file.exists():
        logger.debug(f"Using cached audio for '{word}'")
        return cache_file.read_bytes()

    audio_data = download_audio(word)
    cache_file.write_bytes(audio_data)
    return audio_data
```

## Documentation

### Inline Comments

Use comments to explain **why**, not **what**:

```python
# Good - explains the reasoning
# Use elementary dictionary first as it's more appropriate for spelling tests
data = client.get_elementary(word)

# Bad - just restates the code
# Call get_elementary method with word parameter
data = client.get_elementary(word)
```

### README vs Other Docs

- **README.md**: Human-authored, user-facing documentation
- **DESIGN.md**: Architecture and technical design decisions
- **REFERENCE.md**: Technical references and external resources
- **CLAUDE.md**: Development guidelines for AI assistants (this file)

## Additional Resources

- **uv Documentation**: https://github.com/astral-sh/uv
- **Python Logging**: https://docs.python.org/3/library/logging.html
- **pytest Documentation**: https://docs.pytest.org/
- **Type Hints**: https://docs.python.org/3/library/typing.html
