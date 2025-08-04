# Meeting Pipeline: Transcribe → Summarize → Notion

Complete workflow for processing meeting recordings into structured notes.

## Overview

The meeting pipeline automates the process of:
1. **Transcribing** audio files using Whisper
2. **Summarizing** transcripts using Claude API
3. **Creating** structured notes in Notion

## Quick Start

### 1. Install Dependencies

```bash
# Install pipeline dependencies
pip install -r requirements-pipeline.txt

# Install main project dependencies (if not already done)
pip install -r requirements.txt
```

### 2. Set Up API Keys

**Option A: Environment Variables (Recommended)**
```bash
export ANTHROPIC_API_KEY="your-claude-api-key"
export NOTION_TOKEN="your-notion-integration-token"
export NOTION_DATABASE_ID="your-database-id"
```

**Option B: Configuration File**
```bash
# Copy and edit the config file
cp config/pipeline_config.yaml config/my_config.yaml
# Edit my_config.yaml with your API keys
```

### 3. Set Up Notion Database

1. Create a new Notion database with these properties:
   - **Title** (Title)
   - **Date** (Date)
   - **Type** (Select) - options: "Meeting", "Call", "Interview"
   - **Status** (Select) - options: "Processed", "Review", "Done"
   - **Participants** (Multi-select)
   - **Audio File** (URL)

2. Get your database ID from the URL:
   ```
   https://notion.so/workspace/DATABASE_ID?v=...
   ```

3. Create a Notion integration at https://www.notion.so/my-integrations
4. Share your database with the integration

### 4. Run the Pipeline

```bash
# Full pipeline
python3 src/meeting_pipeline.py meeting_recording.m4a

# With custom config
python3 src/meeting_pipeline.py meeting_recording.m4a --config config/my_config.yaml

# Skip Notion integration (just transcribe + summarize)
python3 src/meeting_pipeline.py meeting_recording.m4a --skip-notion
```

## Usage Examples

### Basic Usage
```bash
# Process with default settings
python3 src/meeting_pipeline.py audio_input/team_meeting.m4a
```

### Advanced Options
```bash
# Use large Whisper model for better accuracy
python3 src/meeting_pipeline.py audio_input/important_call.m4a --model large

# Skip transcription (use existing transcript)
python3 src/meeting_pipeline.py audio_input/meeting.m4a --skip-transcribe

# Skip Notion integration
python3 src/meeting_pipeline.py audio_input/meeting.m4a --skip-notion

# Verbose logging
python3 src/meeting_pipeline.py audio_input/meeting.m4a --verbose
```

## Configuration

### Summary Templates

The pipeline includes different summary templates:

- **business** (default): Structured business meeting summary
- **technical**: Technical discussion focused summary  
- **personal**: Casual conversation summary
- **default**: Simple summary format

### Whisper Models

- **tiny**: Fastest, least accurate
- **base** (default): Good balance of speed/accuracy
- **small/medium/large**: Increasing accuracy and processing time

## API Setup Guides

### Claude API Setup

1. Go to https://console.anthropic.com/
2. Create an account and get API access
3. Generate an API key
4. Set `ANTHROPIC_API_KEY` environment variable

### Notion API Setup

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it "Meeting Pipeline" and select your workspace
4. Copy the "Internal Integration Token"
5. Set `NOTION_TOKEN` environment variable
6. Share your database with the integration:
   - Open your database in Notion
   - Click "Share" → "Invite"
   - Select your integration

## Troubleshooting

### Common Issues

**"anthropic package not installed"**
```bash
pip install anthropic
```

**"notion-client package not installed"**
```bash
pip install notion-client
```

**"Claude API key not found"**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**"Notion token not found"**
```bash
export NOTION_TOKEN="your-token-here"
export NOTION_DATABASE_ID="your-database-id"
```

**"No database_id configured"**
- Make sure you've set `NOTION_DATABASE_ID` environment variable
- Or add `database_id` to your config file

### Debug Mode

```bash
python3 src/meeting_pipeline.py meeting.m4a --verbose
```

## Architecture

```
meeting_pipeline.py              # Main pipeline script
├── integrations/
│   ├── claude_summarizer.py     # Claude API integration
│   └── notion_client.py         # Notion API integration
├── config/
│   └── pipeline_config.yaml     # Configuration template
└── requirements-pipeline.txt    # Additional dependencies
```

## Output

The pipeline creates:

1. **Console Output**: Progress and results summary
2. **Notion Page**: Structured meeting notes with:
   - Meeting summary
   - Full transcript (collapsible)
   - Metadata (date, participants, etc.)
3. **Transcript File**: Local backup in `transcriptions/` folder

## Cost Considerations

- **Whisper**: Free (runs locally)
- **Claude**: ~$0.0008 per 1K input tokens (Haiku model)
- **Notion**: Free for personal use

A typical 30-minute meeting costs ~$0.05-0.20 in Claude API fees.

## Security

- API keys are stored in environment variables or config files
- Audio files are processed locally
- Only transcript text is sent to external APIs
- Notion pages respect your workspace permissions

## Next Steps

- **Batch Processing**: Process multiple recordings at once
- **Email Integration**: Send summaries via email
- **Calendar Integration**: Link to calendar events
- **Custom Templates**: Create domain-specific summary formats