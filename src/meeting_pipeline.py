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
from typing import Optional, Dict, Any, List
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
                    detected_type, confidence = summarizer.detect_meeting_type(results['transcript'], filename=audio_file.name)
                    logging.info(f"Auto-detected meeting type: {detected_type.value} (confidence: {confidence:.2f})")
            else:
                detected_type, confidence = summarizer.detect_meeting_type(results['transcript'], filename=audio_file.name)
                logging.info(f"Auto-detected meeting type: {detected_type.value} (confidence: {confidence:.2f})")
            
            summary_result = summarizer.summarize_meeting(
                transcript=results['transcript'],
                meeting_type=detected_type,
                filename=audio_file.name
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
                """Generate a clean meeting title from filename format: 2025-08-06-Name-Weekly-1-1"""
                # Split by dashes to get parts
                parts = filename.split('-')
                
                if len(parts) < 4:
                    # Fallback for unexpected format
                    return filename.replace('_', ' ').replace('-', ' ').title()
                
                # Skip date parts (2025-08-06 = first 3 parts)
                # Get name (4th part, index 3) - keep EMEA uppercase
                person_name = parts[3] if len(parts) > 3 else "Unknown"
                if person_name.upper() == "EMEA":
                    person_name = "EMEA"
                else:
                    person_name = person_name.title()
                
                # Find meeting frequency (5th part, index 4)
                frequency = parts[4].title() if len(parts) > 4 else ""
                
                # Find meeting type (remaining parts like "1-1" → "1:1")
                meeting_type_parts = parts[5:] if len(parts) > 5 else []
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
            processed_dir = Path('processed')
            processed_dir.mkdir(exist_ok=True)
            
            # Generate processed filename with processing date
            timestamp = datetime.now().strftime('%Y%m%d')
            processed_name = f"{audio_file.stem}_processed_{timestamp}{audio_file.suffix}"
            processed_path = processed_dir / processed_name
            
            # Move file to processed (only if it's in audio_input)
            if 'audio_input' in str(audio_file):
                import shutil
                shutil.move(str(audio_file), str(processed_path))
                results['processed_file'] = str(processed_path)
                logging.info(f"✓ Audio file moved to processed: {processed_path}")
            else:
                logging.info("Audio file not in audio_input/, skipping move to processed")
                
        except Exception as e:
            error_msg = f"Failed to move audio file to processed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    return results


def process_combined_meeting(
    audio_files: List[Path],
    config: Dict[str, Any],
    whisper_model: str = 'medium',
    meeting_type: Optional[str] = None,
    combined_title: Optional[str] = None,
    skip_transcribe: bool = False,
    skip_summarize: bool = False,
    skip_notion: bool = False,
    no_archive: bool = False
) -> Dict[str, Any]:
    """
    Process multiple meeting audio files into a single combined summary.
    
    Args:
        audio_files: List of audio file paths to process
        config: Configuration dictionary
        whisper_model: Whisper model to use for transcription
        meeting_type: Meeting type for summary formatting
        combined_title: Title for the combined meeting
        skip_transcribe: Skip transcription step
        skip_summarize: Skip summarization step
        skip_notion: Skip Notion integration
        no_archive: Don't archive processed files
        
    Returns:
        Dictionary with combined results
    """
    results = {
        'audio_files': [str(f) for f in audio_files],
        'timestamp': datetime.now().isoformat(),
        'combined_transcript': None,
        'individual_transcripts': [],
        'summary': None,
        'notion_page': None,
        'errors': []
    }
    
    logging.info(f"Starting combined meeting pipeline for {len(audio_files)} files")
    
    # Step 1: Transcribe all audio files
    combined_transcript_parts = []
    
    for i, audio_file in enumerate(audio_files, 1):
        if not skip_transcribe:
            try:
                logging.info(f"Step 1.{i}: Transcribing {audio_file.name}...")
                transcriber = WhisperTranscriber(model_name=whisper_model)
                
                # Get Whisper settings from config
                whisper_config = config.get('whisper', {})
                transcribe_kwargs = {}
                if whisper_config.get('language'):
                    transcribe_kwargs['language'] = whisper_config['language']
                if whisper_config.get('temperature') is not None:
                    transcribe_kwargs['temperature'] = whisper_config['temperature']
                    
                transcript_result = transcriber.transcribe_file(str(audio_file), **transcribe_kwargs)
                transcript_text = transcript_result['text']
                
                # Store individual transcript
                results['individual_transcripts'].append({
                    'file': str(audio_file),
                    'transcript': transcript_text,
                    'language': transcript_result.get('language', 'unknown')
                })
                
                # Add to combined transcript with file separator
                file_header = f"\n{'='*60}\nFILE: {audio_file.name}\n{'='*60}\n"
                combined_transcript_parts.append(file_header + transcript_text)
                
                logging.info(f"✓ Transcription {i}/{len(audio_files)} completed")
                
            except Exception as e:
                error_msg = f"Transcription failed for {audio_file}: {str(e)}"
                logging.error(error_msg)
                results['errors'].append(error_msg)
                continue
        else:
            # Load existing transcript if skipping transcription
            transcriptions_dir = Path('transcriptions')
            transcript_files = list(transcriptions_dir.glob(f"{audio_file.stem}_transcription_*.txt"))
            
            if transcript_files:
                # Use the most recent transcript file
                transcript_file = max(transcript_files, key=lambda f: f.stat().st_mtime)
                transcript_text = transcript_file.read_text()
                
                results['individual_transcripts'].append({
                    'file': str(audio_file),
                    'transcript': transcript_text
                })
                
                file_header = f"\n{'='*60}\nFILE: {audio_file.name}\n{'='*60}\n"
                combined_transcript_parts.append(file_header + transcript_text)
                
                logging.info(f"Using existing transcript: {transcript_file}")
            else:
                error_msg = f"No existing transcript found for {audio_file.stem}"
                results['errors'].append(error_msg)
                continue
    
    # Combine all transcripts
    if combined_transcript_parts:
        results['combined_transcript'] = '\n'.join(combined_transcript_parts)
        
        # Save combined transcript file
        try:
            transcriptions_dir = Path('transcriptions')
            transcriptions_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            combined_filename = f"combined_meeting_transcription_{timestamp}.txt"
            transcript_file = transcriptions_dir / combined_filename
            
            # Create transcript content
            transcript_content = []
            transcript_content.append(f"Combined Transcription of: {len(audio_files)} files")
            transcript_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            transcript_content.append(f"Model: {whisper_model}")
            transcript_content.append(f"Files: {', '.join([f.name for f in audio_files])}")
            transcript_content.append("=" * 50)
            transcript_content.append("")
            transcript_content.append(results['combined_transcript'])
            
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(transcript_content))
            
            results['transcript_file'] = str(transcript_file)
            logging.info(f"✓ Combined transcript saved to: {transcript_file}")
            
        except Exception as e:
            logging.warning(f"Failed to save combined transcript file: {e}")
    
    # Step 2: Generate single summary from combined transcript
    if not skip_summarize and results['combined_transcript']:
        try:
            logging.info("Step 2: Generating combined summary with Claude...")
            summarizer = ClaudeSummarizer(config.get('claude', {}))
            
            # Use provided meeting type or auto-detect from combined transcript
            if meeting_type:
                try:
                    detected_type = MeetingType(meeting_type)
                    logging.info(f"Using specified meeting type: {detected_type.value}")
                except ValueError:
                    logging.warning(f"Invalid meeting type '{meeting_type}', auto-detecting...")
                    detected_type, confidence = summarizer.detect_meeting_type(results['combined_transcript'], filename=audio_files[0].name)
                    logging.info(f"Auto-detected meeting type: {detected_type.value} (confidence: {confidence:.2f})")
            else:
                detected_type, confidence = summarizer.detect_meeting_type(results['combined_transcript'], filename=audio_files[0].name)
                logging.info(f"Auto-detected meeting type: {detected_type.value} (confidence: {confidence:.2f})")
            
            # Add context about this being a combined meeting
            combined_context = f"This is a combined summary of {len(audio_files)} related meeting recordings: {', '.join([f.name for f in audio_files])}"
            enhanced_transcript = f"{combined_context}\n\n{results['combined_transcript']}"
            
            summary_result = summarizer.summarize_meeting(
                transcript=enhanced_transcript,
                meeting_type=detected_type,
                filename=audio_files[0].name
            )
            results['summary'] = summary_result['summary']
            results['meeting_type'] = summary_result['meeting_type']
            results['summary_metadata'] = summary_result
            logging.info("✓ Combined summary generated")
        except Exception as e:
            error_msg = f"Summarization failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Step 2.5: Save combined summary to file
    if results['summary']:
        try:
            summaries_dir = Path('summaries')
            summaries_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = summaries_dir / f"combined_meeting_summary_{timestamp}.txt"
            
            file_list = '\n'.join([f"  - {f.name}" for f in audio_files])
            summary_content = f"""Combined Meeting Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Audio Files ({len(audio_files)} total):
{file_list}
Model: Claude ({config.get('claude', {}).get('model', 'claude-sonnet-4-20250514')})
Meeting Type: {results.get('meeting_type', 'auto-detected')}

{'-' * 50}
COMBINED SUMMARY
{'-' * 50}

{results['summary']}

{'-' * 50}
COMBINED TRANSCRIPT  
{'-' * 50}

{results['combined_transcript'] or 'No transcript available'}
"""
            
            summary_file.write_text(summary_content, encoding='utf-8')
            results['summary_file'] = str(summary_file)
            logging.info(f"✓ Combined summary saved to: {summary_file}")
            
        except Exception as e:
            error_msg = f"Failed to save combined summary file: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Step 3: Add to Notion (using combined title)
    if not skip_notion and results['summary']:
        try:
            logging.info("Step 3: Creating Notion page for combined meeting...")
            notion_client = NotionClient(config.get('notion', {}))
            
            # Use provided title or generate one
            if combined_title:
                clean_title = combined_title
            else:
                # Generate title from file names
                if len(audio_files) == 2:
                    clean_title = f"Combined Meeting: {audio_files[0].stem} + {audio_files[1].stem}"
                else:
                    clean_title = f"Combined Meeting: {len(audio_files)} recordings"
            
            page_url = notion_client.create_meeting_page(
                title=clean_title,
                transcript=results['combined_transcript'],
                summary=results['summary'],
                audio_file=f"Combined: {', '.join([f.name for f in audio_files])}"
            )
            results['notion_page'] = page_url
            logging.info(f"✓ Notion page created: {page_url}")
        except Exception as e:
            error_msg = f"Notion integration failed: {str(e)}"
            logging.error(error_msg)
            results['errors'].append(error_msg)
    
    # Step 4: Archive processed audio files (optional)
    if not results['errors'] and not no_archive and config.get('pipeline', {}).get('archive_processed', True):
        for audio_file in audio_files:
            try:
                processed_dir = Path('processed')
                processed_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d')
                processed_name = f"{audio_file.stem}_processed_{timestamp}{audio_file.suffix}"
                processed_path = processed_dir / processed_name
                
                # Move file to processed (only if it's in audio_input)
                if 'audio_input' in str(audio_file):
                    import shutil
                    shutil.move(str(audio_file), str(processed_path))
                    logging.info(f"✓ Audio file moved to processed: {processed_path}")
                    
            except Exception as e:
                error_msg = f"Failed to move audio file {audio_file} to processed: {str(e)}"
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
  %(prog)s part1.m4a --combine part2.m4a part3.m4a  # Combine 3 files into single summary
  %(prog)s file1.m4a --combine file2.m4a --combine-title "Weekly Review"  # Combined with custom title
        """
    )
    
    # Input arguments
    parser.add_argument('filename', nargs='?', help='Audio file to process (or first file for --combine)')
    parser.add_argument('--combine', nargs='+', metavar='FILE', help='Combine multiple files into single summary (provide additional files)')
    parser.add_argument('--combine-title', help='Title for combined meeting summary')
    parser.add_argument('--config', help='Path to configuration file')
    
    # Whisper options
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model to use (default: from config)')
    
    # Claude options
    parser.add_argument('--meeting-type', choices=['1:1', 'team_meeting', 'forecast', 'customer', 'technical', 'strategic', 'deal_review'],
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
    
    # Handle combine mode
    if args.combine:
        if not args.filename:
            logging.error("Must provide primary filename when using --combine")
            sys.exit(1)
            
        # Collect all files for combination
        all_filenames = [args.filename] + args.combine
        audio_files = []
        
        for filename in all_filenames:
            audio_file = find_audio_file(filename)
            if not audio_file:
                logging.error(f"Audio file not found: {filename}")
                sys.exit(1)
            audio_files.append(audio_file)
        
        logging.info(f"Combining {len(audio_files)} audio files into single summary")
        
        # Get Whisper model from CLI args or config
        whisper_model = args.model or config.get('whisper', {}).get('default_model', 'medium')
        
        # Process combined meeting
        results = process_combined_meeting(
            audio_files=audio_files,
            config=config,
            whisper_model=whisper_model,
            meeting_type=getattr(args, 'meeting_type', None),
            combined_title=args.combine_title,
            skip_transcribe=args.skip_transcribe,
            skip_summarize=args.skip_summarize,
            skip_notion=args.skip_notion,
            no_archive=args.no_archive
        )
    else:
        # Single file processing (existing behavior)
        if not args.filename:
            logging.error("Must provide filename (or use --combine for multiple files)")
            sys.exit(1)
            
        # Find audio file
        audio_file = find_audio_file(args.filename)
        if not audio_file:
            logging.error(f"Audio file not found: {args.filename}")
            sys.exit(1)
        
        # Get Whisper model from CLI args or config
        whisper_model = args.model or config.get('whisper', {}).get('default_model', 'medium')
        
        # Process the meeting
        results = process_meeting(
            audio_file=audio_file,
            config=config,
            whisper_model=whisper_model,
            meeting_type=getattr(args, 'meeting_type', None),
            skip_transcribe=args.skip_transcribe,
            skip_summarize=args.skip_summarize,
            skip_notion=args.skip_notion,
            no_archive=args.no_archive
        )
    
    # Print results
    print("\n" + "="*50)
    if args.combine:
        print("COMBINED MEETING PIPELINE RESULTS")
        print("="*50)
        print(f"✓ Combined Files: {len(results['audio_files'])}")
        for i, audio_file in enumerate(results['audio_files'], 1):
            print(f"  {i}. {Path(audio_file).name}")
    else:
        print("MEETING PIPELINE RESULTS")
        print("="*50)
    
    # Handle transcript results (single or combined)
    if args.combine:
        if results.get('combined_transcript'):
            print(f"✓ Combined Transcript: {len(results['combined_transcript'])} characters")
            if results.get('transcript_file'):
                print(f"✓ Combined Transcript File: {results['transcript_file']}")
        
        if results.get('individual_transcripts'):
            print(f"✓ Individual Transcripts: {len(results['individual_transcripts'])} files")
    else:
        if results.get('transcript'):
            print(f"✓ Transcript: {len(results['transcript'])} characters")
            if results.get('transcript_file'):
                print(f"✓ Transcript File: {results['transcript_file']}")
    
    if results.get('summary'):
        print(f"✓ Summary: Generated")
        if results.get('meeting_type'):
            print(f"✓ Meeting Type: {results['meeting_type']}")
        if results.get('summary_file'):
            print(f"✓ Summary File: {results['summary_file']}")
        print("\nSUMMARY:")
        print("-" * 30)
        print(results['summary'])
    
    if results.get('notion_page'):
        print(f"✓ Notion: {results['notion_page']}")
    
    if results.get('processed_file'):
        print(f"✓ Processed: {results['processed_file']}")
    
    if results.get('errors'):
        print(f"\n⚠ Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    # Exit with error code if there were issues
    sys.exit(1 if results['errors'] else 0)


if __name__ == "__main__":
    main()