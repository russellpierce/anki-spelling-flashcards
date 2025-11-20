# Design Document: Anki Spelling Words Package

## Project Overview

This package automates the creation and updating of Anki (APKG) flashcard decks for spelling test preparation. It generates cards with audio pronunciations and definitions, suitable for elementary and middle school spelling bee practice.

**Target Platform**: Ubuntu 24.04
**Language**: Python 3.x
**Package Manager**: uv

## System Architecture

### High-Level Components

```
┌─────────────────┐
│  Word List      │
│  Input          │
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌──────────────────┐
│  Dictionary     │────▶│  Audio           │
│  API Client     │     │  Downloader      │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         │  (definition)         │  (audio files)
         │                       │
         v                       v
┌─────────────────────────────────────────┐
│  Audio Processor                        │
│  - Concatenate multiple pronunciations  │
│  - Add 1-second gaps                    │
│  - Convert to compatible format         │
└────────────────┬────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────┐
│  APKG Manager                           │
│  - Read existing APKG                   │
│  - Update notes table                   │
│  - Update media files                   │
│  - Recompress and package               │
└─────────────────────────────────────────┘
                 │
                 v
┌─────────────────┐
│  Output APKG    │
└─────────────────┘
```

## Core Components

### 1. Word List Manager

**Purpose**: Handle input of word lists

**Responsibilities**:
- Read word lists from file (TXT, CSV, JSON)
- Validate word format
- Handle duplicates
- Provide word iteration interface

**MVP**: Simple text file input (one word per line)

### 2. Dictionary API Client

**Purpose**: Fetch word definitions and audio URLs

**Responsibilities**:
- Query Merriam-Webster Elementary Dictionary API (primary)
- Fallback to Merriam-Webster Collegiate Dictionary API
- Parse API responses
- Extract definitions, audio URLs, and pronunciation variants
- Handle API errors and rate limiting
- Manage API key from environment variables

**Data Retrieved**:
- Word definitions
- Audio file URLs (may be multiple for different pronunciations)
- Pronunciation symbols (future)
- Etymology/language tips (future)

### 3. Audio Downloader

**Purpose**: Download audio files from dictionary APIs

**Responsibilities**:
- Download audio files from URLs
- Handle multiple pronunciations per word
- Cache downloaded files
- Validate audio file format
- Handle network errors with retry logic

### 4. Audio Processor

**Purpose**: Process and format audio for Anki

**Responsibilities**:
- Load audio files (MP3, WAV, etc.)
- Concatenate multiple pronunciations with 1-second gaps
- Convert to target format (MP3 recommended)
- Normalize audio levels (optional, future enhancement)
- Generate unique filenames

**Dependencies**: pydub, ffmpeg (system)

### 5. APKG Manager

**Purpose**: Create or update APKG files

**Responsibilities**:
- Read and decompress existing APKG files
- Parse SQLite database (collection.anki21b)
- Extract model ID from existing notes
- Generate new note IDs (millisecond timestamp)
- Generate GUIDs (random 10-character strings)
- Format note fields with `\x1f` separator
- Update notes table in SQLite database
- Manage media index mapping
- Compress media files with Zstandard
- Recompress SQLite database
- Package everything into new APKG file

**Key Operations**:
- Decompress: `zstandard.ZstdDecompressor()`
- Compress: `zstandard.ZstdCompressor()`
- Database: `sqlite3` module
- Archive: `zipfile` module

### 6. Configuration Manager

**Purpose**: Manage application configuration

**Responsibilities**:
- Load API keys from `.env` file
- Provide configuration access throughout application
- Validate required configuration

**Environment Variables**:
- `MW_ELEMENTARY_API_KEY`: Merriam-Webster Elementary Dictionary API key
- `MW_COLLEGIATE_API_KEY`: Merriam-Webster Collegiate Dictionary API key (fallback)

## Card Structure

### Front of Card (Question)

```
[sound:word_combined.mp3]

Definition: <word definition from dictionary>
```

**Future Enhancements**:
- Headscratcher language tips
- Pronunciation symbols (IPA)
- Spelling suggestions/hints

### Back of Card (Answer)

```
word
```

Where `word` is the lowercase spelling.

**Future Enhancements**:
- Etymology
- Usage examples
- Part of speech

## Development Phases

### Phase 1: MVP (Minimum Viable Product)

**Goal**: Create basic APKG files with audio and definitions

