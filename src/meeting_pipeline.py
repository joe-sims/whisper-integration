#!/usr/bin/env python3
"""
Meeting Pipeline: Transcribe → Summarize → Add to Notion

Complete workflow for processing meeting recordings:
1. Transcribe audio using Whisper
2. Summarize transcript using Claude API  
3. Create structured notes in Notion
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Dict, Any
import yaml

# Load environment variables from .env file
try:
    from . import env_loader
except ImportError:
    # When running directly, use absolute import
    import env_loader

# Import the transcriber
try:
    from .whisper_transcriber import WhisperTranscriber
    from .integrations.claude_summarizer import ClaudeSummarizer, MeetingType
    from .integrations.notion_client import NotionClient
except ImportError:
    # Fallback for when running directly
    sys.path.append(str(Path(__file__).parent.parent))
    from src import env_loader
    from src.whisper_transcriber import WhisperTranscriber
    from src.integrations.claude_summarizer import ClaudeSummarizer, MeetingType
    from src.integrations.notion_client import NotionClient


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config' / 'pipeline_config.yaml'
    
    if not Path(config_path).exists():
        logging.warning(f"Config file not found: {config_path}")
        return {}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def find_audio_file(filename: str) -> Optional[Path]:
    """
    Find audio file in audio_input folder first, then current directory.
    """
    # Check audio_input folder first
    audio_input_path = Path('audio_input') / filename
    if audio_input_path.exists():
        return audio_input_path
    
    # Check current directory
    current_dir_path = Path(filename)
    if current_dir_path.exists():
        return current_dir_path
    
    # Check if it's already an absolute path
    abs_path = Path(filename)
    if abs_path.exists():
        return abs_path
    
    return None


def process_meeting(
    audio_file: Path,
    config: Dict[str, Any],
    whisper_model: str = 'medium',
    meeting_type: Optional[str] = None,
    skip_transcribe: bool = False,
    skip_summarize: bool = False,
    skip_notion: bool = False,
    no_archive: bool = False
) -> Dict[str, Any]:
    """
    Process a meeting through the complete pipeline.
    
    Returns:
        Dictionary with results from each step
    """
    results = {
        'audio_file': str(audio_file),
        'timestamp': datetime.now().isoformat(),
        'transcript': None,
        'summary': None,
        'notion_page': None,
        'errors': []
    }
    
    logging.info(f"Starting meeting pipeline for: {audio_file}")
    
    # Step 1: Transcription
    if not skip_transcribe:
        try:
            logging.info("Step 1: Transcribing audio...")
            transcriber = WhisperTranscriber(model_name=whisper_model)
            
            # Get Whisper settings from config
            whisper_config = config.get('whisper', {})
            transcribe_kwargs = {}
            if whisper_config.get('language'):
                transcribe_kwargs['language'] = whisper_config['language']
            if whisper_config.get('temperature') is not None:
                transcribe_kwargs['temperature'] = whisper_config['temperature']
                
            transcript_result = transcriber.transcribe_file(str(audio_file), **transcribe_kwargs)
            results['transcript'] = transcript_result['text']
            logging.info("✓ Transcription completed")
            
            # Step 1.5: Save transcript file immediately (in case later steps fail)
            try:
                transcriptions_dir = Path('transcriptions')
                transcriptions_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                transcript_filename = transcriptions_dir / f"{audio_file.stem}_transcription_{timestamp}.txt"
                
                # Create transcript content
                transcript_content = []
                transcript_content.append(f"Transcription of: {audio_file}")
                transcript_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                transcript_content.append(f"Model: {transcriber.model_name}")
                transcript_content.append("=" * 50)
                
                language = transcript_result.get('language', 'unknown')
                transcript_content.append(f"Language: {language}")
                transcript_content.append("")
                
                transcript_content.append("Full Text:")
                transcript_content.append(transcript_result['text'].strip())
                
                # Save transcript file
                with open(transcript_filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(transcript_content))
                
                results['transcript_file'] = str(transcript_filename)
                logging.info(f"✓ Transcript saved to: {transcript_filename}")
                
            except Exception as e:
                logging.warning(f"Failed to save transcript file: {e}")
                # Don't fail the pipeline for this
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
            return results
    else:
        # Load existing transcript if skipping transcription
        # Look for any transcript file matching the audio file name
        transcriptions_dir = Path('transcriptions')
        transcript_files = list(transcriptions_dir.glob(f"{audio_file.stem}_transcription_*.txt"))
        
        if transcript_files:
            # Use the most recent transcript file
            transcript_file = max(transcript_files, key=lambda f: f.stat().st_mtime)
            results['transcript'] = transcript_file.read_text()
            logging.info(f"Using existing transcript: {transcript_file}")
        else:
            results['errors'].append(f"No existing transcript found for {audio_file.stem}")
            return results
    
    # Step 2: Summarization
    if not skip_summarize and results['transcript']:
        try:
            logging.info("Step 2: Generating summary with Claude...")
            summarizer = ClaudeSummarizer(config.get('claude', {}))
            
            # Use provided meeting type or auto-detect from transcript
            if meeting_type:
                try:
                    detected_type = MeetingType(meeting_type)
                    logging.info(f"Using specified meeting type: {detected_type.value}")
                except ValueError:
                    logging.warning(f"Invalid meeting type '{meeting_type}', auto-detecting...")
                    detected_type, confidence = summarizer.detect_meeting_type(results['transcript'])
                    logging.info(f"Auto-detected meeting type: {detected_type.value} (confidence: {confidence:.2f})")
            else:
                detected_type, confidence = summarizer.detect_meeting_type(results['transcript'])
                logging.info(f"Auto-detected meeting type: {detected_type.value} (confidence: {confidence:.2f})")
            
            summary_result = summarizer.summarize_meeting(
                transcript=results['transcript'],
                meeting_type=detected_type
            )
            results['summary'] = summary_result['summary']  # Extract just the summary text
            results['meeting_type'] = summary_result['meeting_type']
            results['summary_metadata'] = summary_result  # Store full metadata
            logging.info("✓ Summary generated")
        except Exception as e:
            error_msg = f"Summarization failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Step 2.5: Save summary to file
    if results['summary']:
        try:
            # Create summaries directory if it doesn't exist
            summaries_dir = Path('summaries')
            summaries_dir.mkdir(exist_ok=True)
            
            # Generate summary filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = summaries_dir / f"{audio_file.stem}_summary_{timestamp}.txt"
            
            # Write summary file
            summary_content = f"""Meeting Summary: {audio_file.stem}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Audio File: {audio_file}
