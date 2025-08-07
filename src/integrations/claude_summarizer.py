"""
Claude API integration for meeting summarization with role-based prompting.
Enhanced version with improved accuracy, error handling, and performance.
Uses original simple truncation approach for long transcripts.
"""

import os
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
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
    """Handles meeting summarization using Claude API with enhanced role-based prompting."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Claude summarizer with enhanced configuration validation."""
        if anthropic is None:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )
        
        # Validate required config
        self._validate_config(config)
        
        # Get API key from config or environment
        api_key = config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "Claude API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or add it to your config file."
            )
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = config.get('model', 'claude-sonnet-4-20250514')  # Latest model
        self.max_tokens = config.get('max_tokens', 3000)  # Increased for detailed summaries
        self.temperature = config.get('temperature', 0.1)
        
        # Original truncation settings
        self.max_transcript_length = config.get('max_transcript_length', 100000)
        
        # User context for personalization with better defaults
        self.user_context = config.get('user_context', {})
        self._set_default_user_context()
        
        # Define role prompts for different meeting types
        self.role_prompts = self._initialize_role_prompts()
        
        # Cache for similar transcripts
        self._summary_cache = {}
        
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration parameters."""
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")
            
        # Check for reasonable values
        max_tokens = config.get('max_tokens', 3000)
        if max_tokens < 500 or max_tokens > 8000:
            logging.warning(f"max_tokens value {max_tokens} may not be optimal (recommended: 2000-4000)")
            
        temperature = config.get('temperature', 0.1)
        if temperature < 0 or temperature > 1:
            raise ValueError("temperature must be between 0 and 1")
    
    def _set_default_user_context(self) -> None:
        """Set default user context values."""
        defaults = {
            'role': 'Director of Solutions Engineering',
            'region': 'EMEA',
            'team_size': 6,
            'company': 'Entrust'
        }
        
        for key, default_value in defaults.items():
            if key not in self.user_context:
                self.user_context[key] = default_value
                
        if not self.user_context.get('role'):
            logging.warning("No role specified in user context - summaries may be less targeted")
        
    def _initialize_role_prompts(self) -> Dict[MeetingType, str]:
        """Initialize enhanced system prompts for different roles."""
        base_instruction = "Use British English spelling throughout (e.g., 'realise', 'colour', 'organised')."
        
        return {
            MeetingType.ONE_ON_ONE: f"""{base_instruction} You are an experienced senior solutions engineering manager specialising in team development and performance management. You excel at identifying coaching opportunities, tracking commitments, and ensuring clear action items from 1:1 discussions. You understand the importance of both technical growth and soft skills development for solutions engineers.""",
            
            MeetingType.TEAM_MEETING: f"""{base_instruction} You are a senior solutions engineering leader focused on team coordination, delivery excellence, and cross-functional collaboration. You understand how to balance customer needs, technical requirements, and team capacity whilst maintaining high morale and productivity.""",
            
            MeetingType.FORECAST: f"""{base_instruction} You are a seasoned sales operations analyst with deep expertise in pipeline management and revenue forecasting. You understand the nuances of solution engineering metrics, deal progression, and risk assessment in enterprise software sales.""",
            
            MeetingType.CUSTOMER: f"""{base_instruction} You are a customer-focused solutions architect who understands both technical requirements and business value. You excel at identifying customer pain points, mapping solutions to business outcomes, and ensuring successful technical engagement strategies.""",
            
            MeetingType.TECHNICAL: f"""{base_instruction} You are a principal solutions engineer with expertise in identity verification solutions. You understand complex technical architectures, integration challenges, and can identify both immediate solutions and long-term technical strategies.""",
            
            MeetingType.STRATEGIC: f"""{base_instruction} You are a strategic business advisor specialising in EMEA markets and enterprise technology sales. You understand regional dynamics, competitive positioning, and how to align technical capabilities with market opportunities."""
        }
    
    def _count_tokens_estimate(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token for English text)."""
        return len(text) // 4

    def _truncate_transcript(self, transcript: str) -> str:
        """Apply original simple truncation if transcript exceeds length limit."""
        if len(transcript) <= self.max_transcript_length:
            return transcript
        
        logging.warning(f"Transcript truncated due to length limits ({len(transcript)} > {self.max_transcript_length} chars)")
        return transcript[:self.max_transcript_length] + "\n\n[Transcript truncated...]"
    
    def detect_meeting_type(self, transcript: str, participants: Optional[List[str]] = None) -> Tuple[MeetingType, float]:
        """Enhanced meeting type detection with confidence scoring."""
        transcript_lower = transcript.lower()
        scores = {meeting_type: 0.0 for meeting_type in MeetingType}
        
        # Enhanced keyword scoring with weights
        keywords = {
            MeetingType.ONE_ON_ONE: {
                'high_weight': ['1:1', 'one on one', 'performance review', 'career development', 'feedback', 'personal development'],
                'medium_weight': ['growth', 'coaching', 'personal', 'individual', 'progress', 'goals'],
                'low_weight': ['you', 'your performance', 'development plan']
            },
            MeetingType.FORECAST: {
                'high_weight': ['forecast', 'pipeline', 'commit', 'quarter close', 'revenue', 'quota'],
                'medium_weight': ['deals', 'close date', 'probability', 'funnel', 'attainment', 'bookings'],
                'low_weight': ['q1', 'q2', 'q3', 'q4', 'monthly', 'target']
            },
            MeetingType.CUSTOMER: {
                'high_weight': ['customer', 'client', 'prospect', 'demo', 'requirements', 'use case'],
                'medium_weight': ['stakeholder', 'business case', 'roi', 'solution', 'integration', 'implementation'],
                'low_weight': ['meeting with', 'client call', 'customer meeting']
            },
            MeetingType.TECHNICAL: {
                'high_weight': ['architecture', 'integration', 'api', 'technical design', 'system', 'infrastructure'],
                'medium_weight': ['configuration', 'deployment', 'security', 'authentication', 'protocol', 'database'],
                'low_weight': ['technical', 'setup', 'install']
            },
            MeetingType.STRATEGIC: {
                'high_weight': ['strategy', 'market', 'competitive', 'positioning', 'roadmap', 'planning'],
                'medium_weight': ['vision', 'direction', 'priorities', 'objectives', 'initiative', 'transformation'],
                'low_weight': ['future', 'long term', 'next year']
            },
            MeetingType.TEAM_MEETING: {
                'high_weight': ['team', 'everyone', 'all hands', 'standup', 'sync', 'status update'],
                'medium_weight': ['updates', 'blockers', 'sprint', 'project status', 'coordination'],
                'low_weight': ['team meeting', 'weekly sync', 'daily standup']
            }
        }
        
        # Score based on keyword frequency and weight
        for meeting_type, criteria in keywords.items():
            for word in criteria.get('high_weight', []):
                scores[meeting_type] += transcript_lower.count(word) * 3.0
            for word in criteria.get('medium_weight', []):
                scores[meeting_type] += transcript_lower.count(word) * 1.5
            for word in criteria.get('low_weight', []):
                scores[meeting_type] += transcript_lower.count(word) * 0.5
        
        # Additional heuristics
        if participants and len(participants) == 2:
            scores[MeetingType.ONE_ON_ONE] += 2.0
        
        transcript_length = len(transcript.split())
        if transcript_length < 500:  # Short meeting likely 1:1
            scores[MeetingType.ONE_ON_ONE] += 1.0
        
        # Find highest scoring type and confidence
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.0
        
        # Default to team meeting if confidence is low
        if confidence < 0.3:
            max_type = MeetingType.TEAM_MEETING
            confidence = 0.3
            
        return max_type, confidence
    
    def _get_few_shot_examples(self, meeting_type: MeetingType) -> str:
        """Provide few-shot examples for consistent output formatting."""
        examples = {
            MeetingType.ONE_ON_ONE: """
EXAMPLE INPUT: "We discussed Sarah's progress on the enterprise deals. She's doing well but needs help with objection handling. I'll set up coaching sessions and she'll practice with mock scenarios."

EXAMPLE OUTPUT:
## Discussion Highlights
- **Performance/Development:** Sarah showing strong progress on enterprise deals but identified need for objection handling skills
- **Current Projects:** Enterprise deal pipeline management

## Coaching & Development  
- **Strengths Demonstrated:** Enterprise deal management, client engagement
- **Growth Areas:** Objection handling techniques and confidence

## Action Items
- [ ] **Set up objection handling coaching sessions** - Manager Action - Due: This week
- [ ] **Practice with mock objection scenarios** - Sarah - Due: Next week
""",
            
            MeetingType.FORECAST: """
EXAMPLE INPUT: "Our committed pipeline is £450K with three deals. The TechCorp deal worth £200K is at 90% but legal is taking longer than expected. We might need to slip it to next quarter."

EXAMPLE OUTPUT:
## Pipeline Summary
- **Committed:** £450K (3 deals)
- **Risk Level:** Medium due to legal delays

## Key Deals
| Deal | Value | Stage | Close Date | Risk Level | Next Steps |
|------|-------|-------|------------|------------|------------|
| TechCorp | £200K | 90% | This Quarter | High | Chase legal approval |

## Risk Assessment
- **High Risk Deals:** TechCorp - legal approval delays may cause slip
""",
        }
        
        return examples.get(meeting_type, "")
    
    def _get_user_message(self, meeting_type: MeetingType, transcript: str, previous_meeting_summary: Optional[str] = None) -> str:
        """Create enhanced user message with examples and context."""
        base_instructions = f"""
I need you to summarise the following {meeting_type.value} meeting transcript. 
Context: I'm the {self.user_context['role']} for {self.user_context['region']} at {self.user_context['company']}, managing a team of {self.user_context['team_size']} Solutions Engineers.

Please provide a structured summary using Notion-compatible markdown formatting:
"""
        
        # Add few-shot examples
        examples = self._get_few_shot_examples(meeting_type)
        if examples:
            base_instructions += f"\n{examples}\n"
        
        # Add previous meeting context if provided
        context_addition = ""
        if previous_meeting_summary:
            context_addition = f"""
PREVIOUS MEETING CONTEXT:
{previous_meeting_summary[:1000]}{'...' if len(previous_meeting_summary) > 1000 else ''}

Please note any follow-ups from previous discussions and mark completed items.
"""
        
        # Meeting-specific instructions (keeping existing templates)
        type_instructions = {
            MeetingType.ONE_ON_ONE: """
## 1:1 Meeting Summary

## Discussion Highlights
- **Performance/Development:** [Key points about growth, achievements, or areas for improvement]
- **Current Projects:** [Status updates on key initiatives]
- **Challenges/Blockers:** [Any issues raised and support needed]

## Coaching & Development
- **Strengths Demonstrated:** [Specific examples]
- **Growth Areas:** [Skills or behaviours to develop]
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
""",
        }
        
        instructions = type_instructions.get(
            meeting_type, 
            self._get_generic_instructions()
        )
        
        formatting_guidelines = """
---
**Formatting Guidelines:**
- Use consistent ## headers for ALL main sections (never mix ## and ###)
- Bold important labels using **text**
- Use tables where appropriate for structured data
- Include checkbox format (- [ ]) for all action items
- If information isn't mentioned in the transcript, omit that section
- Keep language professional but conversational
- Use British English spelling throughout
- IMPORTANT: All section headers must be ## (level 2) - no ### headers
- Focus on actionable outcomes and clear next steps
"""
        
        return f"""{base_instructions}
{context_addition}
{instructions}
{formatting_guidelines}

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
    
    def _create_cache_key(self, transcript: str, meeting_type: MeetingType) -> str:
        """Create cache key for transcript."""
        content = f"{transcript[:1000]}{meeting_type.value}"  # Use first 1000 chars + type
        return hashlib.md5(content.encode()).hexdigest()
    
    def summarize_meeting(
        self, 
        transcript: str, 
        meeting_type: Optional[MeetingType] = None,
        participants: Optional[List[str]] = None,
        previous_meeting_summary: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Summarize a meeting transcript using Claude with enhanced role-based prompting.
        Uses original simple truncation for long transcripts.
        
        Args:
            transcript: The meeting transcript text
            meeting_type: Type of meeting (auto-detected if not provided)
            participants: List of meeting participants for better detection
            previous_meeting_summary: Summary from previous related meeting
            custom_prompt: Custom prompt to override defaults
            use_cache: Whether to use response caching
            
        Returns:
            Dict containing summary, detected type, confidence, and metadata
        """
        # Detect meeting type if not provided
        confidence = 1.0
        if meeting_type is None:
            meeting_type, confidence = self.detect_meeting_type(transcript, participants)
            logging.info(f"Auto-detected meeting type: {meeting_type.value} (confidence: {confidence:.2f})")
        
        # Check cache first
        cache_key = self._create_cache_key(transcript, meeting_type) if use_cache else None
        if cache_key and cache_key in self._summary_cache:
            logging.debug("Using cached summary")
            cached_result = self._summary_cache[cache_key].copy()
            cached_result['cached'] = True
            return cached_result
        
        # Apply original truncation if too long
        original_length = len(transcript)
        transcript = self._truncate_transcript(transcript)
        was_truncated = len(transcript) < original_length
        
        try:
            # Get role-based system prompt
            system_prompt = self.role_prompts.get(meeting_type, self.role_prompts[MeetingType.TEAM_MEETING])
            
            # Get user message with instructions
            if custom_prompt:
                user_message = f"{custom_prompt}\n\nTranscript:\n{transcript}"
            else:
                user_message = self._get_user_message(meeting_type, transcript, previous_meeting_summary)
            
            estimated_tokens = self._count_tokens_estimate(user_message)
            logging.debug(f"Sending to Claude (model: {self.model}, type: {meeting_type.value}, ~{estimated_tokens} tokens)")
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            
            summary = message.content[0].text
            
            # Create result dict
            result = {
                'summary': summary,
                'meeting_type': meeting_type.value,
                'detection_confidence': confidence,
                'was_truncated': was_truncated,
                'original_length': original_length,
                'processed_tokens': estimated_tokens,
                'cached': False
            }
            
            # Cache the result
            if cache_key and use_cache:
                self._summary_cache[cache_key] = result.copy()
                # Limit cache size
                if len(self._summary_cache) > 50:
                    # Remove oldest entry
                    oldest_key = next(iter(self._summary_cache))
                    del self._summary_cache[oldest_key]
            
            logging.debug("Summary generated successfully")
            return result
            
        except anthropic.APITimeoutError:
            logging.error("Claude API timeout - transcript may be too long")
            raise
        except anthropic.RateLimitError as e:
            logging.error(f"Rate limit exceeded: {e}")
            raise
        except anthropic.APIError as e:
            logging.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during summarization: {str(e)}")
            raise
    
    def create_custom_role(self, role_description: str) -> str:
        """Create a custom role prompt for specialised meetings."""
        return f"""Use British English spelling throughout. You are {role_description}. You bring deep domain expertise and understand the nuances of this specialised area. Your summaries reflect both tactical details and strategic implications."""
    
    def get_available_meeting_types(self) -> Dict[str, str]:
        """Return available meeting types with descriptions."""
        descriptions = {
            MeetingType.ONE_ON_ONE: "One-on-one meetings with team members",
            MeetingType.TEAM_MEETING: "Team meetings and standups",
            MeetingType.FORECAST: "Sales forecast and pipeline reviews",
            MeetingType.CUSTOMER: "Customer calls and demos",
            MeetingType.TECHNICAL: "Technical discussions and architecture reviews",
            MeetingType.STRATEGIC: "Strategic planning and market discussions"
        }
        return {meeting_type.value: descriptions[meeting_type] for meeting_type in MeetingType}
    
    def set_user_context(self, context: Dict[str, Any]) -> None:
        """Update user context for personalisation."""
        self.user_context.update(context)
        logging.info(f"Updated user context: {context}")
    
    def clear_cache(self) -> None:
        """Clear the summary cache."""
        self._summary_cache.clear()
        logging.info("Summary cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'cache_size': len(self._summary_cache),
            'max_cache_size': 50
        }
    
    def get_truncation_stats(self) -> Dict[str, Any]:
        """Get truncation configuration."""
        return {
            'max_transcript_length': self.max_transcript_length,
            'max_transcript_tokens': self.max_transcript_length // 4
        }