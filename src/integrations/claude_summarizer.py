"""
Claude API integration for meeting summarization.
"""

import os
from typing import Dict, Any, Optional
import logging

try:
    import anthropic
except ImportError:
    anthropic = None


class ClaudeSummarizer:
    """Handles meeting summarization using Claude API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Claude summarizer.
        
        Args:
            config: Configuration dictionary containing Claude settings
        """
        if anthropic is None:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )
        
        # Get API key from config or environment
        api_key = config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "Claude API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or add it to your config file."
            )
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = config.get('model', 'claude-3-haiku-20240307')
        self.max_tokens = config.get('max_tokens', 1000)
        self.temperature = config.get('temperature', 0.1)
        
        # Summary templates
        self.templates = {
            'default': self._get_default_template(),
            'business': self._get_business_template(),
            'technical': self._get_technical_template(),
            'personal': self._get_personal_template()
        }
        
        self.template_type = config.get('template_type', 'business')
        
    def _get_default_template(self) -> str:
        """Default summarization template."""
        return """
Please provide a concise summary of this meeting transcript using proper markdown formatting that Notion can interpret:

## Key Topics Discussed
- List the main topics and discussions

## Important Decisions Made
- Any decisions or agreements reached

## Action Items
- Tasks assigned with owners (if mentioned)
- Deadlines (if mentioned)

## Next Steps
- Follow-up meetings or actions planned

Use proper markdown headers (##) and bullet points (-). Keep the summary clear and well-structured.
        """.strip()
    
    def _get_business_template(self) -> str:
        """Business meeting template."""
        return """
Please analyze this business meeting transcript and provide a structured summary:

## Meeting Summary

### Key Discussion Points
- List the main topics and discussions

### Decisions Made
- Any decisions or agreements reached

### Action Items
- Tasks assigned with owners (if mentioned)
- Deadlines (if mentioned)

### Financial/Business Impact
- Revenue, costs, or business metrics mentioned
- Deal statuses or customer updates

### Next Steps
- Follow-up meetings or actions planned

### Risks/Concerns
- Any issues or concerns raised

Keep it professional and concise.
        """.strip()
    
    def _get_technical_template(self) -> str:
        """Technical meeting template."""
        return """
Please summarize this technical meeting transcript:

## Technical Meeting Summary

### Topics Covered
- Main technical discussions

### Technical Decisions
- Architecture, implementation, or technical choices made

### Issues/Blockers
- Problems identified and solutions discussed

### Action Items
- Development tasks and assignments

### Next Steps
- Technical milestones and timelines

Focus on technical details and implementation aspects.
        """.strip()
    
    def _get_personal_template(self) -> str:
        """Personal/casual meeting template."""
        return """
Please provide a friendly summary of this conversation:

## Conversation Summary

### Main Topics
- What was discussed

### Important Points
- Key information shared

### Plans/Next Steps
- Any plans or follow-ups mentioned

Keep the tone casual and conversational.
        """.strip()
    
    def summarize_meeting(
        self, 
        transcript: str, 
        template_type: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Summarize a meeting transcript using Claude.
        
        Args:
            transcript: The meeting transcript text
            template_type: Type of template to use ('default', 'business', 'technical', 'personal')
            custom_prompt: Custom prompt to override template
            
        Returns:
            Generated summary text
        """
        # Use custom prompt or template
        if custom_prompt:
            system_prompt = custom_prompt
        else:
            template = template_type or self.template_type
            system_prompt = self.templates.get(template, self.templates['default'])
        
        # Truncate transcript if too long (Claude has context limits)
        max_transcript_length = 100000  # Adjust based on model limits
        if len(transcript) > max_transcript_length:
            transcript = transcript[:max_transcript_length] + "\n\n[Transcript truncated...]"
            logging.warning("Transcript truncated due to length limits")
        
        try:
            logging.debug(f"Sending transcript to Claude (model: {self.model})")
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"{system_prompt}\n\nTranscript:\n{transcript}"
                    }
                ]
            )
            
            summary = message.content[0].text
            logging.debug("Summary generated successfully")
            return summary
            
        except Exception as e:
            logging.error(f"Claude API error: {str(e)}")
            raise
    
    def get_available_templates(self) -> Dict[str, str]:
        """Return available summary templates."""
        return {name: template.split('\n')[0] for name, template in self.templates.items()}
    
    def set_template_type(self, template_type: str) -> None:
        """Set the default template type."""
        if template_type not in self.templates:
            raise ValueError(f"Unknown template type: {template_type}")
        self.template_type = template_type