Model: Claude ({config.get('claude', {}).get('model', 'claude-sonnet-4-20250514')})

{'-' * 50}
SUMMARY
{'-' * 50}

{results['summary']}

{'-' * 50}
FULL TRANSCRIPT  
{'-' * 50}

{results['transcript'] or 'No transcript available'}
"""
            
            summary_file.write_text(summary_content, encoding='utf-8')
            results['summary_file'] = str(summary_file)
            logging.info(f"✓ Summary saved to: {summary_file}")
            
        except Exception as e:
            error_msg = f"Failed to save summary file: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Step 3: Add to Notion
    if not skip_notion and results['summary']:
        try:
            logging.info("Step 3: Creating Notion page...")
            notion_client = NotionClient(config.get('notion', {}))
            # Generate clean meeting title
            def generate_meeting_title(filename: str) -> str:
                """Generate a clean meeting title from filename format: date-name-weekly-1-2-1"""
                # Split by dashes to get parts
                parts = filename.split('-')
                
                if len(parts) < 3:
                    # Fallback for unexpected format
                    return filename.replace('_', ' ').replace('-', ' ').title()
                
                # Skip date part (first part like "2025-08-04")
                # Find name (second part)
                person_name = parts[1].title() if len(parts) > 1 else "Unknown"
                
                # Find meeting frequency (third part like "weekly")
                frequency = parts[2].title() if len(parts) > 2 else ""
                
                # Find meeting type (remaining parts like "1-2-1")
                meeting_type_parts = parts[3:] if len(parts) > 3 else []
                meeting_type = ':'.join(meeting_type_parts) if meeting_type_parts else ""
                
                # Build title based on what we have
                if meeting_type and frequency:
                    return f"{person_name} {frequency} {meeting_type}"
                elif meeting_type:
                    return f"{person_name} {meeting_type}"
                elif frequency:
                    return f"{person_name} {frequency}"
                else:
                    return f"{person_name} Meeting"
            
            clean_title = generate_meeting_title(audio_file.stem)
            
            page_url = notion_client.create_meeting_page(
                title=clean_title,
                transcript=results['transcript'],
                summary=results['summary'],
                audio_file=str(audio_file)
            )
            results['notion_page'] = page_url
            logging.info(f"✓ Notion page created: {page_url}")
        except Exception as e:
            error_msg = f"Notion integration failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Step 4: Archive processed audio file
    if not results['errors'] and not no_archive and config.get('pipeline', {}).get('archive_processed', True):
        try:
            archive_dir = Path('archive')
            archive_dir.mkdir(exist_ok=True)
            
            # Generate archive filename with processing date
            timestamp = datetime.now().strftime('%Y%m%d')
            archive_name = f"{audio_file.stem}_processed_{timestamp}{audio_file.suffix}"
            archive_path = archive_dir / archive_name
            
            # Move file to archive (only if it's in audio_input)
            if 'audio_input' in str(audio_file):
                import shutil
                shutil.move(str(audio_file), str(archive_path))
                results['archived_file'] = str(archive_path)
                logging.info(f"✓ Audio file archived: {archive_path}")
            else:
                logging.info("Audio file not in audio_input/, skipping archive")
                
        except Exception as e:
            error_msg = f"Failed to archive audio file: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    return results


def main():
    """Main pipeline entry point."""
    parser = argparse.ArgumentParser(
        description="Meeting Pipeline: Transcribe → Summarize → Add to Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s meeting.m4a                           # Full pipeline with auto-detection
  %(prog)s meeting.m4a --model large             # Use large Whisper model
  %(prog)s meeting.m4a --meeting-type 1:1        # Force 1:1 meeting template
  %(prog)s meeting.m4a --meeting-type forecast   # Use forecast template
  %(prog)s meeting.m4a --skip-notion             # Skip Notion integration
  %(prog)s meeting.m4a --config my.yaml          # Use custom config file
        """
    )
    
    # Input arguments
    parser.add_argument('filename', help='Audio file to process')
    parser.add_argument('--config', help='Path to configuration file')
    
    # Whisper options
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'],
                       default='base', help='Whisper model to use (default: base)')
    
    # Claude options
    parser.add_argument('--meeting-type', choices=['1:1', 'team_meeting', 'forecast', 'customer', 'technical', 'strategic'],
                       help='Specify meeting type (auto-detected if not provided)')
    
    # Pipeline control
    parser.add_argument('--skip-transcribe', action='store_true', 
                       help='Skip transcription (use existing transcript)')
    parser.add_argument('--skip-summarize', action='store_true',
                       help='Skip Claude summarization')
    parser.add_argument('--skip-notion', action='store_true',
                       help='Skip Notion integration')
    parser.add_argument('--no-archive', action='store_true',
                       help='Don\'t archive processed audio files')
    
    # Logging
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Find audio file
    audio_file = find_audio_file(args.filename)
    if not audio_file:
        logging.error(f"Audio file not found: {args.filename}")
        sys.exit(1)
    
    # Process the meeting
    results = process_meeting(
        audio_file=audio_file,
        config=config,
        whisper_model=args.model,
        meeting_type=getattr(args, 'meeting_type', None),
        skip_transcribe=args.skip_transcribe,
        skip_summarize=args.skip_summarize,
        skip_notion=args.skip_notion,
        no_archive=args.no_archive
    )
    
    # Print results
    print("\n" + "="*50)
    print("MEETING PIPELINE RESULTS")
    print("="*50)
    
    if results['transcript']:
        print(f"✓ Transcript: {len(results['transcript'])} characters")
        if results.get('transcript_file'):
            print(f"✓ Transcript File: {results['transcript_file']}")
    
    if results['summary']:
        print(f"✓ Summary: Generated")
        if results.get('meeting_type'):
            print(f"✓ Meeting Type: {results['meeting_type']}")
        if results.get('summary_file'):
            print(f"✓ Summary File: {results['summary_file']}")
        print("\nSUMMARY:")
        print("-" * 30)
        print(results['summary'])
    
    if results['notion_page']:
        print(f"✓ Notion: {results['notion_page']}")
    
    if results.get('archived_file'):
        print(f"✓ Archived: {results['archived_file']}")
    
    if results['errors']:
        print(f"\n⚠ Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    # Exit with error code if there were issues
    sys.exit(1 if results['errors'] else 0)


if __name__ == "__main__":
    main()