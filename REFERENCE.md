# Reference Documentation

This document contains technical references and resources for the Anki Spelling Words package.

## AnkiDroid Documentation

- **Main Documentation**: https://docs.ankidroid.org/
- **AnkiDroid GitHub Repository**: https://github.com/ankidroid/Anki-Android
- **APKG File Format Specification**: https://docs.fileformat.com/web/apkg/

## APKG File Format

### File Structure

The APKG file is a ZIP archive containing:

- **collection.anki21b**: Zstandard-compressed SQLite database (main data)
- **collection.anki2**: Legacy SQLite database (for backwards compatibility)
- **media**: JSON file mapping media IDs to filenames (keys are numeric strings like "0", "1", "2")
- **Numbered files** (0, 1, 2, etc.): Zstandard-compressed media files (audio, images, etc.)
- **meta**: Metadata file

### Database Schema

The `collection.anki21b` SQLite database contains several tables. The most important for our use case are:

#### notes table (flashcard content)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Unique note ID (millisecond timestamp) |
| guid | TEXT | Unique identifier string |
| mid | INTEGER | Model ID (card template type) |
| mod | INTEGER | Modification timestamp |
| usn | INTEGER | Update sequence number (-1 for new cards) |
| tags | TEXT | Space-separated tags |
| flds | TEXT | Field data separated by `\x1f` character (front/back content) |
| sfld | TEXT | Sort field (first field, used for sorting) |
| csum | INTEGER | Checksum for duplicate detection |
| flags | INTEGER | Flags (usually 0) |
| data | TEXT | Additional data (usually empty) |

#### cards table (scheduling data)

Links to notes and tracks review statistics, study intervals, etc.

### Media Handling

- Media files are referenced in notes using `[sound:filename.mp3]` syntax
- The `media` JSON file maps numeric indices to filenames: `{"0": "word1.mp3", "1": "word2.mp3"}`
- Media files are stored as numbered files in the ZIP, compressed with Zstandard

## Dictionary and Audio APIs

### Primary: Merriam-Webster Elementary Dictionary API

- **Product Page**: https://dictionaryapi.com/products/api-elementary-dictionary
- **Features**: Designed for elementary/middle school level
- **Audio**: Provides pronunciation audio files
- **Authentication**: Requires API key
- **Rate Limits**: Check current terms at API product page

### Fallback: Merriam-Webster Collegiate Dictionary API

- **Product Page**: https://dictionaryapi.com/products/api-collegiate-dictionary
- **Features**: Comprehensive dictionary with adult vocabulary
- **Audio**: Provides pronunciation audio files
- **Authentication**: Requires API key
- **Use Case**: Fallback when word not found in elementary dictionary

### Alternative: Free Dictionary API

- **Endpoint**: `https://api.dictionaryapi.dev/api/v2/entries/en/{word}`
- **Features**: Free, no authentication required
- **Audio**: Includes phonetics and audio URLs
- **Limitations**: May not have all words, less reliable

### Text-to-Speech Options (Future)

If dictionary APIs don't have audio:

- **Google Cloud Text-to-Speech**: 1M characters/month free tier
- **Azure Speech**: 5M characters/month free trial
- **Amazon Polly**: Pay-as-you-go, ~$4/1M characters

## Audio Processing

### Supported Formats

Anki supports multiple audio formats:
- **MP3**: Recommended for simplicity and wide compatibility
- **OGG**: Open source alternative
- **WAV**: Uncompressed, larger files
- **3GP**: Mobile format (original format in some APKG files)

### Audio Concatenation

For words with multiple pronunciations, audio files should be:
1. Downloaded/generated separately
2. Concatenated with 1-second gaps between pronunciations
3. Converted to target format (MP3 recommended)

### Required Libraries

- **pydub**: Python library for audio manipulation
  - System dependency: **ffmpeg** (must be installed on Ubuntu)
- **zstandard**: Compression/decompression for APKG files
- **requests**: For API calls
- **sqlite3**: Built-in Python library for database operations

### Audio Conversion Example

```python
from pydub import AudioSegment

# Load audio files
audio1 = AudioSegment.from_mp3("pronunciation1.mp3")
audio2 = AudioSegment.from_mp3("pronunciation2.mp3")

# Create 1-second silence
silence = AudioSegment.silent(duration=1000)  # milliseconds

# Concatenate with gap
combined = audio1 + silence + audio2

# Export as MP3
combined.export("word.mp3", format="mp3", bitrate="128k")
```

## Python Libraries

### Core Dependencies

- **zstandard**: APKG compression/decompression
- **pydub**: Audio file manipulation
- **requests**: HTTP requests for API calls
- **python-dotenv**: Environment variable management

### System Dependencies

- **ffmpeg**: Required by pydub for audio format conversion
  - Install on Ubuntu: `sudo apt-get install ffmpeg`

## Spelling Bee Context

### Card Front (Question Side)

Should include everything a student can ask for in a spelling bee:
- **Audio pronunciation**: Multiple pronunciations if available
- **Definition**: From dictionary API
- **Future enhancements**:
  - "Headscratcher" language tips
  - Pronunciation symbols (IPA)
  - Spelling suggestions

### Card Back (Answer Side)

Should include:
- **Word**: Lowercase spelling
- **Future enhancements**:
  - Additional learning aids
  - Etymology
  - Usage examples

## Development References

- **uv Documentation**: https://github.com/astral-sh/uv (Python package manager)
