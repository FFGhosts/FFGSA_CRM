"""
Video Utilities Module
Provides video processing functions: metadata extraction, thumbnail generation, etc.
"""
import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    pass


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg and ffprobe are installed"""
    try:
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_video_metadata(video_path: str) -> Dict[str, any]:
    """
    Extract comprehensive metadata from video file using ffprobe
    
    Args:
        video_path: Absolute path to the video file
        
    Returns:
        Dictionary containing video metadata:
        {
            'duration': int (seconds),
            'width': int,
            'height': int,
            'codec': str,
            'bitrate': int (kbps),
            'framerate': float,
            'format': str,
            'size': int (bytes)
        }
        
    Raises:
        VideoProcessingError: If metadata extraction fails
    """
    if not os.path.exists(video_path):
        raise VideoProcessingError(f"Video file not found: {video_path}")
    
    if not check_ffmpeg_installed():
        logger.warning("ffmpeg/ffprobe not installed. Returning basic metadata.")
        return _get_basic_metadata(video_path)
    
    try:
        # Run ffprobe to get video information
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            '-select_streams', 'v:0',  # Select first video stream
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        
        data = json.loads(result.stdout)
        
        # Extract format info
        format_info = data.get('format', {})
        
        # Extract video stream info
        streams = data.get('streams', [])
        if not streams:
            raise VideoProcessingError("No video stream found in file")
        
        video_stream = streams[0]
        
        # Parse metadata
        metadata = {
            'duration': int(float(format_info.get('duration', 0))),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'codec': video_stream.get('codec_name', 'unknown'),
            'bitrate': int(format_info.get('bit_rate', 0)) // 1000,  # Convert to kbps
            'framerate': _parse_framerate(video_stream.get('r_frame_rate', '0/0')),
            'format': format_info.get('format_name', 'unknown'),
            'size': int(format_info.get('size', os.path.getsize(video_path)))
        }
        
        logger.info(f"Extracted metadata for {Path(video_path).name}: "
                   f"{metadata['width']}x{metadata['height']}, "
                   f"{metadata['duration']}s, {metadata['codec']}")
        
        return metadata
        
    except subprocess.TimeoutExpired:
        raise VideoProcessingError("Metadata extraction timed out")
    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(f"ffprobe error: {e.stderr}")
    except json.JSONDecodeError:
        raise VideoProcessingError("Failed to parse ffprobe output")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error: {str(e)}")


def _parse_framerate(framerate_str: str) -> float:
    """Parse framerate from fraction string (e.g., '30000/1001')"""
    try:
        if '/' in framerate_str:
            num, denom = framerate_str.split('/')
            return round(float(num) / float(denom), 2)
        return float(framerate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _get_basic_metadata(video_path: str) -> Dict[str, any]:
    """Get basic metadata when ffprobe is not available"""
    return {
        'duration': 0,
        'width': 0,
        'height': 0,
        'codec': 'unknown',
        'bitrate': 0,
        'framerate': 0.0,
        'format': os.path.splitext(video_path)[1][1:],  # File extension
        'size': os.path.getsize(video_path)
    }


def generate_thumbnail(video_path: str, output_path: str, timestamp: str = '00:00:01', 
                      width: int = 320, height: int = 180) -> bool:
    """
    Generate thumbnail image from video at specified timestamp
    
    Args:
        video_path: Path to source video
        output_path: Path for output thumbnail (e.g., 'thumb.jpg')
        timestamp: Time position for thumbnail (format: HH:MM:SS)
        width: Thumbnail width in pixels
        height: Thumbnail height in pixels
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        VideoProcessingError: If thumbnail generation fails
    """
    if not os.path.exists(video_path):
        raise VideoProcessingError(f"Video file not found: {video_path}")
    
    if not check_ffmpeg_installed():
        logger.warning("ffmpeg not installed. Cannot generate thumbnail.")
        return False
    
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate thumbnail using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', timestamp,  # Seek to timestamp
            '-i', video_path,  # Input file
            '-vframes', '1',   # Extract 1 frame
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
            '-y',              # Overwrite output file
            output_path
        ]
        
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=30
        )
        
        logger.info(f"Generated thumbnail: {Path(output_path).name}")
        return True
        
    except subprocess.TimeoutExpired:
        raise VideoProcessingError("Thumbnail generation timed out")
    except subprocess.CalledProcessError as e:
        raise VideoProcessingError(f"ffmpeg error: {e.stderr.decode()}")
    except Exception as e:
        raise VideoProcessingError(f"Unexpected error: {str(e)}")


def delete_thumbnail(thumbnail_path: str) -> bool:
    """
    Delete thumbnail file
    
    Args:
        thumbnail_path: Path to thumbnail file
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            logger.info(f"Deleted thumbnail: {Path(thumbnail_path).name}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting thumbnail: {e}")
        return False


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., '1h 23m', '45m 30s', '12s')
    """
    if seconds == 0:
        return '0s'
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f'{hours}h')
    if minutes > 0:
        parts.append(f'{minutes}m')
    if secs > 0 and hours == 0:  # Only show seconds if less than 1 hour
        parts.append(f'{secs}s')
    
    return ' '.join(parts) if parts else '0s'


def format_resolution(width: int, height: int) -> str:
    """
    Format video resolution to standard name
    
    Args:
        width: Video width in pixels
        height: Video height in pixels
        
    Returns:
        Resolution name (e.g., '1080p', '720p', '480p', or custom)
    """
    if width == 0 or height == 0:
        return 'Unknown'
    
    # Common resolution names
    resolutions = {
        (3840, 2160): '4K (2160p)',
        (2560, 1440): '1440p',
        (1920, 1080): '1080p (Full HD)',
        (1280, 720): '720p (HD)',
        (854, 480): '480p',
        (640, 360): '360p',
        (426, 240): '240p'
    }
    
    # Check for exact match
    if (width, height) in resolutions:
        return resolutions[(width, height)]
    
    # Return custom resolution
    return f'{width}x{height}'


def format_bitrate(bitrate_kbps: int) -> str:
    """
    Format bitrate to human-readable string
    
    Args:
        bitrate_kbps: Bitrate in kilobits per second
        
    Returns:
        Formatted string (e.g., '5.2 Mbps', '850 kbps')
    """
    if bitrate_kbps == 0:
        return '0 kbps'
    
    if bitrate_kbps >= 1000:
        mbps = bitrate_kbps / 1000
        return f'{mbps:.1f} Mbps'
    
    return f'{bitrate_kbps} kbps'


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA256 checksum of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    import hashlib
    
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f'Error calculating checksum for {file_path}: {e}')
        raise VideoProcessingError(f'Failed to calculate checksum: {e}')


def verify_checksum(file_path: str, expected_checksum: str) -> bool:
    """
    Verify file checksum matches expected value
    
    Args:
        file_path: Path to the file
        expected_checksum: Expected SHA256 hash
        
    Returns:
        True if checksums match, False otherwise
    """
    try:
        actual_checksum = calculate_checksum(file_path)
        return actual_checksum.lower() == expected_checksum.lower()
    except Exception as e:
        logger.error(f'Error verifying checksum for {file_path}: {e}')
        return False


def get_thumbnail_path(video_filename: str, thumbnail_folder: str) -> str:
    """
    Get thumbnail path for a video file
    
    Args:
        video_filename: Original video filename
        thumbnail_folder: Base thumbnail directory
        
    Returns:
        Full path to thumbnail file
    """
    name_without_ext = os.path.splitext(video_filename)[0]
    return os.path.join(thumbnail_folder, f"{name_without_ext}.jpg")
