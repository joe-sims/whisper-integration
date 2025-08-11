#!/usr/bin/env python3
"""
Archive Manager for Whisper Integration

Manages archiving of transcriptions, summaries, and processed audio files.
Organizes files by date and removes duplicates while preserving the latest versions.
"""

import os
import shutil
import datetime
from pathlib import Path
from collections import defaultdict
import argparse
import logging
from typing import Dict, List, Tuple, Optional
import re

class ArchiveManager:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.transcriptions_dir = self.base_dir / "transcriptions"
        self.summaries_dir = self.base_dir / "summaries"
        self.processed_dir = self.base_dir / "processed"  # Recently processed audio files
        self.archive_dir = self.base_dir / "archive"  # Long-term archive
        
        # Create archive directory structure
        self.archive_transcriptions = self.archive_dir / "transcriptions"
        self.archive_summaries = self.archive_dir / "summaries"
        self.archive_audio = self.archive_dir / "audio"
        
        # Ensure directories exist
        for dir_path in [self.archive_dir, self.archive_transcriptions, 
                        self.archive_summaries, self.archive_audio]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def parse_filename(self, filename: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parse filename to extract base name, timestamp, and file type.
        Returns (base_name, timestamp, file_type)
        """
        # Remove file extension
        name_without_ext = Path(filename).stem
        
        # Pattern for files with timestamps
        timestamp_patterns = [
            r'(.+)_transcription_(\d{8}_\d{6})$',  # transcription files
            r'(.+)_summary_(\d{8}_\d{6})$',       # summary files
            r'(.+)_processed_(\d{8})$',           # processed audio files
        ]
        
        for pattern in timestamp_patterns:
            match = re.match(pattern, name_without_ext)
            if match:
                base_name = match.group(1)
                timestamp = match.group(2)
                if 'transcription' in pattern:
                    file_type = 'transcription'
                elif 'summary' in pattern:
                    file_type = 'summary'
                else:
                    file_type = 'audio'
                return base_name, timestamp, file_type
        
        # No timestamp pattern found
        return name_without_ext, None, None

    def group_files_by_base_name(self, directory: Path) -> Dict[str, List[Path]]:
        """Group files by their base name (without timestamps)."""
        groups = defaultdict(list)
        
        if not directory.exists():
            return groups
        
        for file_path in directory.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                base_name, timestamp, file_type = self.parse_filename(file_path.name)
                groups[base_name].append(file_path)
        
        return groups

    def get_latest_file(self, files: List[Path]) -> Path:
        """Get the latest file based on timestamp in filename or modification time."""
        def get_sort_key(file_path):
            base_name, timestamp, file_type = self.parse_filename(file_path.name)
            if timestamp:
                # Use timestamp from filename
                return timestamp
            else:
                # Use file modification time as fallback
                return file_path.stat().st_mtime
        
        return max(files, key=get_sort_key)

    def organize_by_date(self, file_path: Path, target_dir: Path) -> Path:
        """Organize file into date-based subdirectory structure."""
        base_name, timestamp, file_type = self.parse_filename(file_path.name)
        
        if timestamp:
            # Extract date from timestamp (format: YYYYMMDD_HHMMSS or YYYYMMDD)
            date_part = timestamp.split('_')[0]
            try:
                date_obj = datetime.datetime.strptime(date_part, '%Y%m%d')
                year_month = date_obj.strftime('%Y-%m')
            except ValueError:
                year_month = 'unknown-date'
        else:
            # Use file modification date as fallback
            mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            year_month = mod_time.strftime('%Y-%m')
        
        # Create year-month directory
        date_dir = target_dir / year_month
        date_dir.mkdir(parents=True, exist_ok=True)
        
        return date_dir / file_path.name

    def archive_duplicates(self, directory: Path, archive_target: Path, dry_run: bool = False) -> int:
        """Archive duplicate files, keeping only the latest version."""
        groups = self.group_files_by_base_name(directory)
        archived_count = 0
        
        for base_name, files in groups.items():
            if len(files) <= 1:
                continue  # No duplicates
            
            # Get latest file
            latest_file = self.get_latest_file(files)
            
            # Archive older files
            for file_path in files:
                if file_path != latest_file:
                    archive_path = self.organize_by_date(file_path, archive_target)
                    
                    if dry_run:
                        self.logger.info(f"[DRY RUN] Would move {file_path} -> {archive_path}")
                    else:
                        archive_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file_path), str(archive_path))
                        self.logger.info(f"Archived {file_path.name} -> {archive_path}")
                    
                    archived_count += 1
        
        return archived_count

    def archive_old_files(self, directory: Path, archive_target: Path, 
                         days_old: int = 30, dry_run: bool = False) -> int:
        """Archive files older than specified days."""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        archived_count = 0
        
        if not directory.exists():
            return 0
        
        for file_path in directory.iterdir():
            if not file_path.is_file() or file_path.name.startswith('.'):
                continue
            
            # Check if file is old enough
            mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            if mod_time < cutoff_date:
                archive_path = self.organize_by_date(file_path, archive_target)
                
                if dry_run:
                    self.logger.info(f"[DRY RUN] Would move old file {file_path} -> {archive_path}")
                else:
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(archive_path))
                    self.logger.info(f"Archived old file {file_path.name} -> {archive_path}")
                
                archived_count += 1
        
        return archived_count

    def clean_empty_directories(self, directory: Path, dry_run: bool = False) -> int:
        """Remove empty directories."""
        removed_count = 0
        
        if not directory.exists():
            return 0
        
        for item in directory.iterdir():
            if item.is_dir():
                # Recursively clean subdirectories first
                removed_count += self.clean_empty_directories(item, dry_run)
                
                # Remove if empty
                if not any(item.iterdir()):
                    if dry_run:
                        self.logger.info(f"[DRY RUN] Would remove empty directory {item}")
                    else:
                        item.rmdir()
                        self.logger.info(f"Removed empty directory {item}")
                    removed_count += 1
        
        return removed_count

    def archive_all(self, remove_duplicates: bool = True, archive_old: bool = False, 
                   days_old: int = 30, archive_processed_audio: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """Perform complete archiving process."""
        results = {
            'transcriptions_duplicates': 0,
            'summaries_duplicates': 0,
            'transcriptions_old': 0,
            'summaries_old': 0,
            'processed_audio_archived': 0,
            'empty_dirs': 0
        }
        
        self.logger.info(f"Starting archive process (dry_run={dry_run})")
        
        if remove_duplicates:
            # Archive duplicate transcriptions
            results['transcriptions_duplicates'] = self.archive_duplicates(
                self.transcriptions_dir, self.archive_transcriptions, dry_run
            )
            
            # Archive duplicate summaries  
            results['summaries_duplicates'] = self.archive_duplicates(
                self.summaries_dir, self.archive_summaries, dry_run
            )
        
        if archive_old:
            # Archive old files
            results['transcriptions_old'] = self.archive_old_files(
                self.transcriptions_dir, self.archive_transcriptions, days_old, dry_run
            )
            results['summaries_old'] = self.archive_old_files(
                self.summaries_dir, self.archive_summaries, days_old, dry_run
            )
        
        if archive_processed_audio:
            # Archive processed audio files
            results['processed_audio_archived'] = self.archive_old_files(
                self.processed_dir, self.archive_audio, days_old, dry_run
            )
        
        # Clean empty directories
        results['empty_dirs'] = self.clean_empty_directories(self.archive_dir, dry_run)
        
        return results

    def list_duplicates(self) -> Dict[str, Dict[str, List[str]]]:
        """List all duplicate files without archiving them."""
        duplicates = {}
        
        # Check transcriptions
        transcription_groups = self.group_files_by_base_name(self.transcriptions_dir)
        transcription_dupes = {name: [f.name for f in files] 
                             for name, files in transcription_groups.items() 
                             if len(files) > 1}
        if transcription_dupes:
            duplicates['transcriptions'] = transcription_dupes
        
        # Check summaries
        summary_groups = self.group_files_by_base_name(self.summaries_dir)
        summary_dupes = {name: [f.name for f in files] 
                        for name, files in summary_groups.items() 
                        if len(files) > 1}
        if summary_dupes:
            duplicates['summaries'] = summary_dupes
        
        return duplicates

    def print_statistics(self):
        """Print current statistics about files."""
        stats = {
            'transcriptions': len(list(self.transcriptions_dir.glob('*'))) if self.transcriptions_dir.exists() else 0,
            'summaries': len(list(self.summaries_dir.glob('*'))) if self.summaries_dir.exists() else 0,
            'processed_audio': len(list(self.processed_dir.glob('*'))) if self.processed_dir.exists() else 0,
            'archived_transcriptions': len(list(self.archive_transcriptions.rglob('*'))) if self.archive_transcriptions.exists() else 0,
            'archived_summaries': len(list(self.archive_summaries.rglob('*'))) if self.archive_summaries.exists() else 0,
            'archived_audio': len(list(self.archive_audio.rglob('*'))) if self.archive_audio.exists() else 0,
        }
        
        print(f"\n📊 File Statistics:")
        print(f"   Active transcriptions: {stats['transcriptions']}")
        print(f"   Active summaries: {stats['summaries']}")
        print(f"   Processed audio files: {stats['processed_audio']}")
        print(f"   Archived transcriptions: {stats['archived_transcriptions']}")
        print(f"   Archived summaries: {stats['archived_summaries']}")
        print(f"   Archived audio files: {stats['archived_audio']}")


def main():
    parser = argparse.ArgumentParser(description='Archive Manager for Whisper Integration')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--duplicates-only', action='store_true',
                       help='Only remove duplicates, don\'t archive old files')
    parser.add_argument('--archive-old', action='store_true',
                       help='Archive files older than specified days')
    parser.add_argument('--archive-audio', action='store_true',
                       help='Archive processed audio files older than specified days')
    parser.add_argument('--days-old', type=int, default=30,
                       help='Days old threshold for archiving (default: 30)')
    parser.add_argument('--list-duplicates', action='store_true',
                       help='List duplicate files without archiving')
    parser.add_argument('--stats', action='store_true',
                       help='Show file statistics')
    
    args = parser.parse_args()
    
    archive_manager = ArchiveManager()
    
    if args.stats:
        archive_manager.print_statistics()
        return
    
    if args.list_duplicates:
        duplicates = archive_manager.list_duplicates()
        if duplicates:
            print("\n🔍 Duplicate Files Found:")
            for category, dupes in duplicates.items():
                print(f"\n{category.upper()}:")
                for base_name, files in dupes.items():
                    print(f"  {base_name}:")
                    for file in files:
                        print(f"    - {file}")
        else:
            print("\n✅ No duplicate files found!")
        return
    
    # Run archive process
    remove_duplicates = True
    archive_old = args.archive_old or not args.duplicates_only
    
    if args.duplicates_only:
        archive_old = False
    
    results = archive_manager.archive_all(
        remove_duplicates=remove_duplicates,
        archive_old=archive_old, 
        days_old=args.days_old,
        archive_processed_audio=args.archive_audio,
        dry_run=args.dry_run
    )
    
    # Print results
    print(f"\n📋 Archive Results:")
    print(f"   Duplicate transcriptions archived: {results['transcriptions_duplicates']}")
    print(f"   Duplicate summaries archived: {results['summaries_duplicates']}")
    if archive_old:
        print(f"   Old transcriptions archived: {results['transcriptions_old']}")
        print(f"   Old summaries archived: {results['summaries_old']}")
    if args.archive_audio:
        print(f"   Processed audio archived: {results['processed_audio_archived']}")
    print(f"   Empty directories removed: {results['empty_dirs']}")
    
    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to perform actual archiving.")
    else:
        print("\n✅ Archive process completed!")
    
    archive_manager.print_statistics()


if __name__ == '__main__':
    main()