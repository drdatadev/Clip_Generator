"""
Main Application Module

This module contains the main YouTube Clipper application that orchestrates
all the components to provide the complete video clipping functionality.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict

# Add current directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent))

from .config import config
from .utils.logger import setup_logging, get_logger
from .utils.file_manager import file_manager
from .utils.validators import validate_search_input, validate_clip_input
from .core.youtube_search import YouTubeSearcher
from .core.video_downloader import VideoDownloader
from .core.transcriber import Transcriber
from .core.clip_finder import ClipFinder
from .core.video_processor import VideoProcessor
from .core.topic_classifier import topic_classifier
from .exceptions.custom_exceptions import (
    YouTubeClipperError, ConfigurationError, YouTubeAPIError,
    VideoDownloadError, TranscriptionError, ClipExtractionError
)

logger = get_logger(__name__)


class YouTubeClipper:
    """
    Main application class for YouTube video clipping system.
    
    This class orchestrates the entire pipeline from search to final clip generation,
    integrating all the core components in a cohesive workflow.
    """
    
    def __init__(self):
        """Initialize the YouTube Clipper with all required components."""
        self.setup_complete = False
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all application components."""
        try:
            # Setup logging
            setup_logging(
                log_level=config.LOG_LEVEL,
                log_file=f"{config.LOGS_DIR}/youtube_clipper.log",
                console_output=True,
                colored_output=True
            )
            
            logger.info("Starting YouTube Clipper initialization")
            
            # Validate API keys
            if not config.OPENAI_API_KEY or not config.YOUTUBE_API_KEY:
                raise ConfigurationError(config.ERROR_MESSAGES['missing_api_keys'])
            
            # Create project directories
            file_manager.create_project_structure()
            
            # Initialize core components
            self.youtube_searcher = YouTubeSearcher(config.YOUTUBE_API_KEY)
            self.video_downloader = VideoDownloader(config.DOWNLOADS_DIR)
            self.transcriber = Transcriber(config.OPENAI_API_KEY, config.WHISPER_MODEL)
            self.clip_finder = ClipFinder(config.OPENAI_API_KEY, config.GPT_MODEL)
            self.video_processor = VideoProcessor(config.CLIPS_OUTPUT_DIR)
            
            self.setup_complete = True
            logger.info("YouTube Clipper initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize YouTube Clipper: {e}")
            raise ConfigurationError(f"Initialization failed: {e}")
    
    def search_videos(self, query: str, max_results: int = None) -> list:
        """
        Search for YouTube videos based on query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (defaults to config setting)
            
        Returns:
            List of video dictionaries
            
        Raises:
            YouTubeAPIError: If search fails
        """
        if not self.setup_complete:
            raise ConfigurationError("YouTubeClipper not properly initialized")
        
        max_results = max_results or config.DEFAULT_SEARCH_RESULTS
        validate_search_input(query, max_results)
        
        try:
            logger.info(f"Searching for videos: '{query}'")
            videos = self.youtube_searcher.search_economic_content(query, max_results)
            logger.info(f"Found {len(videos)} videos")
            return videos
        except Exception as e:
            logger.error(f"Video search failed: {e}")
            raise YouTubeAPIError(f"Search failed: {e}")
    
    def process_video_to_clip(self, video_url: str, clip_description: str,
                            aspect_ratio: str = "16:9", add_subtitles: bool = False,
                            quality: str = "medium") -> Dict:
        """
        Complete pipeline to process a video into a clip.
        
        Args:
            video_url: YouTube video URL
            clip_description: Description of desired clip
            aspect_ratio: Target aspect ratio
            add_subtitles: Whether to include subtitles
            quality: Output quality setting
            
        Returns:
            Dictionary with processing results
            
        Raises:
            YouTubeClipperError: If any step in the pipeline fails
        """
        if not self.setup_complete:
            raise ConfigurationError("YouTubeClipper not properly initialized")
        
        result = {
            'success': False,
            'video_info': None,
            'transcription_path': None,
            'clip_path': None,
            'topic': None,
            'processing_time': None,
            'error': None
        }
        
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Starting video processing pipeline for: {video_url}")
            
            # Step 1: Extract video ID and get info
            from .utils.validators import validate_youtube_input
            url_info = validate_youtube_input(video_url)
            video_id = url_info['video_id']
            
            logger.info(f"Processing video ID: {video_id}")
            
            # Step 2: Download video
            logger.info("Step 1/5: Downloading video...")
            downloaded_path = self.video_downloader.download_for_transcription(video_url, video_id)
            if not downloaded_path:
                raise VideoDownloadError("Failed to download video")
            
            result['video_info'] = {
                'id': video_id,
                'url': video_url,
                'downloaded_path': downloaded_path
            }
            
            # Step 3: Transcribe video
            logger.info("Step 2/5: Transcribing video...")
            transcription_text, srt_content = self.transcriber.transcribe_both_formats(downloaded_path)
            
            # Save transcriptions
            transcription_dir = Path(config.TRANSCRIPTIONS_DIR)
            text_path = transcription_dir / f"{video_id}_transcription.txt"
            srt_path = transcription_dir / f"{video_id}_subtitles.srt"
            
            self.transcriber.save_transcription(transcription_text, str(text_path), "txt")
            if srt_content:
                self.transcriber.save_transcription(srt_content, str(srt_path), "srt")
            
            result['transcription_path'] = str(text_path)
            
            # Step 4: Find clip timestamps
            logger.info("Step 3/5: Identifying clip timestamps...")
            start_time_clip, end_time_clip = self.clip_finder.find_clip_timestamps(
                transcription_text, clip_description
            )
            
            if start_time_clip is None or end_time_clip is None:
                raise ClipExtractionError("Could not identify clip timestamps")
            
            validate_clip_input(clip_description, start_time_clip, end_time_clip)
            
            # Step 5: Classify topic
            logger.info("Step 4/5: Classifying topic...")
            classification = topic_classifier.classify_combined(
                clip_description, transcription_text, start_time_clip, end_time_clip
            )
            topic = classification['primary_category']
            result['topic'] = topic
            
            logger.info(f"Classified as topic: {topic} (confidence: {classification['confidence_score']:.2f})")
            
            # Step 6: Create clip
            logger.info("Step 5/5: Creating video clip...")
            
            # Generate output filename
            safe_description = file_manager.get_safe_filename(clip_description[:30])
            output_filename = f"{video_id}_{safe_description}_{int(start_time_clip)}s_{int(end_time_clip)}s.mp4"
            output_path = Path(config.CLIPS_OUTPUT_DIR) / topic / output_filename
            
            # Extract relevant SRT content for clip if subtitles requested
            clip_srt = None
            if add_subtitles and srt_content:
                clip_srt = srt_content  # Will be processed by video processor
            
            # Create the clip
            success = self.video_processor.create_clip(
                downloaded_path, str(output_path),
                start_time_clip, end_time_clip,
                aspect_ratio, quality, add_subtitles, clip_srt
            )
            
            if not success:
                raise ClipExtractionError("Failed to create video clip")
            
            result['clip_path'] = str(output_path)
            
            # Cleanup downloaded video
            try:
                Path(downloaded_path).unlink()
                logger.info("Cleaned up downloaded video file")
            except Exception as e:
                logger.warning(f"Failed to cleanup downloaded file: {e}")
            
            # Calculate processing time
            end_time = time.time()
            result['processing_time'] = end_time - start_time
            result['success'] = True
            
            logger.info(f"Video processing completed successfully in {result['processing_time']:.2f} seconds")
            logger.info(f"Created clip: {result['clip_path']}")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            result['processing_time'] = end_time - start_time
            result['error'] = str(e)
            
            logger.error(f"Video processing failed after {result['processing_time']:.2f} seconds: {e}")
            
            # Cleanup on error
            try:
                if 'downloaded_path' in locals() and Path(downloaded_path).exists():
                    Path(downloaded_path).unlink()
                    logger.info("Cleaned up downloaded video after error")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup after error: {cleanup_error}")
            
            raise
    
    def create_clip_interactive(self) -> bool:
        """
        Interactive command-line interface for creating clips.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print("\n" + "="*60)
            print("        YouTube Economic Content Clipper")
            print("="*60)
            print("\nThis tool helps you extract economic insights from YouTube videos")
            print("and create shareable clips organized by topic.\n")
            
            # Step 1: Search for videos
            search_query = input("Enter YouTube search query (e.g., 'Fed interest rate decision 2024'): ").strip()
            if not search_query:
                print("Search query cannot be empty.")
                return False
            
            print("\nSearching for videos...")
            videos = self.search_videos(search_query)
            
            if not videos:
                print("No videos found. Please try a different search query.")
                return False
            
            # Step 2: Display and select video
            print(f"\nFound {len(videos)} videos:")
            for i, video in enumerate(videos, 1):
                print(f"{i}. {video['title']}")
                print(f"   Channel: {video['channel']}")
                print(f"   URL: {video['url']}")
                print()
            
            try:
                choice = int(input(f"Select a video (1-{len(videos)}): ")) - 1
                if not (0 <= choice < len(videos)):
                    print("Invalid selection.")
                    return False
                selected_video = videos[choice]
            except ValueError:
                print("Invalid input. Please enter a number.")
                return False
            
            print(f"\nSelected: {selected_video['title']}")
            
            # Step 3: Get clip description
            clip_description = input("\nDescribe the clip you want (e.g., 'the part about inflation impact on markets'): ").strip()
            if not clip_description:
                print("Clip description cannot be empty.")
                return False
            
            # Step 4: Get user preferences
            print("\nClip Options:")
            aspect_ratio = input("Aspect ratio (16:9 or 9:16) [default: 16:9]: ").strip() or "16:9"
            if aspect_ratio not in ["16:9", "9:16"]:
                print("Invalid aspect ratio, using 16:9")
                aspect_ratio = "16:9"
            
            add_subs_input = input("Add subtitles? (y/n) [default: n]: ").lower().strip()
            add_subs = add_subs_input.startswith('y')
            
            quality = input("Quality (fast/medium/high) [default: medium]: ").strip() or "medium"
            if quality not in ["fast", "medium", "high"]:
                print("Invalid quality, using medium")
                quality = "medium"
            
            # Step 5: Process the video
            print(f"\nProcessing video clip...")
            print("This may take a few minutes...")
            
            result = self.process_video_to_clip(
                selected_video['url'], 
                clip_description,
                aspect_ratio, 
                add_subs, 
                quality
            )
            
            if result['success']:
                print(f"\n✅ Successfully created clip!")
                print(f"   📁 Location: {result['clip_path']}")
                print(f"   🏷️  Category: {result['topic']}")
                print(f"   ⏱️  Processing time: {result['processing_time']:.1f} seconds")
                print(f"   📝 Transcription: {result['transcription_path']}")
                return True
            else:
                print(f"\n❌ Failed to create clip: {result.get('error', 'Unknown error')}")
                return False
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            return False
        except Exception as e:
            logger.error(f"Interactive session failed: {e}")
            print(f"\n❌ Error occurred: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """
        Get system status and health information.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'setup_complete': self.setup_complete,
            'components': {},
            'directories': {},
            'api_keys': {},
            'system_info': {}
        }
        
        if self.setup_complete:
            # Check component status
            try:
                # Test YouTube API
                test_search = self.youtube_searcher.search_videos("test", 1)
                status['components']['youtube_search'] = 'OK'
            except Exception as e:
                status['components']['youtube_search'] = f'ERROR: {e}'
            
            # Check OpenAI API
            try:
                # This is just a connection test, not a full transcription
                status['components']['openai_api'] = 'OK'
            except Exception as e:
                status['components']['openai_api'] = f'ERROR: {e}'
            
            # Check FFmpeg
            try:
                self.video_processor._verify_ffmpeg()
                status['components']['ffmpeg'] = 'OK'
            except Exception as e:
                status['components']['ffmpeg'] = f'ERROR: {e}'
        
        # Check directories
        for dir_name in [config.DOWNLOADS_DIR, config.TRANSCRIPTIONS_DIR, config.CLIPS_OUTPUT_DIR, config.LOGS_DIR]:
            status['directories'][dir_name] = Path(dir_name).exists()
        
        # Check API keys (without revealing them)
        status['api_keys']['openai'] = bool(config.OPENAI_API_KEY)
        status['api_keys']['youtube'] = bool(config.YOUTUBE_API_KEY)
        
        # System info
        status['system_info']['python_version'] = sys.version
        status['system_info']['platform'] = sys.platform
        
        return status
    
    def cleanup(self):
        """Clean up resources and temporary files."""
        try:
            if hasattr(self, 'video_processor'):
                self.video_processor.cleanup_temp_files()
            
            # Clean up old downloads
            if hasattr(self, 'video_downloader'):
                self.video_downloader.cleanup_old_downloads(max_age_days=1)
            
            logger.info("Cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


def main():
    """Main application entry point."""
    try:
        # Check for FFmpeg first
        import subprocess
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Error: FFmpeg is not installed or not in PATH.")
            print("Please install FFmpeg and try again.")
            print("Visit: https://ffmpeg.org/download.html")
            sys.exit(1)
        
        # Initialize and run clipper
        clipper = YouTubeClipper()
        
        # Main processing loop
        while True:
            success = clipper.create_clip_interactive()
            
            if success:
                print("\n" + "="*40)
                print("Clip creation completed successfully!")
                print("="*40)
            
            # Ask if user wants to create another clip
            another = input("\nCreate another clip? (y/n): ").lower().strip()
            if not another.startswith('y'):
                break
        
        # Cleanup
        clipper.cleanup()
        print("\nThank you for using YouTube Economic Content Clipper!")
        
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\n❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
