"""
Video Downloader Module

This module handles downloading YouTube videos using pytube library.
Provides methods for downloading videos in various formats and qualities.
"""

import os
from typing import Optional, Dict, List
from pathlib import Path
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, RegexMatchError

from ..utils.logger import get_logger, log_execution_time
from ..utils.file_manager import file_manager
from ..utils.validators import validate_youtube_input
from ..exceptions.custom_exceptions import VideoDownloadError, ValidationError

logger = get_logger(__name__)


class VideoDownloader:
    """
    Handles YouTube video download operations using pytube.
    
    This class provides methods to download videos in different qualities
    and formats, with robust error handling and progress tracking.
    """
    
    def __init__(self, download_dir: str = "downloads"):
        """
        Initialize the video downloader.
        
        Args:
            download_dir: Directory to store downloaded videos
        """
        self.download_dir = Path(download_dir)
        file_manager.ensure_directory(self.download_dir)
        
    @log_execution_time
    def download_video(self, url: str, video_id: str, 
                      quality: str = "highest", 
                      format_type: str = "progressive") -> Optional[str]:
        """
        Download a YouTube video.
        
        Args:
            url: YouTube video URL
            video_id: Video ID for filename
            quality: Quality preference ("highest", "lowest", or specific resolution)
            format_type: Stream type ("progressive", "adaptive", "audio_only")
            
        Returns:
            Path to downloaded video file or None if failed
            
        Raises:
            VideoDownloadError: If download fails
            ValidationError: If URL is invalid
        """
        try:
            # Validate URL
            url_info = validate_youtube_input(url)
            actual_video_id = url_info['video_id']
            
            logger.info(f"Starting download for video: {actual_video_id}")
            
            # Create YouTube object
            yt = YouTube(url, on_progress_callback=self._progress_callback)
            
            # Log video information
            logger.info(f"Video title: {yt.title}")
            logger.info(f"Video length: {yt.length} seconds")
            logger.info(f"Video views: {yt.views}")
            
            # Get appropriate stream
            stream = self._select_stream(yt, quality, format_type)
            if not stream:
                raise VideoDownloadError("No suitable video stream found")
            
            logger.info(f"Selected stream: {stream.resolution or 'audio'} - {stream.mime_type}")
            
            # Generate filename
            safe_title = file_manager.get_safe_filename(yt.title)
            if format_type == "audio_only":
                filename = f"{video_id}_{safe_title}.{stream.subtype}"
            else:
                filename = f"{video_id}_{safe_title}.{stream.subtype}"
            
            filepath = self.download_dir / filename
            
            # Download the stream
            logger.info(f"Downloading to: {filepath}")
            stream.download(output_path=str(self.download_dir), filename=filename)
            
            # Verify download
            if not filepath.exists():
                raise VideoDownloadError("Download completed but file not found")
            
            file_size_mb = file_manager.get_file_size_mb(filepath)
            logger.info(f"Download completed successfully. File size: {file_size_mb:.2f} MB")
            
            return str(filepath)
            
        except VideoUnavailable as e:
            logger.error(f"Video is unavailable: {e}")
            raise VideoDownloadError(f"Video is unavailable: {e}")
        except RegexMatchError as e:
            logger.error(f"Invalid YouTube URL: {e}")
            raise ValidationError(f"Invalid YouTube URL: {e}")
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise VideoDownloadError(f"Download failed: {e}")
    
    def _select_stream(self, yt: YouTube, quality: str, format_type: str):
        """
        Select the best stream based on quality and format preferences.
        
        Args:
            yt: YouTube object
            quality: Quality preference
            format_type: Format type preference
            
        Returns:
            Selected stream object or None
        """
        try:
            if format_type == "audio_only":
                # Get audio-only stream
                streams = yt.streams.filter(only_audio=True)
                if streams:
                    return streams.order_by('abr').desc().first()
                return None
            
            elif format_type == "progressive":
                # Progressive streams (video + audio combined)
                streams = yt.streams.filter(progressive=True, file_extension='mp4')
                
                if quality == "highest":
                    return streams.order_by('resolution').desc().first()
                elif quality == "lowest":
                    return streams.order_by('resolution').asc().first()
                else:
                    # Try to match specific resolution
                    specific_stream = streams.filter(res=quality).first()
                    if specific_stream:
                        return specific_stream
                    # Fallback to highest if specific resolution not found
                    return streams.order_by('resolution').desc().first()
            
            elif format_type == "adaptive":
                # Adaptive streams (video only, higher quality available)
                video_streams = yt.streams.filter(adaptive=True, only_video=True, file_extension='mp4')
                
                if quality == "highest":
                    return video_streams.order_by('resolution').desc().first()
                elif quality == "lowest":
                    return video_streams.order_by('resolution').asc().first()
                else:
                    specific_stream = video_streams.filter(res=quality).first()
                    if specific_stream:
                        return specific_stream
                    return video_streams.order_by('resolution').desc().first()
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting stream: {e}")
            return None
    
    def _progress_callback(self, stream, chunk, bytes_remaining):
        """
        Callback function for download progress.
        
        Args:
            stream: The stream being downloaded
            chunk: Chunk of data downloaded
            bytes_remaining: Bytes remaining to download
        """
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = (bytes_downloaded / total_size) * 100
        
        # Log progress every 10%
        if int(percentage) % 10 == 0 and int(percentage) != getattr(self, '_last_logged_progress', -1):
            logger.info(f"Download progress: {percentage:.1f}%")
            self._last_logged_progress = int(percentage)
    
    def get_available_streams(self, url: str) -> Dict[str, List[Dict]]:
        """
        Get information about available streams for a video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with stream information categorized by type
            
        Raises:
            VideoDownloadError: If unable to fetch stream information
        """
        try:
            validate_youtube_input(url)
            yt = YouTube(url)
            
            result = {
                'progressive': [],
                'adaptive_video': [],
                'audio_only': []
            }
            
            # Progressive streams
            for stream in yt.streams.filter(progressive=True):
                result['progressive'].append({
                    'itag': stream.itag,
                    'resolution': stream.resolution,
                    'fps': stream.fps,
                    'mime_type': stream.mime_type,
                    'filesize_mb': round(stream.filesize / (1024 * 1024), 2) if stream.filesize else None
                })
            
            # Adaptive video streams
            for stream in yt.streams.filter(adaptive=True, only_video=True):
                result['adaptive_video'].append({
                    'itag': stream.itag,
                    'resolution': stream.resolution,
                    'fps': stream.fps,
                    'mime_type': stream.mime_type,
                    'filesize_mb': round(stream.filesize / (1024 * 1024), 2) if stream.filesize else None
                })
            
            # Audio-only streams
            for stream in yt.streams.filter(only_audio=True):
                result['audio_only'].append({
                    'itag': stream.itag,
                    'abr': stream.abr,
                    'mime_type': stream.mime_type,
                    'filesize_mb': round(stream.filesize / (1024 * 1024), 2) if stream.filesize else None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get stream information: {e}")
            raise VideoDownloadError(f"Failed to get stream information: {e}")
    
    def download_for_transcription(self, url: str, video_id: str) -> Optional[str]:
        """
        Download video optimized for transcription (audio quality priority).
        
        Args:
            url: YouTube video URL
            video_id: Video ID for filename
            
        Returns:
            Path to downloaded video file
        """
        try:
            # First try progressive (easier for transcription)
            filepath = self.download_video(url, video_id, quality="highest", format_type="progressive")
            
            if filepath:
                return filepath
            
            # Fallback to adaptive if progressive fails
            logger.info("Progressive download failed, trying adaptive...")
            return self.download_video(url, video_id, quality="720p", format_type="adaptive")
            
        except Exception as e:
            logger.error(f"Optimized download failed: {e}")
            raise VideoDownloadError(f"Optimized download failed: {e}")
    
    def estimate_download_time(self, url: str, connection_speed_mbps: float = 10.0) -> Optional[float]:
        """
        Estimate download time based on video size and connection speed.
        
        Args:
            url: YouTube video URL
            connection_speed_mbps: Connection speed in Mbps
            
        Returns:
            Estimated download time in seconds, or None if cannot estimate
        """
        try:
            validate_youtube_input(url)
            yt = YouTube(url)
            
            # Get the highest quality progressive stream
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if stream and stream.filesize:
                filesize_mb = stream.filesize / (1024 * 1024)
                download_time_seconds = (filesize_mb * 8) / connection_speed_mbps  # Convert to bits and divide by speed
                return download_time_seconds
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not estimate download time: {e}")
            return None
    
    def cleanup_old_downloads(self, max_age_days: int = 1) -> int:
        """
        Clean up old downloaded videos.
        
        Args:
            max_age_days: Maximum age in days for downloaded files
            
        Returns:
            Number of files removed
        """
        return file_manager.cleanup_old_files(self.download_dir, max_age_days)
    
    def get_video_info(self, url: str) -> Dict:
        """
        Get basic video information without downloading.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video information
        """
        try:
            validate_youtube_input(url)
            yt = YouTube(url)
            
            return {
                'title': yt.title,
                'length_seconds': yt.length,
                'views': yt.views,
                'author': yt.author,
                'description': yt.description[:500] + "..." if len(yt.description) > 500 else yt.description,
                'publish_date': yt.publish_date.isoformat() if yt.publish_date else None,
                'thumbnail_url': yt.thumbnail_url
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise VideoDownloadError(f"Failed to get video info: {e}")