**Features**:
- Read word list from simple text file (one word per line)
- Query Merriam-Webster Elementary Dictionary API
- Download single pronunciation audio file per word
- Extract basic definition
- Create new APKG file with notes containing:
  - Audio reference on front
  - Definition on front
  - Lowercase word on back
- Basic error handling and logging

**Deliverables**:
- Working Python package installable via uv
- Command-line interface (CLI) for basic usage
- `.env.example` file with required API keys
- Basic documentation

**Success Criteria**:
- Can process a list of 20 common spelling words
- Generates valid APKG file loadable in AnkiDroid
- Cards display audio and definition correctly

### Phase 2: Enhanced Audio Processing

**Goal**: Handle multiple pronunciations and improve audio quality

**Features**:
- Download multiple pronunciations when available
- Concatenate pronunciations with 1-second gaps
- Audio format conversion and validation
- Fallback to Collegiate Dictionary API
- Audio caching to avoid re-downloads

**Deliverables**:
- Enhanced audio processing module
- Cache management
- Improved error handling for API failures

**Success Criteria**:
- Correctly handles words with 2+ pronunciations
- Gracefully falls back between API sources
- Reduces redundant downloads via caching

### Phase 3: APKG Update Support

**Goal**: Update existing APKG files instead of creating new ones

**Features**:
- Read existing APKG files
- Extract current notes and media
- Add new words without duplicating existing ones
- Preserve existing card scheduling data
- Update media index correctly

**Deliverables**:
- APKG update functionality
- Duplicate detection
- Preserves user study progress

**Success Criteria**:
- Can add 10 new words to existing 50-card deck
- No data loss or corruption
- Scheduling information preserved

### Phase 4: Enhanced Card Content

**Goal**: Add richer information to cards

**Features**:
- Pronunciation symbols (IPA)
- Etymology information
- Usage examples
- Language tips ("headscratchers")
- Spelling suggestions/patterns
- Part of speech

**Deliverables**:
- Enhanced card templates
- Additional data extraction from APIs
- Configurable card fields

**Success Criteria**:
- Cards include at least 3 additional data points
- Information displayed clearly in AnkiDroid
- Helps students better understand words

### Phase 5: Advanced Features

**Goal**: Production-ready features and polish

**Features**:
- Multiple input formats (CSV, JSON, Google Sheets integration)
- Batch processing optimizations
- Rate limiting and API quota management
- Text-to-Speech fallback for missing audio
- Progress reporting and detailed logging
- Configuration file support
- Word list validation (spell checking, difficulty levels)
- Custom card templates

**Deliverables**:
- Comprehensive CLI with all options
- Detailed logging and diagnostics
- Production documentation
- Test suite

## Technical Decisions

### Why MP3 for Audio?

- Widely supported by Anki/AnkiDroid
- Good compression ratio
- Simpler than 3GP conversion
- Supported by pydub with minimal configuration

### Why Zstandard?

- Required by APKG format (collection.anki21b)
- Efficient compression/decompression
- Well-supported Python library available

### Why SQLite?

- Required by APKG format
- Built-in Python support (sqlite3 module)
- Lightweight and efficient

### Why uv?

- Fast Python package management
- Modern dependency resolution
- Simpler than traditional pip/virtualenv workflow
- Good for reproducible builds

## Error Handling Strategy

Per project coding standards:

1. **Raise specific exception types** (not generic `Exception`)
2. **Try/catch only for known, resolvable exceptions**
3. **Log raised errors with full stack traces**
4. **Validate inputs early** (word lists, API keys, file paths)
5. **Graceful degradation** (fallback APIs, skip problematic words)

## Testing Strategy

**Phase 1 (MVP)**:
- Manual testing with small word lists (5-20 words)
- Verify APKG loads in AnkiDroid

**Phase 2+**:
- Unit tests for each component
- Integration tests for full workflow
- Test with various edge cases:
  - Words not found in dictionary
  - Words with special characters
  - Very long word lists
  - API failures/timeouts
  - Corrupted APKG files

## Security Considerations

1. **API Keys**: Never commit to version control, use `.env` file
2. **Input Validation**: Sanitize word inputs to prevent injection
3. **File Paths**: Validate paths to prevent directory traversal
4. **SQL**: Use parameterized queries to prevent SQL injection

## Future Enhancements (Beyond Phase 5)

- Web interface for non-technical users
- Cloud storage integration (Google Drive, Dropbox)
- Collaborative word lists
- Pre-built word lists (grade level, spelling bee competitions)
- Mobile app for direct integration with AnkiDroid
- Support for other Anki platforms (desktop, iOS)
