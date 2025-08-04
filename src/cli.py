#!/usr/bin/env python3
"""
Unified CLI for Whisper audio transcription.
Combines functionality from example_usage.py and transcribe_fast.py with enhanced features.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, List

# Import the transcriber (will be updated when we move the file)
try:
    from .whisper_transcriber import WhisperTranscriber
except ImportError:
    # Fallback for when running directly before restructure
    sys.path.append(str(Path(__file__).parent.parent))
    from whisper_transcriber import WhisperTranscriber


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def find_audio_file(filename: str) -> Optional[Path]:
    """
    Find audio file in audio_input folder first, then current directory.
    
    Args:
        filename: Name of the audio file
        
    Returns:
        Path to the audio file if found, None otherwise
    """
    # Check audio_input folder first
    audio_input_path = Path('audio_input') / filename
    if audio_input_path.exists():
        return audio_input_path
    
    # Check current directory
    current_dir_path = Path(filename)
    if current_dir_path.exists():
        logging.info(f"Found '{filename}' in current directory. Consider moving to 'audio_input/' folder.")
        return current_dir_path
    
    return None


def create_output_filename(audio_path: Path, model_name: str, fast_mode: bool = False) -> Path:
    """
    Create output filename with timestamp and model info.
    
    Args:
        audio_path: Path to the original audio file
        model_name: Name of the Whisper model used
        fast_mode: Whether fast mode was used
        
    Returns:
        Path for the output transcription file
    """
    # Create transcriptions directory if it doesn't exist
    transcriptions_dir = Path('transcriptions')
    transcriptions_dir.mkdir(exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = audio_path.stem
    
    # Add fast suffix if in fast mode
    fast_suffix = "_fast" if fast_mode else ""
    
    output_file = transcriptions_dir / f"{base_name}_transcription_{timestamp}{fast_suffix}.txt"
    return output_file


def create_file_content(audio_file: str, transcriber: WhisperTranscriber, 
                       result: dict, with_timestamps: bool = True) -> List[str]:
    """
    Create the content for the transcription file.
    
    Args:
        audio_file: Original audio file path
        transcriber: WhisperTranscriber instance
        result: Transcription result from Whisper
        with_timestamps: Whether to include timestamped segments
        
    Returns:
        List of strings representing file content lines
    """
    file_content = []
    file_content.append(f"Transcription of: {audio_file}")
    file_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    file_content.append(f"Model: {transcriber.model_name}")
    file_content.append("=" * 50)
    
    language = result.get('language', 'unknown')
    file_content.append(f"Language: {language}")
    file_content.append("")
    
    file_content.append("Full Text:")
    text = result.get('text', '').strip()
    file_content.append(text)
    file_content.append("")
    
    if with_timestamps and 'segments' in result:
        file_content.append("Timestamped Segments:")
        for segment in result['segments']:
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            segment_text = segment.get('text', '').strip()
            timestamp_line = f"[{start:.2f}s - {end:.2f}s]: {segment_text}"
            file_content.append(timestamp_line)
    
    return file_content


def transcribe_single_file(filename: str, model_name: str, fast_mode: bool = False, 
                          with_timestamps: bool = True, **kwargs) -> bool:
    """
    Transcribe a single audio file.
    
    Args:
        filename: Name of the audio file
        model_name: Whisper model to use
        fast_mode: Whether to use fast mode (affects output filename)
        with_timestamps: Whether to include timestamped segments
        **kwargs: Additional arguments for transcription
        
    Returns:
        True if successful, False otherwise
    """
    # Find the audio file
    audio_path = find_audio_file(filename)
    if not audio_path:
        logging.error(f"Audio file '{filename}' not found in 'audio_input/' folder or current directory.")
        return False
    
    try:
        # Initialize transcriber
        logging.info(f"Loading Whisper model: {model_name}")
        transcriber = WhisperTranscriber(model_name=model_name)
        
        # Transcribe
        logging.info(f"Transcribing: {audio_path}")
        if with_timestamps:
            result = transcriber.transcribe_with_timestamps(str(audio_path), **kwargs)
        else:
            result = transcriber.transcribe_file(str(audio_path), **kwargs)
        
        # Create output file
        output_file = create_output_filename(audio_path, model_name, fast_mode)
        
        # Create file content
        file_content = create_file_content(str(audio_path), transcriber, result, with_timestamps)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(file_content))
        
        # Print results
        print("-" * 50)
        print("Transcribed Text:")
        print(result.get('text', '').strip())
        print()
        print("Language detected:", result.get('language', 'unknown'))
        
        if with_timestamps and 'segments' in result:
            print()
            print("Transcription with timestamps:")
            for segment in result['segments']:
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                segment_text = segment.get('text', '').strip()
                print(f"[{start:.2f}s - {end:.2f}s]: {segment_text}")
        
        print(f"\n✓ Transcription saved to: {output_file}")
        return True
        
    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        return False


def transcribe_batch(directory: str, model_name: str, **kwargs) -> None:
    """
    Transcribe all audio files in a directory.
    
    Args:
        directory: Directory containing audio files
        model_name: Whisper model to use
        **kwargs: Additional arguments for transcription
    """
    audio_dir = Path(directory)
    if not audio_dir.exists():
        logging.error(f"Directory '{directory}' not found.")
        return
    
    # Common audio file extensions
    audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.wma', '.aac'}
    
    # Find all audio files
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(audio_dir.glob(f"*{ext}"))
        audio_files.extend(audio_dir.glob(f"*{ext.upper()}"))
    
    if not audio_files:
        logging.warning(f"No audio files found in '{directory}'.")
        return
    
    logging.info(f"Found {len(audio_files)} audio files to transcribe.")
    
    successful = 0
    for audio_file in audio_files:
        logging.info(f"Processing {audio_file.name}...")
        if transcribe_single_file(audio_file.name, model_name, **kwargs):
            successful += 1
    
    print(f"\n✓ Successfully transcribed {successful}/{len(audio_files)} files.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Whisper transcription tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s audio.m4a                          # Transcribe with default base model
  %(prog)s audio.m4a --model tiny --fast      # Fast transcription with tiny model
  %(prog)s audio.m4a --model large            # High accuracy with large model
  %(prog)s --batch audio_input/               # Transcribe all files in directory
  %(prog)s audio.m4a --no-timestamps          # Text only, no timestamps
        """
    )
    
    # Input arguments
    parser.add_argument('filename', nargs='?', help='Audio file to transcribe')
    parser.add_argument('--batch', metavar='DIR', help='Transcribe all audio files in directory')
    
    # Model selection
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'], 
                       default='base', help='Whisper model to use (default: base)')
    parser.add_argument('--fast', action='store_true', 
                       help='Fast mode (equivalent to --model tiny, affects output filename)')
    
    # Output options
    parser.add_argument('--no-timestamps', action='store_true', 
                       help='Skip timestamped segments in output')
    
    # Whisper options
    parser.add_argument('--language', help='Force specific language (e.g., "en", "es", "fr")')
    parser.add_argument('--task', choices=['transcribe', 'translate'], default='transcribe',
                       help='Task to perform (default: transcribe)')
    
    # Logging
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Handle fast mode
    if args.fast:
        args.model = 'tiny'
    
    # Prepare kwargs for transcription
    transcribe_kwargs = {}
    if args.language:
        transcribe_kwargs['language'] = args.language
    if args.task:
        transcribe_kwargs['task'] = args.task
    
    # Handle batch mode
    if args.batch:
        transcribe_batch(args.batch, args.model, 
                        with_timestamps=not args.no_timestamps, **transcribe_kwargs)
        return
    
    # Handle single file
    if not args.filename:
        parser.print_help()
        return
    
    success = transcribe_single_file(
        args.filename, args.model, 
        fast_mode=args.fast,
        with_timestamps=not args.no_timestamps,
        **transcribe_kwargs
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()