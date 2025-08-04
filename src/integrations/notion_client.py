"""
Notion API integration for creating meeting notes.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

try:
    from notion_client import Client
except ImportError:
    Client = None


class NotionClient:
    """Handles creating and managing meeting notes in Notion."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Notion client.
        
        Args:
            config: Configuration dictionary containing Notion settings
        """
        if Client is None:
            raise ImportError(
                "notion-client package not installed. Run: pip install notion-client"
            )
        
        # Get API token from config or environment
        token = config.get('token') or os.getenv('NOTION_TOKEN')
        if not token:
            raise ValueError(
                "Notion token not found. Set NOTION_TOKEN environment variable "
                "or add it to your config file."
            )
        
        self.client = Client(auth=token)
        self.database_id = config.get('database_id') or os.getenv('NOTION_DATABASE_ID')
        self.page_template = config.get('page_template', 'meeting')
        
        # Page templates
        self.templates = {
            'meeting': self._get_meeting_template(),
            'simple': self._get_simple_template(),
            'detailed': self._get_detailed_template()
        }
        
    def _get_meeting_template(self) -> Dict[str, Any]:
        """Standard meeting page template."""
        return {
            'properties': {
                'Name': 'title',
                'Date': 'date', 
                'Type': 'select',
                'Status': 'select',
                'Partipants': 'multi_select'  # Note: matches your DB spelling
            },
            'default_values': {
                'Type': 'Meeting',
                'Status': 'Processed'
            }
        }
    
    def _get_simple_template(self) -> Dict[str, Any]:
        """Simple page template."""
        return {
            'properties': {
                'Title': 'title',
                'Date': 'date',
                'Audio File': 'url'
            },
            'default_values': {}
        }
    
    def _get_detailed_template(self) -> Dict[str, Any]:
        """Detailed meeting page template."""
        return {
            'properties': {
                'Title': 'title',
                'Date': 'date',
                'Type': 'select', 
                'Status': 'select',
                'Participants': 'multi_select',
                'Duration': 'number',
                'Audio File': 'url',
                'Model Used': 'select',
                'Summary Rating': 'select'
            },
            'default_values': {
                'Type': 'Meeting',
                'Status': 'Processed',
                'Summary Rating': 'Good'
            }
        }
    
    def create_meeting_page(
        self,
        title: str,
        transcript: str,
        summary: str,
        audio_file: str,
        participants: Optional[List[str]] = None,
        template_type: Optional[str] = None,
        custom_properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new meeting page in Notion.
        
        Args:
            title: Page title
            transcript: Full transcript text
            summary: Meeting summary
            audio_file: Path to audio file
            participants: List of participant names
            template_type: Template to use ('meeting', 'simple', 'detailed')
            custom_properties: Additional properties to set
            
        Returns:
            URL of the created page
        """
        # Get template
        template = template_type or self.page_template
        page_config = self.templates.get(template, self.templates['meeting'])
        
        # Build page properties
        properties = self._build_properties(
            title=title,
            audio_file=audio_file,
            participants=participants or [],
            template_config=page_config,
            custom_properties=custom_properties or {}
        )
        
        # Build page content
        children = self._build_page_content(transcript, summary)
        
        try:
            if self.database_id:
                # Create page in database
                page = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties,
                    children=children
                )
            else:
                # Create standalone page (requires parent page ID)
                raise ValueError(
                    "No database_id configured. Set NOTION_DATABASE_ID or add to config."
                )
            
            page_url = page['url']
            logging.info(f"Created Notion page: {page_url}")
            return page_url
            
        except Exception as e:
            logging.error(f"Failed to create Notion page: {str(e)}")
            raise
    
    def _build_properties(
        self,
        title: str,
        audio_file: str,
        participants: List[str],
        template_config: Dict[str, Any],
        custom_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build page properties based on template."""
        properties = {}
        
        # Title (required) - Use 'Name' property which is standard in Notion databases
        properties['Name'] = {
            "title": [{"text": {"content": title}}]
        }
        
        # Date
        if 'Date' in template_config['properties']:
            properties['Date'] = {
                "date": {"start": datetime.now().isoformat()}
            }
        
        # Audio File URL
        if 'Audio File' in template_config['properties']:
            properties['Audio File'] = {
                "url": f"file://{audio_file}"
            }
        
        # Participants (note the spelling in your database)
        if 'Partipants' in template_config['properties'] and participants:
            properties['Partipants'] = {
                "multi_select": [{"name": name} for name in participants[:10]]  # Limit to 10
            }
        
        # Apply default values from template
        for prop, value in template_config.get('default_values', {}).items():
            if prop in template_config['properties']:
                prop_type = template_config['properties'][prop]
                if prop_type == 'select':
                    properties[prop] = {"select": {"name": value}}
                elif prop_type == 'number':
                    properties[prop] = {"number": value}
                elif prop_type == 'checkbox':
                    properties[prop] = {"checkbox": value}
        
        # Add custom properties
        properties.update(custom_properties)
        
        return properties
    
    def _build_page_content(self, transcript: str, summary: str) -> List[Dict[str, Any]]:
        """Build page content blocks."""
        children = []
        
        # Parse summary as markdown and convert to Notion blocks
        if summary:
            # Split summary into lines and process markdown
            summary_lines = summary.split('\n')
            current_section = []
            
            for line in summary_lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Handle markdown headers
                if line.startswith('## '):
                    # Flush current section
                    if current_section:
                        children.append({
                            "paragraph": {
                                "rich_text": [{"text": {"content": '\n'.join(current_section)}}]
                            }
                        })
                        current_section = []
                    
                    # Add header
                    children.append({
                        "heading_2": {
                            "rich_text": [{"text": {"content": line[3:]}}]  # Remove "## "
                        }
                    })
                elif line.startswith('- '):
                    # Add bullet point
                    children.append({
                        "bulleted_list_item": {
                            "rich_text": [{"text": {"content": line[2:]}}]  # Remove "- "
                        }
                    })
                else:
                    # Regular paragraph text
                    current_section.append(line)
            
            # Flush any remaining content
            if current_section:
                children.append({
                    "paragraph": {
                        "rich_text": [{"text": {"content": '\n'.join(current_section)}}]
                    }
                })
        
        # Metadata section (no transcript)
        children.extend([
            {
                "divider": {}
            },
            {
                "paragraph": {
                    "rich_text": [
                        {"text": {"content": f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "}},
                        {"text": {"content": "Whisper + Claude + Notion Pipeline"}}
                    ]
                }
            }
        ])
        
        return children
    
    def test_connection(self) -> bool:
        """Test connection to Notion API."""
        try:
            # Try to get user info
            user = self.client.users.me()
            logging.info(f"Connected to Notion as: {user.get('name', 'Unknown')}")
            
            # Test database access if configured
            if self.database_id:
                db = self.client.databases.retrieve(self.database_id)
                logging.info(f"Database access confirmed: {db.get('title', [{}])[0].get('plain_text', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logging.error(f"Notion connection test failed: {str(e)}")
            return False
    
    def get_available_templates(self) -> Dict[str, str]:
        """Return available page templates."""
        return {
            name: f"Template with properties: {', '.join(config['properties'].keys())}"
            for name, config in self.templates.items()
        }