# Whisper Audio Transcription Integration

**v2.0.0** - Professional meeting transcription and summarization with AI-powered role-based analysis.

A comprehensive solution that transforms audio recordings into structured meeting notes with intelligent categorization, professional summaries, and seamless Notion integration.

## ✨ Key Features

- 🎙️ **High-quality transcription** using OpenAI Whisper models
- 🤖 **AI-powered summarization** with Claude using role-based prompts  
- 📊 **6 specialized meeting types**: 1:1, forecast, customer, technical, strategic, team
- 🧠 **Auto meeting type detection** from transcript content
- 📝 **Professional templates** tailored for managers and solutions engineers
- 🔗 **Notion integration** with automatic task creation and linking
- 🔒 **Enterprise security** with environment variable credential management
- ⚡ **Complete pipeline** from audio → transcript → summary → structured notes

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

# Include timestamped segments
python3 src/cli.py audio_file.m4a --timestamps
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
| `--timestamps` | Include timestamped segments | False |
| `--no-timestamps` | Skip timestamped segments (backwards compatibility) | - |
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
- Timestamped segments (only when --timestamps is used)

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

## 🚀 Meeting Pipeline (v2.0.0)

The enhanced **Meeting Pipeline** provides intelligent, role-based meeting analysis:

### Quick Start
```bash
# Set up environment variables (first time only)
cp .env.example .env  # Edit with your API keys

# Full workflow: Transcribe → AI Summary → Notion Integration
python3 src/meeting_pipeline.py meeting.m4a

# Force specific meeting type
python3 src/meeting_pipeline.py meeting.m4a --meeting-type 1:1
python3 src/meeting_pipeline.py forecast.m4a --meeting-type forecast
```

### 🧠 Intelligent Features
- **Auto-detects meeting type** from content (1:1, forecast, customer, etc.)
- **Role-based AI summaries** tailored for engineering managers
- **Action item extraction** with automatic task creation in Notion
- **Professional formatting** with proper business context
- **Direct task linking** back to source meeting pages

### 📊 Specialized Meeting Types
| Type | Use Case | Key Sections |
|------|----------|--------------|
| **1:1** | Performance reviews, coaching | Employee overview, development plans, manager notes |
| **Forecast** | Sales pipeline reviews | Deal tables, risk assessment, commitments |
| **Customer** | Client meetings, demos | Requirements, solutions mapping, next steps |
| **Technical** | Architecture discussions | Technical decisions, integration challenges |
| **Strategic** | Business planning | Market analysis, competitive positioning |
| **Team** | Weekly syncs, standups | Project status, team health, coordination |

### 🔒 Secure Setup
```bash
# Create .env file with your API keys
ANTHROPIC_API_KEY=your-claude-key
NOTION_TOKEN=your-notion-token
NOTION_DATABASE_ID=your-meeting-database-id
NOTION_TASK_DATABASE_ID=your-task-database-id
```

All credentials are securely managed via environment variables - no hardcoded secrets!

## Acknowledgments

Built on OpenAI's Whisper model for state-of-the-art speech recognition.