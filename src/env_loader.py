"""
Environment variable loader with .env file support.
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None) -> None:
    """
    Load environment variables from a .env file.
    
    Args:
        env_path: Path to .env file. If None, looks for .env in project root.
    """
    if env_path is None:
        # Look for .env file in project root
        project_root = Path(__file__).parent.parent
        env_path = project_root / '.env'
    else:
        env_path = Path(env_path)
    
    if not env_path.exists():
        return
    
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Set environment variable if not already set
                    if key not in os.environ:
                        os.environ[key] = value
                        
    except Exception as e:
        # Don't fail if .env file has issues
        print(f"Warning: Could not load .env file: {e}")


def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable with fallback to default.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


def check_required_env_vars() -> bool:
    """
    Check if all required environment variables are set.
    
    Returns:
        True if all required variables are set, False otherwise
    """
    required_vars = [
        'ANTHROPIC_API_KEY',
        'NOTION_TOKEN', 
        'NOTION_DATABASE_ID',
        'NOTION_TASK_DATABASE_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or shell environment.")
        return False
    
    return True


# Load .env file automatically when this module is imported
load_env_file()