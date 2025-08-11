#!/usr/bin/env python3
"""
Standalone archive script for whisper-integration project.
This is a convenience wrapper around the archive functionality.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from archive_manager import main

if __name__ == "__main__":
    main()