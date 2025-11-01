# FFmpeg Installation Guide for PiCMS

## Why FFmpeg?

PiCMS uses FFmpeg for:
- **Video metadata extraction** (duration, resolution, codec, bitrate)
- **Thumbnail generation** from video files
- **Video quality analysis**

Without FFmpeg, videos will still upload and work, but won't have thumbnails or detailed metadata.

## Installation

### Windows

**Option 1: Winget (Recommended for Windows 11)**
```powershell
winget install FFmpeg
```

**Option 2: Chocolatey**
```powershell
choco install ffmpeg
```

**Option 3: Manual Installation**
1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your PATH:
   - Right-click "This PC" → Properties
   - Advanced system settings → Environment Variables
   - Edit "Path" → New → Add `C:\ffmpeg\bin`
4. Restart PowerShell/Command Prompt

### macOS

```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ffmpeg
```

### Raspberry Pi (Raspbian)

```bash
sudo apt update
sudo apt install ffmpeg
```

## Verify Installation

After installation, verify FFmpeg is working:

```bash
ffmpeg -version
ffprobe -version
```

You should see version information displayed.

## Test in PiCMS

1. Restart your PiCMS application
2. Upload a test video
3. Check if thumbnail appears and metadata is displayed (resolution, duration, codec)

## Troubleshooting

### "ffmpeg not found" error
- Ensure FFmpeg is in your system PATH
- Restart your terminal/command prompt after installation
- Try running `where ffmpeg` (Windows) or `which ffmpeg` (Linux/Mac)

### Thumbnail generation fails
- Check video file is not corrupted
- Ensure enough disk space in `static/thumbnails/`
- Check logs in `logs/app.log` for detailed error messages

### Slow metadata extraction
- This is normal for large video files
- Consider using async processing for production (Celery)
- Metadata extraction happens once during upload

## Performance Tips

For large video files (>1GB):
1. **Increase timeout**: Edit `utils/video_utils.py`, increase `timeout=30` to higher value
2. **Use faster preset**: Thumbnails use default quality, can be adjusted
3. **Consider async processing**: Implement background tasks with Celery (future enhancement)

## Alternative: Disable FFmpeg Features

If you can't install FFmpeg, the application will still work:
- Videos upload normally
- No thumbnails generated (shows placeholder icon)
- Basic metadata only (file size, upload date)
- No video duration or resolution info

The application gracefully degrades without FFmpeg.
