"""
Claude API integration for meeting summarization with role-based prompting.
"""

import os
from typing import Dict, Any, Optional, Tuple
import logging
from enum import Enum

try:
    import anthropic
except ImportError:
    anthropic = None


class MeetingType(Enum):
    """Meeting types for specialized processing."""
    ONE_ON_ONE = "1:1"
    TEAM_MEETING = "team_meeting"
    FORECAST = "forecast"
    CUSTOMER = "customer"
    TECHNICAL = "technical"
    STRATEGIC = "strategic"


class ClaudeSummarizer:
    """Handles meeting summarization using Claude API with role-based prompting."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Claude summarizer with role-based configuration."""
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
        self.model = config.get('model', 'claude-3-5-sonnet-20241022')  # Updated to latest
        self.max_tokens = config.get('max_tokens', 2000)  # Increased for detailed summaries
        self.temperature = config.get('temperature', 0.1)
        
        # User context for personalization
        self.user_context = config.get('user_context', {
            'role': 'Director of Solutions Engineering',
            'region': 'EMEA',
            'team_size': 6,
            'company': 'Entrust'
        })
        
        # Define role prompts for different meeting types
        self.role_prompts = self._initialize_role_prompts()
        
    def _initialize_role_prompts(self) -> Dict[MeetingType, str]:
        """Initialize system prompts for different roles."""
        return {
            MeetingType.ONE_ON_ONE: """You are an experienced senior solutions engineering manager specializing in team development and performance management. You excel at identifying coaching opportunities, tracking commitments, and ensuring clear action items from 1:1 discussions. You understand the importance of both technical growth and soft skills development for solutions engineers.""",
            
            MeetingType.TEAM_MEETING: """You are a senior solutions engineering leader focused on team coordination, delivery excellence, and cross-functional collaboration. You understand how to balance customer needs, technical requirements, and team capacity while maintaining high morale and productivity.""",
            
            MeetingType.FORECAST: """You are a seasoned sales operations analyst with deep expertise in pipeline management and revenue forecasting. You understand the nuances of solution engineering metrics, deal progression, and risk assessment in enterprise software sales.""",
            
            MeetingType.CUSTOMER: """You are a customer-focused solutions architect who understands both technical requirements and business value. You excel at identifying customer pain points, mapping solutions to business outcomes, and ensuring successful technical engagement strategies.""",
            
            MeetingType.TECHNICAL: """You are a principal solutions engineer with expertise in identity verification solutions. You understand complex technical architectures, integration challenges, and can identify both immediate solutions and long-term technical strategies.""",
            
            MeetingType.STRATEGIC: """You are a strategic business advisor specializing in EMEA markets and enterprise technology sales. You understand regional dynamics, competitive positioning, and how to align technical capabilities with market opportunities."""
        }
    
    def _get_user_message(self, meeting_type: MeetingType, transcript: str) -> str:
        """Create the user message with instructions based on meeting type."""
        base_instructions = f"""
I need you to summarize the following {meeting_type.value} meeting transcript. 
Context: I'm the {self.user_context['role']} for {self.user_context['region']} at {self.user_context['company']}, managing a team of {self.user_context['team_size']} Solutions Engineers.

Please provide a structured summary using Notion-compatible markdown formatting:
"""
        
        # Meeting-specific instructions
        type_instructions = {
            MeetingType.ONE_ON_ONE: """
## 1:1 Meeting Summary

## Discussion Highlights
- **Performance/Development:** [Key points about growth, achievements, or areas for improvement]
- **Current Projects:** [Status updates on key initiatives]
- **Challenges/Blockers:** [Any issues raised and support needed]

## Coaching & Development
- **Strengths Demonstrated:** [Specific examples]
- **Growth Areas:** [Skills or behaviors to develop]
- **Career Progression:** [Any discussions about next steps]

## Action Items
- [ ] **[Manager Action]** - Due: [Date]
- [ ] **[Employee Action]** - Due: [Date]

## Follow-up for Next 1:1
- [Topics to revisit]
- [Progress to check]

## Manager Notes (Confidential)
- [Any observations about engagement, motivation, or concerns]
""",
            
            MeetingType.FORECAST: """
## Forecast Call Summary

## Pipeline Summary
- **Committed:** €[Amount] ([X] deals)
- **Best Case:** €[Amount] ([X] deals)
- **Pipeline Coverage:** [X:1 ratio]

## Key Deals
| Deal | Value | Stage | Close Date | Risk Level | Next Steps |
|------|-------|-------|------------|------------|------------|
| [Customer] | €[Value] | [Stage] | [Date] | [H/M/L] | [Action] |

## Changes Since Last Forecast
- **New Additions:** [Deals added to forecast]
- **Slipped Deals:** [Deals pushed out with reasons]
- **Lost/Removed:** [Deals removed with reasons]

## Risk Assessment
- **High Risk Deals:** [List with mitigation plans]
- **Dependencies:** [Technical, legal, or commercial blockers]

## Resource Requirements
- **SE Capacity:** [Any resource constraints]
- **Technical Support:** [Specialist needs]

## Action Items
- [ ] **[Task]** - Owner: [Name] - Due: [Date]

## Commitments Made
- [Specific commitments for the period]
""",
            
            MeetingType.TEAM_MEETING: """
## Team Meeting Summary

## Team Updates
- **Wins/Successes:** [Celebrate achievements]
- **Current Priorities:** [Top 3-5 team focuses]

## Project Status
| Project | Owner | Status | Next Milestone | Risks |
|---------|-------|---------|----------------|-------|
| [Name] | [SE] | [RAG] | [Date/Action] | [Issues] |

## Cross-functional Topics
- **Product Updates:** [Relevant product changes]
- **Process Changes:** [Any new procedures]
- **Training Needs:** [Skills gaps identified]

## Team Health
- **Morale Indicators:** [Observations]
- **Workload Balance:** [Any concerns]

## Action Items
- [ ] **[Task]** - Owner: [Name] - Due: [Date]

## Next Meeting Focus
- [Topics for next sync]
"""
        }
        
        instructions = type_instructions.get(
            meeting_type, 
            self._get_generic_instructions()
        )
        
        return f"""{base_instructions}

{instructions}

---
**Formatting Guidelines:**
- Use consistent ## headers for ALL main sections (never mix ## and ###)
- Bold important labels using **text**
- Use tables where appropriate
- Include checkbox format (- [ ]) for all action items
- If information isn't mentioned, omit the section
- Keep language professional but conversational
- Use British English spelling
- IMPORTANT: All section headers must be ## (level 2) - no ### headers

**Transcript:**
{transcript}"""
    
    def _get_generic_instructions(self) -> str:
        """Generic instructions for unspecified meeting types."""
        return """
## Meeting Summary

## Key Discussion Points
- **[Topic 1]:** [Summary and outcome]
- **[Topic 2]:** [Summary and outcome]

## Decisions Made
- [List key decisions with rationale]

## Action Items
- [ ] **[Task]** - Owner: [Name] - Due: [Date]

## Next Steps
- [Follow-up actions or meetings]
"""
    
    def detect_meeting_type(self, transcript: str) -> MeetingType:
        """Detect meeting type from transcript content."""
        transcript_lower = transcript.lower()
        
        # Detection logic based on keywords
        if any(phrase in transcript_lower for phrase in ['1:1', 'one on one', 'performance review', 'career development']):
            return MeetingType.ONE_ON_ONE
        elif any(phrase in transcript_lower for phrase in ['forecast', 'pipeline', 'commit', 'quarter close']):
            return MeetingType.FORECAST
        elif any(phrase in transcript_lower for phrase in ['customer', 'client', 'prospect', 'demo']):
            return MeetingType.CUSTOMER
        elif any(phrase in transcript_lower for phrase in ['architecture', 'integration', 'api', 'technical design']):
            return MeetingType.TECHNICAL
        elif any(phrase in transcript_lower for phrase in ['strategy', 'market', 'competitive', 'positioning']):
            return MeetingType.STRATEGIC
        else:
            return MeetingType.TEAM_MEETING
    
    def summarize_meeting(
        self, 
        transcript: str, 
        meeting_type: Optional[MeetingType] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Summarize a meeting transcript using Claude with role-based prompting.
        
        Args:
            transcript: The meeting transcript text
            meeting_type: Type of meeting (auto-detected if not provided)
            custom_prompt: Custom prompt to override defaults
            
        Returns:
            Generated summary text
        """
        # Detect meeting type if not provided
        if meeting_type is None:
            meeting_type = self.detect_meeting_type(transcript)
            logging.info(f"Auto-detected meeting type: {meeting_type.value}")
        
        # Truncate transcript if too long
        max_transcript_length = 100000
        if len(transcript) > max_transcript_length:
            transcript = transcript[:max_transcript_length] + "\n\n[Transcript truncated...]"
            logging.warning("Transcript truncated due to length limits")
        
        try:
            # Get role-based system prompt
            system_prompt = self.role_prompts.get(meeting_type, self.role_prompts[MeetingType.TEAM_MEETING])
            
            # Get user message with instructions
            if custom_prompt:
                user_message = f"{custom_prompt}\n\nTranscript:\n{transcript}"
            else:
                user_message = self._get_user_message(meeting_type, transcript)
            
            logging.debug(f"Sending transcript to Claude (model: {self.model}, type: {meeting_type.value})")
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,  # Role-based system prompt
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            
            summary = message.content[0].text
            logging.debug("Summary generated successfully")
            return summary
            
        except Exception as e:
            logging.error(f"Claude API error: {str(e)}")
            raise
    
    def create_custom_role(self, role_description: str) -> str:
        """Create a custom role prompt for specialized meetings."""
        return f"""You are {role_description}. You bring deep domain expertise and understand the nuances of this specialized area. Your summaries reflect both tactical details and strategic implications."""
    
    def get_available_meeting_types(self) -> Dict[str, str]:
        """Return available meeting types."""
        return {meeting_type.value: meeting_type.name for meeting_type in MeetingType}
    
    def set_user_context(self, context: Dict[str, Any]) -> None:
        """Update user context for personalization."""
        self.user_context.update(context)