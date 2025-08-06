"""
Notion API integration for creating meeting notes.
"""

import os
import re
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
        self.task_database_id = config.get('task_database_id') or os.getenv('NOTION_TASK_DATABASE_ID')
        self.create_tasks = config.get('create_tasks', True)
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
            page_id = page['id']
            logging.info(f"Created Notion page: {page_url}")
            
            # Extract and create tasks from summary
            if summary and self.create_tasks and self.task_database_id:
                try:
                    task_urls = self.create_tasks_from_summary(summary, page_id, title)
                    if task_urls:
                        logging.info(f"Created {len(task_urls)} tasks linked to meeting page")
                except Exception as e:
                    logging.error(f"Failed to create tasks from summary: {str(e)}")
            
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
                elif line.startswith('- [ ] '):
                    # Add to-do item (checkbox) with bold formatting support
                    todo_text = line[6:]  # Remove "- [ ] "
                    if '**' in todo_text:
                        rich_text = self._parse_bold_text(todo_text)
                    else:
                        rich_text = [{"text": {"content": todo_text}}]
                    
                    children.append({
                        "to_do": {
                            "rich_text": rich_text,
                            "checked": False
                        }
                    })
                elif line.startswith('- [x] '):
                    # Add completed to-do item with bold formatting support  
                    todo_text = line[6:]  # Remove "- [x] "
                    if '**' in todo_text:
                        rich_text = self._parse_bold_text(todo_text)
                    else:
                        rich_text = [{"text": {"content": todo_text}}]
                    
                    children.append({
                        "to_do": {
                            "rich_text": rich_text,
                            "checked": True
                        }
                    })
                elif line.startswith('- '):
                    # Flush any pending content first
                    if current_section:
                        children.append({
                            "paragraph": {
                                "rich_text": [{"text": {"content": '\n'.join(current_section)}}]
                            }
                        })
                        current_section = []
                    
                    # Add regular bullet point (check for bold formatting)
                    bullet_text = line[2:]  # Remove "- "
                    
                    # Handle text that's too long by truncating properly
                    if len(bullet_text) > 2000:
                        bullet_text = bullet_text[:1997] + "..."
                    
                    if '**' in bullet_text:
                        rich_text = self._parse_bold_text(bullet_text)
                    else:
                        rich_text = [{"text": {"content": bullet_text}}]
                    
                    children.append({
                        "bulleted_list_item": {
                            "rich_text": rich_text
                        }
                    })
                else:
                    # Handle bold text formatting **text** -> bold
                    if '**' in line:
                        # Parse bold text within the line
                        rich_text = self._parse_bold_text(line)
                        children.append({
                            "paragraph": {
                                "rich_text": rich_text
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
    
    def _parse_bold_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse text with **bold** formatting into Notion rich text."""
        rich_text = []
        parts = text.split('**')
        
        for i, part in enumerate(parts):
            if not part:  # Skip empty parts
                continue
            
            # Truncate individual parts if too long
            if len(part) > 2000:
                part = part[:1997] + "..."
                
            if i % 2 == 1:  # Odd indices are bold text
                rich_text.append({
                    "text": {"content": part},
                    "annotations": {"bold": True}
                })
            else:  # Even indices are regular text
                rich_text.append({
                    "text": {"content": part}
                })
        
        # If we have no rich text, return a fallback
        if not rich_text:
            rich_text = [{"text": {"content": text[:2000]}}]
        
        return rich_text
    
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
    
    def extract_action_items(self, summary: str) -> List[Dict[str, Any]]:
        """
        Extract action items from summary text.
        
        Args:
            summary: The meeting summary text containing action items
            
        Returns:
            List of action item dictionaries with task, owner, due_date, priority
        """
        action_items = []
        
        # Look for action item patterns in the summary
        # Pattern: - [ ] **[Task]** - Owner: [Name] | Due: [Date] | Priority: [High/Med/Low]
        action_item_pattern = r'- \[ \] \*\*(.*?)\*\*(?: - Owner: (.*?))?(?: \| Due: (.*?))?(?: \| Priority: (.*?))?(?:\n|$)'
        
        matches = re.findall(action_item_pattern, summary, re.MULTILINE)
        
        for match in matches:
            task_text = match[0].strip()
            owner = match[1].strip() if match[1] else None
            due_date = match[2].strip() if match[2] else None
            priority = match[3].strip() if match[3] else 'Medium'
            
            # Clean up priority values
            priority_map = {
                'high': 'High',
                'med': 'Medium', 
                'medium': 'Medium',
                'low': 'Low',
                'urgent': 'Urgent'
            }
            priority = priority_map.get(priority.lower(), priority) if priority else 'Medium'
            
            action_items.append({
                'task': task_text,
                'owner': owner,
                'due_date': due_date,
                'priority': priority
            })
        
        # Also look for simpler patterns like: - [ ] Task description
        simple_pattern = r'- \[ \] (.*?)(?:\n|$)'
        simple_matches = re.findall(simple_pattern, summary, re.MULTILINE)
        
        # Add items that weren't caught by the detailed pattern
        detailed_tasks = {item['task'] for item in action_items}
        for simple_match in simple_matches:
            task_text = simple_match.strip()
            # Remove any markdown formatting
            task_text = re.sub(r'\*\*(.*?)\*\*', r'\1', task_text)
            
            if task_text not in detailed_tasks and len(task_text) > 5:  # Avoid very short items
                action_items.append({
                    'task': task_text,
                    'owner': None,
                    'due_date': None,
                    'priority': 'Medium'
                })
        
        logging.info(f"Extracted {len(action_items)} action items from summary")
        return action_items
    
    def create_task_in_database(self, action_item: Dict[str, Any], source_page_id: str, meeting_title: str) -> Optional[str]:
        """
        Create a task in the task database.
        
        Args:
            action_item: Dictionary containing task details
            source_page_id: ID of the source meeting page
            meeting_title: Title of the source meeting
            
        Returns:
            URL of created task page or None if failed
        """
        if not self.task_database_id or not self.create_tasks:
            return None
        
        try:
            # Build task properties (matching your database schema)
            properties = {
                'Task name': {
                    'title': [{'text': {'content': action_item['task']}}]
                },
                'Status': {
                    'status': {'name': 'Not started'}
                },
                'Priority': {
                    'select': {'name': action_item['priority']}
                },
                'Task type': {
                    'multi_select': [{'name': 'Action Item'}]
                },
                'Source Meeting': {
                    'relation': [{'id': source_page_id}]
                }
            }
            
            # Add assigned person if available
            if action_item.get('owner'):
                # Note: 'people' property requires user IDs, not names
                # Could implement user lookup in the future
                logging.info(f"Task owner '{action_item['owner']}' noted but not set (requires user ID mapping)")
            
            # Add due date if available and parseable
            if action_item.get('due_date'):
                try:
                    # Try to parse common date formats for the due date field
                    due_date = action_item['due_date']
                    if due_date.lower() not in ['asap', 'tbd', 'n/a'] and '-' in due_date:
                        properties['Due date'] = {
                            'date': {'start': due_date}
                        }
                        logging.info(f"Set due date: {due_date}")
                except Exception as e:
                    logging.debug(f"Could not parse due date '{action_item.get('due_date')}': {e}")
                    pass
            
            # Create the task page
            task_page = self.client.pages.create(
                parent={'database_id': self.task_database_id},
                properties=properties
            )
            
            task_url = task_page['url']
            logging.info(f"Created task: {action_item['task'][:50]}... -> {task_url}")
            return task_url
            
        except Exception as e:
            logging.error(f"Failed to create task '{action_item['task']}': {str(e)}")
            return None
    
    def create_tasks_from_summary(self, summary: str, source_page_id: str, meeting_title: str) -> List[str]:
        """
        Extract action items from summary and create tasks in task database.
        
        Args:
            summary: Meeting summary containing action items
            source_page_id: ID of the source meeting page
            meeting_title: Title of the source meeting
            
        Returns:
            List of URLs for created tasks
        """
        if not self.task_database_id or not self.create_tasks:
            logging.info("Task creation disabled or no task database configured")
            return []
        
        action_items = self.extract_action_items(summary)
        task_urls = []
        
        for action_item in action_items:
            task_url = self.create_task_in_database(action_item, source_page_id, meeting_title)
            if task_url:
                task_urls.append(task_url)
        
        logging.info(f"Created {len(task_urls)} tasks from {len(action_items)} action items")
        return task_urls