# Whisper Audio Transcription Integration

A Python wrapper around OpenAI's Whisper model for converting audio files to text with timestamps.

## Features

- 🎙️ High-quality audio transcription using OpenAI Whisper
- ⏱️ Word-level and segment-level timestamps
- 🔄 Multiple model sizes (tiny to large) for speed/accuracy tradeoffs
- 📁 Batch processing support
- 🌍 Multi-language support with auto-detection
- 📝 Clean text output with organized file structure

## Installation

### Prerequisites

**ffmpeg** is required for audio processing. Install it first:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use:
```bash
winget install ffmpeg
```

### Install the Project

1. Clone this repository:
```bash
git clone https://github.com/joe-sims/whisper-integration.git
cd whisper-integration
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

**Important**: Ensure numpy version compatibility:
```bash
pip install "numpy<2.3"
```

## Quick Start

Place your audio files in the `audio_input/` directory and run:

```bash
# Basic transcription
python3 src/cli.py my_recording.m4a

# Fast transcription (tiny model)
python3 src/cli.py my_recording.m4a --fast

# High accuracy (large model)
python3 src/cli.py my_recording.m4a --model large
```

## Usage

### Basic Commands

```bash
# Transcribe a single file
python3 src/cli.py audio_file.m4a

# Batch process all files in a directory
python3 src/cli.py --batch audio_input/

# Text-only output (no timestamps)
python3 src/cli.py audio_file.m4a --no-timestamps
```

### Advanced Options

```bash
# Specify model size
python3 src/cli.py audio_file.m4a --model {tiny,base,small,medium,large}

# Force specific language
python3 src/cli.py audio_file.m4a --language en

# Translation to English
python3 src/cli.py audio_file.m4a --task translate

# Verbose output
python3 src/cli.py audio_file.m4a --verbose
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | Whisper model size (tiny, base, small, medium, large) | base |
| `--fast` | Use tiny model for fast processing | - |
| `--batch DIR` | Process all audio files in directory | - |
| `--no-timestamps` | Skip timestamped segments | False |
| `--language` | Force specific language (e.g., "en", "es", "fr") | auto-detect |
| `--task` | Task to perform (transcribe, translate) | transcribe |
| `--verbose, -v` | Enable detailed logging | False |

## Supported Audio Formats

- WAV
- MP3
- M4A
- FLAC
- And more formats supported by ffmpeg

## Output Format

Transcriptions are saved to the `transcriptions/` folder with the format:
`{filename}_transcription_{timestamp}.txt`

Each file contains:
- Full transcription text
- Generation timestamp and model used
- Detected language
- Timestamped segments (unless --no-timestamps is used)

## Project Structure

```
whisper-integration/
├── src/
│   ├── cli.py                 # Unified CLI interface
│   ├── whisper_transcriber.py # Core transcription class
│   └── __init__.py
├── audio_input/               # Place audio files here
├── transcriptions/            # Generated transcription files
├── requirements.txt
└── README.md
```

## Core Classes

### WhisperTranscriber

The main transcription class with three key methods:

- `transcribe_file()`: Full transcription with metadata
- `transcribe_with_timestamps()`: Adds word-level timestamps  
- `get_text_only()`: Returns just the transcribed text

## Model Performance

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| tiny | Fastest | Basic | Quick drafts, real-time |
| base | Fast | Good | General purpose (default) |
| small | Medium | Better | Balanced processing |
| medium | Slow | High | Important documents |
| large | Slowest | Highest | Critical accuracy needs |

## Requirements

- Python 3.7+
- ffmpeg (system installation required)
- Dependencies listed in `requirements.txt`

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

**ImportError with numpy/numba**: Ensure numpy version is < 2.3:
```bash
pip install "numpy<2.3"
```

**ffmpeg not found**: Ensure ffmpeg is installed on your system:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian  
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

**Memory issues with large models**: Use smaller models (tiny, base) for systems with limited RAM.

## Acknowledgments

Built on OpenAI's Whisper model for state-of-the-art speech recognition.