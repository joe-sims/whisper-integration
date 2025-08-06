# Meeting Summaries

This directory contains AI-generated meeting summaries created by the pipeline.

## ⚠️ Important Security Notice

**This directory is excluded from version control** because:
- Meeting summaries contain sensitive business information
- Personal and confidential discussions should not be publicly accessible
- The `.gitignore` file prevents accidental commits of summary files

## 📁 What Goes Here

When you run the meeting pipeline, it will generate summary files with this format:
```
[meeting-name]_summary_[timestamp].txt
```

Example:
```
2025-08-06-Team-Meeting_summary_20250806_143022.txt
```

## 🔒 Privacy & Security

- **Files stay local**: Summary files are never committed to git
- **Generated fresh**: Each pipeline run creates new summaries
- **Safe to delete**: You can safely remove old summaries as needed
- **Notion backup**: Important content is also saved to your Notion database

## 🧹 Cleanup

To clean up old summaries:
```bash
# Remove summaries older than 30 days
find summaries/ -name "*.txt" -type f -mtime +30 -delete

# Remove all summaries (they'll be regenerated as needed)
rm summaries/*.txt
```

## 📝 Format

Each summary file contains:
- **Meeting metadata**: Date, participants, type
- **Structured summary**: Key points, decisions, action items
- **Full transcript**: Complete transcription for reference
- **Processing info**: Model used, generation timestamp