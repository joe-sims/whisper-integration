# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

This is a Whisper audio transcription integration that provides a Python wrapper around OpenAI's Whisper model for converting audio files to text with optional timestamps.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Basic transcription
python3 src/cli.py my_recording.m4a

# Fast transcription
python3 src/cli.py my_recording.m4a --fast

# Batch process all files
python3 src/cli.py --batch audio_input/
```

## Architecture

### Core Components

- **WhisperTranscriber** (`whisper_transcriber.py`): Main transcription class
  - `transcribe_file()`: Full transcription with metadata
  - `transcribe_with_timestamps()`: Adds word-level timestamps  
  - `get_text_only()`: Returns plain text only
- **CLI Interface** (`src/cli.py`): Unified command-line interface
- **Audio Converter** (`convert_audio.py`): Audio format conversion utility

### File Structure

```
whisper-integration/
├── audio_input/        # Place audio files here
├── transcriptions/     # Generated transcripts
├── src/
│   └── cli.py         # Main CLI interface
├── whisper_transcriber.py
└── requirements.txt
```

## CLI Usage

### Basic Syntax
```bash
python3 src/cli.py <audio_filename> [OPTIONS]
```

### Common Commands
```bash
# Different model sizes
python3 src/cli.py recording.m4a --model tiny    # Fastest
python3 src/cli.py recording.m4a --model base    # Default
python3 src/cli.py recording.m4a --model large   # Most accurate

# Include timestamps
python3 src/cli.py recording.m4a --timestamps

# Specify language
python3 src/cli.py recording.m4a --language en

# Batch processing
python3 src/cli.py --batch audio_input/

# Verbose output
python3 src/cli.py recording.m4a --verbose
```

### CLI Options
| Option | Description | Default |
|--------|-------------|---------|
| `--model {tiny,base,small,medium,large}` | Whisper model size | `base` |
| `--fast` | Use tiny model (fastest) | - |
| `--batch DIR` | Process all files in directory | - |
| `--timestamps` | Include timestamped segments | disabled |
| `--no-timestamps` | Skip timestamps (legacy) | - |
| `--language LANG` | Force language (e.g., "en", "es") | auto-detect |
| `--task {transcribe,translate}` | Task type | `transcribe` |
| `--verbose, -v` | Detailed logging | - |

## Models & Performance

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| `tiny` | Fastest | Basic | Quick drafts, testing |
| `base` | Fast | Good | Default choice |
| `small` | Medium | Better | Higher accuracy needed |
| `medium` | Slow | Very good | Professional use |
| `large` | Slowest | Best | Maximum accuracy |

## Setup & Dependencies

### System Requirements
- Python 3.7+
- ffmpeg (must be installed system-wide)

### Installation
```bash
pip install -r requirements.txt
```

**Important**: numpy must be <2.3 for numba compatibility:
```bash
pip install "numpy<2.3"
```

### Supported Audio Formats
WAV, MP3, M4A, FLAC, and other formats supported by ffmpeg.

## Output Format

Generated files follow the pattern: `{filename}_transcription_{timestamp}.txt`

**File contents:**
- Full transcription text
- Generation metadata (timestamp, model, language)
- Timestamped segments (when `--timestamps` enabled)
- UTF-8 encoding

## Archive Management

The system includes built-in archive functionality to manage transcription and summary files:

### Archive Commands
```bash
# Show file statistics
python3 src/cli.py archive --stats

# List duplicate files
python3 src/cli.py archive --list-duplicates

# Archive duplicates (keeps latest versions)
python3 src/cli.py archive --clean-duplicates --dry-run  # Preview
python3 src/cli.py archive --clean-duplicates            # Execute

# Archive old files
python3 src/cli.py archive --clean-old --days 30

# Archive processed audio files (from pipeline)
python3 src/cli.py archive --clean-audio --days 14

# Standalone archive script
python3 archive.py --stats
```

### Archive Structure
```
archive/
├── transcriptions/
│   └── 2025-08/        # Organized by year-month
├── summaries/
│   └── 2025-08/
└── audio/              # Long-term archived audio files
```

### Archive Features
- **Duplicate Management**: Automatically identifies and archives duplicate files while preserving the latest version
- **Date Organization**: Archives files into year-month directory structure
- **Processed Audio Archiving**: Manages audio files processed through the meeting pipeline
- **Dry Run Mode**: Preview changes before executing with `--dry-run`
- **Old File Cleanup**: Archive files older than specified days
- **Statistics**: Track active vs archived file counts across all file types
- **Safe Operation**: Moves files (doesn't delete) for easy recovery

### File Flow
```
audio_input/ → [Pipeline] → processed/ → [Archive] → archive/audio/
                     ↓
transcriptions/ → [Archive] → archive/transcriptions/
                     ↓
summaries/ → [Archive] → archive/summaries/
```

## Implementation Notes

- Models are cached after first load for performance
- Audio is processed at 16kHz (Whisper standard)
- Timestamps have 2 decimal place precision
- Comprehensive error handling for files and model loading
- All text output uses UTF-8 encoding
- Archive operations preserve file integrity and organize by date