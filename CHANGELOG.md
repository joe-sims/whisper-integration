# Changelog

All notable changes to the Whisper Integration project will be documented in this file.

## [2.0.0] - 2025-08-06

### 🚀 Major Features Added
- **Role-based Claude prompts**: Six specialized meeting types (1:1, forecast, customer, technical, strategic, team)
- **Auto meeting type detection**: Intelligent categorization from transcript content
- **Direct task linking**: Notion tasks link back to source meeting pages via relations
- **Enhanced security**: Environment variables replace hardcoded API keys
- **Professional templates**: Manager-focused summaries with business context

### 🔧 Technical Improvements
- **Updated Claude model**: claude-3-5-sonnet-20241022 with 2000 token limit
- **Environment variable loader**: Automatic .env file support with fallback
- **Improved error handling**: Better logging and validation throughout
- **CLI enhancements**: `--meeting-type` flag to override auto-detection
- **User personalization**: Configurable role, region, company context

### 🛡️ Security Enhancements
- **Removed hardcoded secrets**: All API keys moved to environment variables
- **Secure credential management**: .env file support with proper .gitignore
- **Clean configuration**: Example configs without sensitive data

### 🎯 User Experience
- **Cleaner task creation**: Removed auto-populated descriptions
- **Better action item extraction**: Improved pattern matching for tasks/owners
- **Professional formatting**: Proper Notion markdown with consistent headers
- **Enhanced CLI help**: Updated examples and usage instructions

### 🐛 Bug Fixes
- **Fixed markdown formatting**: Consistent `##` headers across all templates
- **Improved task database**: Better property mapping and relation handling
- **Enhanced error messages**: More specific logging for troubleshooting

## [1.0.0] - 2025-08-04

### Initial Release
- **Core transcription**: Whisper integration with multiple model sizes
- **Claude summarization**: Basic meeting summarization with templates  
- **Notion integration**: Automatic page creation with structured content
- **Pipeline orchestration**: End-to-end audio → transcript → summary → Notion
- **CLI interface**: Flexible command-line tool with multiple options
- **File management**: Organized input/output with automatic archiving

### Features
- Multiple Whisper models (tiny, base, small, medium, large)
- Template-based summaries (default, business, technical, personal)
- Notion page templates (meeting, simple, detailed) 
- Batch processing support
- Configurable pipeline steps
- Audio format support (WAV, MP3, M4A, FLAC)

---

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):
- **Major** version for incompatible API changes
- **Minor** version for backwards-compatible functionality additions  
- **Patch** version for backwards-compatible bug fixes