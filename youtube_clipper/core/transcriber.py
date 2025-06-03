"""
Transcriber Module

This module handles video transcription using OpenAI's Whisper API.
Provides methods for transcribing audio to text and generating SRT subtitle files.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict
import srt
from datetime import timedelta
import openai

from ..utils.logger import get_logger, log_execution_time
from ..utils.file_manager import file_manager
from ..exceptions.custom_exceptions import TranscriptionError, ConfigurationError

logger = get_logger(__name__)


class Transcriber:
    """
    Handles video transcription using OpenAI Whisper API.
    
    This class provides methods to transcribe audio to text, generate SRT files,
    and handle various audio/video formats with robust error handling.
    """
    
    def __init__(self, api_key: str, model: str = "whisper-1"):
        """
        Initialize the transcriber with OpenAI credentials.
        
        Args:
            api_key: OpenAI API key
            model: Whisper model to use
            
        Raises:
            ConfigurationError: If API key is invalid or missing
        """
        if not api_key or not api_key.strip():
            raise ConfigurationError("OpenAI API key is required")
            
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
        
        # File size limit for Whisper API (25MB)
        self.max_file_size_mb = 25
        
        logger.info(f"Transcriber initialized with model: {model}")
    
    @log_execution_time
    def transcribe_to_text(self, audio_file_path: str) -> str:
        """
        Transcribe audio/video file to plain text.
        
        Args:
            audio_file_path: Path to audio or video file
            
        Returns:
            Transcribed text
            
        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            audio_path = Path(audio_file_path)
            if not audio_path.exists():
                raise TranscriptionError(f"Audio file not found: {audio_file_path}")
            
            # Check file size
            file_size_mb = file_manager.get_file_size_mb(audio_path)
            if file_size_mb > self.max_file_size_mb:
                raise TranscriptionError(f"File too large ({file_size_mb:.1f}MB). Maximum size: {self.max_file_size_mb}MB")
            
            logger.info(f"Starting transcription of file: {audio_file_path} ({file_size_mb:.1f}MB)")
            
            # Open and transcribe the file
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="text"
                )
            
            if not transcript or not transcript.strip():
                raise TranscriptionError("Transcription returned empty result")
            
            logger.info(f"Transcription completed. Length: {len(transcript)} characters")
            return transcript.strip()
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error during transcription: {e}")
            if "file size" in str(e).lower():
                raise TranscriptionError(f"File too large for Whisper API. Maximum size: {self.max_file_size_mb}MB")
            else:
                raise TranscriptionError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise TranscriptionError(f"Transcription failed: {e}")
    
    @log_execution_time
    def transcribe_with_timestamps(self, audio_file_path: str) -> Dict:
        """
        Transcribe audio/video file with word-level timestamps.
        
        Args:
            audio_file_path: Path to audio or video file
            
        Returns:
            Dictionary with transcription and segment information
            
        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            audio_path = Path(audio_file_path)
            if not audio_path.exists():
                raise TranscriptionError(f"Audio file not found: {audio_file_path}")
            
            # Check file size
            file_size_mb = file_manager.get_file_size_mb(audio_path)
            if file_size_mb > self.max_file_size_mb:
                raise TranscriptionError(f"File too large ({file_size_mb:.1f}MB). Maximum size: {self.max_file_size_mb}MB")
            
            logger.info(f"Starting timestamped transcription of file: {audio_file_path}")
            
            # Open and transcribe the file with timestamps
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            if not transcript or not transcript.text:
                raise TranscriptionError("Transcription returned empty result")
            
            logger.info(f"Timestamped transcription completed. Segments: {len(transcript.segments)}")
            
            return {
                'text': transcript.text,
                'language': transcript.language,
                'duration': transcript.duration,
                'segments': transcript.segments
            }
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error during timestamped transcription: {e}")
            raise TranscriptionError(f"OpenAI API error: {e}")
        except Exception as e:
            logger.error(f"Timestamped transcription failed: {e}")
            raise TranscriptionError(f"Timestamped transcription failed: {e}")
    
    def generate_srt_from_segments(self, segments) -> str:
        """
        Generate SRT subtitle content from transcript segments.
        
        Args:
            segments: List of transcript segments with timestamps
            
        Returns:
            SRT-formatted subtitle content
        """
        try:
            srt_entries = []
            
            for i, segment in enumerate(segments, 1):
                start_time = timedelta(seconds=segment['start'])
                end_time = timedelta(seconds=segment['end'])
                text = segment['text'].strip()
                
                if text:  # Only add non-empty segments
                    srt_entry = srt.Subtitle(
                        index=i,
                        start=start_time,
                        end=end_time,
                        content=text
                    )
                    srt_entries.append(srt_entry)
            
            return srt.compose(srt_entries)
            
        except Exception as e:
            logger.error(f"Failed to generate SRT: {e}")
            raise TranscriptionError(f"Failed to generate SRT: {e}")
    
    def transcribe_both_formats(self, audio_file_path: str) -> Tuple[str, str]:
        """
        Transcribe audio to both plain text and SRT format.
        
        Args:
            audio_file_path: Path to audio or video file
            
        Returns:
            Tuple of (plain_text, srt_content)
            
        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            # Get timestamped transcription
            timestamped_result = self.transcribe_with_timestamps(audio_file_path)
            
            # Extract plain text
            plain_text = timestamped_result['text']
            
            # Generate SRT from segments
            srt_content = self.generate_srt_from_segments(timestamped_result['segments'])
            
            return plain_text, srt_content
            
        except Exception as e:
            logger.error(f"Failed to transcribe both formats: {e}")
            # Fallback to text-only transcription
            try:
                logger.info("Falling back to text-only transcription")
                plain_text = self.transcribe_to_text(audio_file_path)
                return plain_text, ""
            except Exception as fallback_error:
                raise TranscriptionError(f"All transcription methods failed: {fallback_error}")
    
    def save_transcription(self, content: str, output_path: str, format_type: str = "txt") -> None:
        """
        Save transcription content to file.
        
        Args:
            content: Transcription content
            output_path: Output file path
            format_type: Format type ("txt" or "srt")
            
        Raises:
            TranscriptionError: If saving fails
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Transcription saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save transcription: {e}")
            raise TranscriptionError(f"Failed to save transcription: {e}")
    
    def extract_audio_segment(self, video_path: str, start_seconds: float, 
                            end_seconds: float, output_path: str) -> str:
        """
        Extract audio segment from video for targeted transcription.
        
        Args:
            video_path: Path to source video
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            output_path: Output path for extracted audio
            
        Returns:
            Path to extracted audio file
            
        Raises:
            TranscriptionError: If extraction fails
        """
        try:
            import subprocess
            
            # Use ffmpeg to extract audio segment
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_seconds),
                '-t', str(end_seconds - start_seconds),
                '-vn',  # No video
                '-acodec', 'copy',
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise TranscriptionError(f"FFmpeg failed: {result.stderr}")
            
            if not Path(output_path).exists():
                raise TranscriptionError("Audio extraction completed but file not found")
            
            logger.info(f"Audio segment extracted: {output_path}")
            return output_path
            
        except subprocess.SubprocessError as e:
            raise TranscriptionError(f"Audio extraction failed: {e}")
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            raise TranscriptionError(f"Audio extraction error: {e}")
    
    def get_transcription_cost_estimate(self, audio_file_path: str) -> float:
        """
        Estimate the cost of transcribing an audio file.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Estimated cost in USD
        """
        try:
            # Get audio duration (approximation)
            import subprocess
            
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', audio_file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                duration_seconds = float(info['format']['duration'])
                duration_minutes = duration_seconds / 60
                
                # OpenAI Whisper pricing: $0.006 per minute
                estimated_cost = duration_minutes * 0.006
                return estimated_cost
            
            # Fallback estimate based on file size
            file_size_mb = file_manager.get_file_size_mb(Path(audio_file_path))
            estimated_minutes = file_size_mb * 0.5  # Rough estimate
            return estimated_minutes * 0.006
            
        except Exception as e:
            logger.warning(f"Could not estimate transcription cost: {e}")
            return 0.0
    
    def validate_audio_quality(self, audio_file_path: str) -> Dict:
        """
        Validate audio quality for transcription.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Dictionary with quality assessment
        """
        try:
            import subprocess
            
            # Get audio information using ffprobe
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-select_streams', 'a:0', audio_file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                
                if info['streams']:
                    stream = info['streams'][0]
                    
                    return {
                        'sample_rate': int(stream.get('sample_rate', 0)),
                        'channels': int(stream.get('channels', 0)),
                        'bit_rate': int(stream.get('bit_rate', 0)),
                        'codec': stream.get('codec_name', 'unknown'),
                        'duration': float(stream.get('duration', 0)),
                        'quality_score': self._calculate_quality_score(stream)
                    }
            
            return {'quality_score': 0, 'error': 'Could not analyze audio'}
            
        except Exception as e:
            logger.warning(f"Audio quality validation failed: {e}")
            return {'quality_score': 0, 'error': str(e)}
    
    def _calculate_quality_score(self, stream_info: Dict) -> float:
        """
        Calculate a quality score based on audio stream information.
        
        Args:
            stream_info: Audio stream information from ffprobe
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        try:
            sample_rate = int(stream_info.get('sample_rate', 0))
            channels = int(stream_info.get('channels', 0))
            bit_rate = int(stream_info.get('bit_rate', 0))
            
            score = 0.0
            
            # Sample rate score (higher is better, up to 48kHz)
            if sample_rate >= 44100:
                score += 0.4
            elif sample_rate >= 22050:
                score += 0.2
            
            # Channel score (stereo preferred)
            if channels >= 2:
                score += 0.3
            elif channels == 1:
                score += 0.2
            
            # Bit rate score (higher is better, up to 320kbps)
            if bit_rate >= 128000:
                score += 0.3
            elif bit_rate >= 64000:
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception:
            return 0.0
