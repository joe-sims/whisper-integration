# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Whisper audio transcription integration that provides a Python wrapper around OpenAI's Whisper model for converting audio files to text with timestamps.

## Core Architecture

- **WhisperTranscriber** (`whisper_transcriber.py`): Main class that wraps Whisper functionality with three key methods:
  - `transcribe_file()`: Full transcription with metadata
  - `transcribe_with_timestamps()`: Adds word-level timestamps
  - `get_text_only()`: Returns just the transcribed text
- **CLI Interface** (`example_usage.py`): Command-line script that processes audio files and saves results to `.txt` files
- **Audio Converter** (`convert_audio.py`): Utility for converting audio formats using Whisper's built-in loader

## Dependencies and Setup

Install dependencies with:
```bash
pip install -r requirements.txt
```

Critical dependency note: numpy must be <2.3 for numba compatibility:
```bash
pip install "numpy<2.3"
```

## Running Transcriptions

The project requires ffmpeg for audio processing. A local copy is included in `bin/ffmpeg`.

## File Organization

The project uses an organized folder structure:
- `audio_input/`: Place audio files here for transcription
- `transcriptions/`: Generated transcription files are saved here
- `bin/`: Contains local ffmpeg binary

## Unified CLI Interface

The project now uses a unified CLI script (`src/cli.py`) that replaces the old separate scripts with enhanced functionality:

```bash
PATH="/Users/joesims/whisper-integration/bin:$PATH" python3 src/cli.py <audio_filename> [OPTIONS]
```

### Basic Examples:
```bash
# Basic transcription with default base model
python3 src/cli.py my_recording.m4a

# Fast transcription with tiny model
python3 src/cli.py my_recording.m4a --fast

# High accuracy with large model
python3 src/cli.py my_recording.m4a --model large

# Text only (no timestamps)
python3 src/cli.py my_recording.m4a --no-timestamps

# Batch process all files in audio_input/
python3 src/cli.py --batch audio_input/

# Force specific language
python3 src/cli.py my_recording.m4a --language en
```

### CLI Options:
- `--model {tiny,base,small,medium,large}`: Choose Whisper model (default: base)
- `--fast`: Fast mode (equivalent to --model tiny)
- `--batch DIR`: Process all audio files in directory
- `--no-timestamps`: Skip timestamped segments
- `--language LANGUAGE`: Force specific language (e.g., "en", "es", "fr")  
- `--task {transcribe,translate}`: Task to perform
- `--verbose, -v`: Enable detailed logging

Supported formats: WAV, MP3, M4A, FLAC, and more.

Output: Creates a timestamped `.txt` file in the `transcriptions/` subfolder with format `{filename}_transcription_{timestamp}.txt` containing:
- Full transcription text
- Generation timestamp and model used
- Detected language
- Timestamped segments

## Model Selection

WhisperTranscriber supports different model sizes via the `model_name` parameter:
- `"tiny"`: Fastest, least accurate
- `"base"`: Default, balanced speed/accuracy
- `"small"`, `"medium"`, `"large"`: Increasing accuracy and processing time

## Key Implementation Details

- Models are loaded once during initialization and cached
- Audio processing uses 16kHz sample rate (Whisper standard)
- Timestamp precision is to 2 decimal places
- Error handling includes file existence checks and model loading validation
- All output files use UTF-8 encoding