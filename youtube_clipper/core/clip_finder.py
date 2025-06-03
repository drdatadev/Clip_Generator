"""
Clip Finder Module

This module uses GPT-4 to analyze transcriptions and identify specific clip segments
based on user descriptions. Provides intelligent timestamp detection for content extraction.
"""

import re
from typing import Optional, Tuple, Dict, List
import openai

from ..utils.logger import get_logger
from ..config import config
from ..exceptions.custom_exceptions import ClipExtractionError, ConfigurationError

logger = get_logger(__name__)


class ClipFinder:
    """
    Uses GPT-4 to analyze transcriptions and find specific content segments.
    
    This class provides methods to identify clip timestamps based on user descriptions,
    with intelligent content matching and robust error handling.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize the clip finder with OpenAI credentials.
        
        Args:
            api_key: OpenAI API key
            model: GPT model to use for analysis
            
        Raises:
            ConfigurationError: If API key is invalid or missing
        """
        if not api_key or not api_key.strip():
            raise ConfigurationError("OpenAI API key is required")
            
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
        
        logger.info(f"ClipFinder initialized with model: {model}")
    
    def find_clip_timestamps(self, transcription: str, clip_description: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Find start and end timestamps for a clip based on description.
        
        Args:
            transcription: Full video transcription
            clip_description: User description of desired clip
            
        Returns:
            Tuple of (start_time, end_time) in seconds, or (None, None) if not found
            
        Raises:
            ClipExtractionError: If analysis fails
        """
        try:
            logger.info(f"Analyzing transcription to find clip: '{clip_description}'")
            
            # Prepare the transcription with timestamps if available
            prepared_transcription = self._prepare_transcription_for_analysis(transcription)
            
            # Create the prompt for GPT-4
            prompt = self._create_clip_finding_prompt(prepared_transcription, clip_description)
            
            # Call GPT-4 to analyze the content
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing video transcriptions and identifying specific content segments. You provide precise timestamp ranges for requested clips."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=config.GPT_TEMPERATURE,
                max_tokens=config.GPT_MAX_TOKENS
            )
            
            # Parse the response to extract timestamps
            timestamps = self._parse_timestamp_response(response.choices[0].message.content)
            
            if timestamps[0] is not None and timestamps[1] is not None:
                start_time, end_time = timestamps
                duration = end_time - start_time
                
                logger.info(f"Found clip: {start_time:.1f}s to {end_time:.1f}s (duration: {duration:.1f}s)")
                
                # Validate the clip duration
                if not config.validate_clip_duration(duration):
                    logger.warning(f"Clip duration ({duration:.1f}s) outside recommended range")
                
                return start_time, end_time
            else:
                logger.warning("Could not identify clip timestamps from GPT response")
                return None, None
                
        except openai.APIError as e:
            logger.error(f"OpenAI API error during clip finding: {e}")
            raise ClipExtractionError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Clip finding failed: {e}")
            raise ClipExtractionError(f"Clip finding failed: {e}")
    
    def _prepare_transcription_for_analysis(self, transcription: str) -> str:
        """
        Prepare transcription text for GPT analysis by adding structure.
        
        Args:
            transcription: Raw transcription text
            
        Returns:
            Formatted transcription for analysis
        """
        # If transcription is too long, truncate it but keep important parts
        if len(transcription) > config.MAX_TRANSCRIPTION_LENGTH:
            logger.info(f"Transcription too long ({len(transcription)} chars), truncating to {config.MAX_TRANSCRIPTION_LENGTH}")
            # Keep first and last portions, and middle section
            part_size = config.MAX_TRANSCRIPTION_LENGTH // 3
            beginning = transcription[:part_size]
            end = transcription[-part_size:]
            middle_start = len(transcription) // 2 - part_size // 2
            middle = transcription[middle_start:middle_start + part_size]
            
            transcription = f"{beginning}\n\n[... MIDDLE SECTION ...]\n{middle}\n\n[... END SECTION ...]\n{end}"
        
        # Add line numbers for reference (approximate timestamps)
        lines = transcription.split('\n')
        numbered_lines = []
        
        for i, line in enumerate(lines):
            if line.strip():
                # Estimate timestamp based on line position (very rough)
                estimated_time = (i / len(lines)) * 1800  # Assume max 30 min video
                numbered_lines.append(f"[~{estimated_time:.0f}s] {line.strip()}")
            else:
                numbered_lines.append("")
        
        return '\n'.join(numbered_lines)
    
    def _create_clip_finding_prompt(self, transcription: str, clip_description: str) -> str:
        """
        Create a detailed prompt for GPT-4 to find clip timestamps.
        
        Args:
            transcription: Prepared transcription with timestamps
            clip_description: User's description of desired clip
            
        Returns:
            Formatted prompt for GPT-4
        """
        return f"""
Analyze the following video transcription and find the specific segment described by the user.

TRANSCRIPTION:
{transcription}

USER REQUEST: "{clip_description}"

INSTRUCTIONS:
1. Find the section of the transcription that best matches the user's description
2. Identify clear start and end points for a coherent clip
3. Aim for clips between {config.TARGET_CLIP_DURATION_MIN}-{config.TARGET_CLIP_DURATION_MAX} seconds when possible
4. Ensure the clip has a natural beginning and ending
5. Provide your answer in this exact format:

START_TIME: [seconds]
END_TIME: [seconds]
REASONING: [brief explanation of why this section matches the request]

If you cannot find a suitable match, respond with:
START_TIME: NOT_FOUND
END_TIME: NOT_FOUND
REASONING: [explanation of why no match was found]

EXAMPLE RESPONSE FORMAT:
START_TIME: 245.5
END_TIME: 298.2
REASONING: This section discusses inflation's impact on bond markets, matching the user's request for inflation analysis.
"""
    
    def _parse_timestamp_response(self, response_text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse GPT-4 response to extract start and end timestamps.
        
        Args:
            response_text: GPT-4 response text
            
        Returns:
            Tuple of (start_time, end_time) or (None, None) if not found
        """
        try:
            # Look for START_TIME and END_TIME patterns
            start_pattern = r'START_TIME:\s*([0-9]+\.?[0-9]*|NOT_FOUND)'
            end_pattern = r'END_TIME:\s*([0-9]+\.?[0-9]*|NOT_FOUND)'
            
            start_match = re.search(start_pattern, response_text, re.IGNORECASE)
            end_match = re.search(end_pattern, response_text, re.IGNORECASE)
            
            if start_match and end_match:
                start_str = start_match.group(1)
                end_str = end_match.group(1)
                
                if start_str.upper() == 'NOT_FOUND' or end_str.upper() == 'NOT_FOUND':
                    return None, None
                
                try:
                    start_time = float(start_str)
                    end_time = float(end_str)
                    
                    # Validate that end time is after start time
                    if end_time <= start_time:
                        logger.warning(f"Invalid timestamps: end ({end_time}) <= start ({start_time})")
                        return None, None
                    
                    return start_time, end_time
                    
                except ValueError as e:
                    logger.error(f"Could not parse timestamps: {e}")
                    return None, None
            
            # Fallback: try to find any timestamp patterns in the response
            timestamp_patterns = r'(\d+\.?\d*)\s*(?:seconds?|s)\s*(?:to|-)?\s*(\d+\.?\d*)\s*(?:seconds?|s)'
            fallback_match = re.search(timestamp_patterns, response_text, re.IGNORECASE)
            
            if fallback_match:
                try:
                    start_time = float(fallback_match.group(1))
                    end_time = float(fallback_match.group(2))
                    
                    if end_time > start_time:
                        logger.info("Using fallback timestamp parsing")
                        return start_time, end_time
                except ValueError:
                    pass
            
            logger.warning("Could not parse timestamps from GPT response")
            return None, None
            
        except Exception as e:
            logger.error(f"Error parsing timestamp response: {e}")
            return None, None
    
    def find_multiple_clips(self, transcription: str, clip_descriptions: List[str]) -> List[Dict]:
        """
        Find multiple clips from the same transcription.
        
        Args:
            transcription: Full video transcription
            clip_descriptions: List of clip descriptions
            
        Returns:
            List of dictionaries with clip information
        """
        results = []
        
        for i, description in enumerate(clip_descriptions):
            try:
                logger.info(f"Finding clip {i+1}/{len(clip_descriptions)}: {description}")
                start_time, end_time = self.find_clip_timestamps(transcription, description)
                
                result = {
                    'description': description,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time if start_time and end_time else None,
                    'success': start_time is not None and end_time is not None
                }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to find clip {i+1}: {e}")
                results.append({
                    'description': description,
                    'start_time': None,
                    'end_time': None,
                    'duration': None,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def suggest_clip_improvements(self, transcription: str, start_time: float, 
                                end_time: float) -> Dict:
        """
        Suggest improvements to clip boundaries for better content flow.
        
        Args:
            transcription: Full video transcription
            start_time: Current start time
            end_time: Current end time
            
        Returns:
            Dictionary with improvement suggestions
        """
        try:
            # Extract context around the current clip
            context_window = 30  # seconds before and after
            
            prompt = f"""
Analyze this video transcription segment and suggest improvements to the clip boundaries for better flow and completeness.

CURRENT CLIP: {start_time:.1f}s to {end_time:.1f}s (duration: {end_time - start_time:.1f}s)

TRANSCRIPTION CONTEXT:
{transcription}

INSTRUCTIONS:
1. Review the current clip boundaries
2. Suggest better start/end points if they would improve content flow
3. Ensure the clip tells a complete story or makes a complete point
4. Aim for natural speech breaks and complete sentences
5. Consider if extending or shortening would improve clarity

Respond with:
SUGGESTED_START: [seconds or KEEP_CURRENT]
SUGGESTED_END: [seconds or KEEP_CURRENT]
IMPROVEMENT_REASON: [explanation of suggested changes]
CONFIDENCE: [HIGH/MEDIUM/LOW]
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert video editor who optimizes clip boundaries for maximum impact and clarity."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            return self._parse_improvement_response(response.choices[0].message.content, start_time, end_time)
            
        except Exception as e:
            logger.error(f"Failed to suggest improvements: {e}")
            return {
                'suggested_start': start_time,
                'suggested_end': end_time,
                'improvement_reason': 'Could not analyze improvements',
                'confidence': 'LOW'
            }
    
    def _parse_improvement_response(self, response_text: str, original_start: float, 
                                  original_end: float) -> Dict:
        """
        Parse improvement suggestions from GPT response.
        
        Args:
            response_text: GPT response text
            original_start: Original start time
            original_end: Original end time
            
        Returns:
            Dictionary with parsed improvements
        """
        try:
            # Parse suggested times
            start_pattern = r'SUGGESTED_START:\s*([0-9]+\.?[0-9]*|KEEP_CURRENT)'
            end_pattern = r'SUGGESTED_END:\s*([0-9]+\.?[0-9]*|KEEP_CURRENT)'
            reason_pattern = r'IMPROVEMENT_REASON:\s*(.+?)(?=\n|$)'
            confidence_pattern = r'CONFIDENCE:\s*(HIGH|MEDIUM|LOW)'
            
            start_match = re.search(start_pattern, response_text, re.IGNORECASE)
            end_match = re.search(end_pattern, response_text, re.IGNORECASE)
            reason_match = re.search(reason_pattern, response_text, re.IGNORECASE | re.DOTALL)
            confidence_match = re.search(confidence_pattern, response_text, re.IGNORECASE)
            
            # Parse start time
            if start_match:
                start_str = start_match.group(1)
                if start_str.upper() == 'KEEP_CURRENT':
                    suggested_start = original_start
                else:
                    try:
                        suggested_start = float(start_str)
                    except ValueError:
                        suggested_start = original_start
            else:
                suggested_start = original_start
            
            # Parse end time
            if end_match:
                end_str = end_match.group(1)
                if end_str.upper() == 'KEEP_CURRENT':
                    suggested_end = original_end
                else:
                    try:
                        suggested_end = float(end_str)
                    except ValueError:
                        suggested_end = original_end
            else:
                suggested_end = original_end
            
            # Parse other fields
            improvement_reason = reason_match.group(1).strip() if reason_match else "No specific improvements suggested"
            confidence = confidence_match.group(1).upper() if confidence_match else "MEDIUM"
            
            return {
                'suggested_start': suggested_start,
                'suggested_end': suggested_end,
                'improvement_reason': improvement_reason,
                'confidence': confidence,
                'changed': suggested_start != original_start or suggested_end != original_end
            }
            
        except Exception as e:
            logger.error(f"Error parsing improvement response: {e}")
            return {
                'suggested_start': original_start,
                'suggested_end': original_end,
                'improvement_reason': 'Could not parse suggestions',
                'confidence': 'LOW',
                'changed': False
            }
    
    def extract_key_topics(self, transcription: str) -> List[Dict]:
        """
        Extract key topics and their timestamps from transcription.
        
        Args:
            transcription: Full video transcription
            
        Returns:
            List of topics with timestamps and descriptions
        """
        try:
            prompt = f"""
Analyze this video transcription and identify the main topics discussed, along with their approximate timestamps.

TRANSCRIPTION:
{transcription}

INSTRUCTIONS:
1. Identify 3-7 main topics or themes discussed
2. For each topic, provide the approximate start time and a brief description
3. Focus on substantive content sections, not introductions or conclusions
4. Format your response as:

TOPIC 1: [timestamp]s - [brief description]
TOPIC 2: [timestamp]s - [brief description]
etc.

EXAMPLE:
TOPIC 1: 45s - Discussion of inflation trends and CPI data
TOPIC 2: 128s - Federal Reserve policy implications
TOPIC 3: 267s - Impact on housing market and mortgage rates
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing economic content and identifying key discussion topics."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            return self._parse_topics_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Failed to extract topics: {e}")
            return []
    
    def _parse_topics_response(self, response_text: str) -> List[Dict]:
        """
        Parse topic extraction response from GPT.
        
        Args:
            response_text: GPT response text
            
        Returns:
            List of topic dictionaries
        """
        try:
            topics = []
            
            # Look for TOPIC patterns
            topic_pattern = r'TOPIC\s+\d+:\s*([0-9]+\.?[0-9]*)\s*s\s*-\s*(.+?)(?=\n|$)'
            matches = re.findall(topic_pattern, response_text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                try:
                    timestamp = float(match[0])
                    description = match[1].strip()
                    
                    topics.append({
                        'timestamp': timestamp,
                        'description': description,
                        'topic_id': len(topics) + 1
                    })
                except ValueError:
                    continue
            
            return topics
            
        except Exception as e:
            logger.error(f"Error parsing topics response: {e}")
            return []
