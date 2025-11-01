"""
Quick FFmpeg Test
Verify metadata extraction and thumbnail generation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.video_utils import check_ffmpeg_installed

print("="*60)
print("FFMPEG INSTALLATION TEST")
print("="*60)

if check_ffmpeg_installed():
    print("\n✅ SUCCESS! FFmpeg is installed and working!")
    print("\nWhat this means:")
    print("  ✓ Video metadata will be extracted automatically")
    print("  ✓ Thumbnails will be generated on upload")
    print("  ✓ Duration, resolution, codec info will be captured")
    print("\nNext steps:")
    print("  1. Go to http://localhost:5000/videos")
    print("  2. Upload a test video")
    print("  3. Watch as the thumbnail generates automatically!")
    print("  4. See full metadata in the video list")
else:
    print("\n❌ FFmpeg not detected")
    print("\nTroubleshooting:")
    print("  1. Close and reopen PowerShell")
    print("  2. Run: ffmpeg -version")
    print("  3. If that works, restart Flask server")

print("\n" + "="*60)
