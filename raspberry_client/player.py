#!/usr/bin/env python3
"""
PiCMS Video Player Client for Raspberry Pi
Connects to PiCMS server, downloads assigned videos, and plays them in fullscreen loop
"""

import os
import sys
import json
import time
import logging
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import requests

# Configuration - Auto-detect installation directory
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(INSTALL_DIR, 'config.json')
VIDEOS_DIR = os.path.join(INSTALL_DIR, 'videos')
LOG_FILE = os.path.join(INSTALL_DIR, 'logs', 'player.log')
HEARTBEAT_INTERVAL = 60  # seconds
SYNC_INTERVAL = 300  # 5 minutes
SCHEDULE_CHECK_INTERVAL = 60  # Check for schedule changes every minute (Phase 5)
CONFIG_CHECK_INTERVAL = 30  # Check for config updates (Phase 7)
EMERGENCY_CHECK_INTERVAL = 10  # Check for emergency broadcasts (Phase 7)
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PiCMSPlayer:
    """Main player class for PiCMS client"""
    
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()
        self.videos_dir = Path(VIDEOS_DIR)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        self.server_url = self.config.get('server_url')
        self.device_id = self.config.get('device_id')
        self.api_key = self.config.get('api_key')
        
        self.current_video = None
        self.assigned_videos = []
        self.player_process = None
        self.current_schedule = None  # Phase 5: Track active schedule
        self.last_schedule_check = 0  # Phase 5: Last time we checked for schedule
        self.emergency_mode = False  # Phase 7: Emergency broadcast mode
        self.current_emergency = None  # Phase 7: Active emergency broadcast
        self.display_settings = {}  # Phase 7: Display configuration
        self.audio_settings = {}  # Phase 7: Audio configuration
        
        logger.info('PiCMS Player initialized')
        logger.info(f'Server: {self.server_url}')
        logger.info(f'Device ID: {self.device_id}')
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.info('Configuration loaded successfully')
            return config
        except FileNotFoundError:
            logger.error(f'Config file not found: {self.config_file}')
            logger.info('Creating default config file...')
            
            # Create default config
            default_config = {
                'server_url': 'http://192.168.0.100:5000',
                'device_id': None,
                'api_key': None,
                'device_name': self.get_device_name(),
                'serial': self.get_serial_number()
            }
            
            self.save_config(default_config)
            return default_config
        except json.JSONDecodeError as e:
            logger.error(f'Invalid JSON in config file: {e}')
            sys.exit(1)
    
    def save_config(self, config):
        """Save configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info('Configuration saved')
        except Exception as e:
            logger.error(f'Failed to save config: {e}')
    
    def get_device_name(self):
        """Get device hostname as device name"""
        try:
            with open('/etc/hostname', 'r') as f:
                return f.read().strip()
        except:
            return 'RaspberryPi'
    
    def get_serial_number(self):
        """Get Raspberry Pi serial number"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except:
            pass
        
        # Fallback: generate from MAC address
        try:
            result = subprocess.run(['cat', '/sys/class/net/eth0/address'], 
                                  capture_output=True, text=True)
            mac = result.stdout.strip().replace(':', '')
            return f'RPI-{mac.upper()}'
        except:
            return f'RPI-{os.urandom(4).hex().upper()}'
    
    def register_device(self):
        """Register device with CMS server"""
        logger.info('Registering device with server...')
        
        try:
            data = {
                'name': self.config.get('device_name', self.get_device_name()),
                'serial': self.config.get('serial', self.get_serial_number()),
                'ip_address': self.get_local_ip()
            }
            
            response = requests.post(
                f'{self.server_url}/api/device/register',
                json=data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f'Device registered: {result.get("message")}')
                
                # Save device_id and api_key if provided
                if 'device_id' in result:
                    self.config['device_id'] = result['device_id']
                    self.device_id = result['device_id']
                
                if 'api_key' in result:
                    self.config['api_key'] = result['api_key']
                    self.api_key = result['api_key']
                    logger.info('Received new API key')
                
                self.save_config(self.config)
                return True
            else:
                logger.error(f'Registration failed: {response.status_code} - {response.text}')
                return False
        
        except Exception as e:
            logger.error(f'Registration error: {e}')
            return False
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            ip = result.stdout.strip().split()[0]
            return ip
        except:
            return '0.0.0.0'
    
    def get_headers(self):
        """Get API request headers"""
        return {'X-Device-Key': self.api_key}
    
    def get_active_schedule(self):
        """Get currently active schedule from server (Phase 5)"""
        if not self.api_key or not self.device_id:
            return None
        
        try:
            response = requests.get(
                f'{self.server_url}/api/device/{self.device_id}/active-schedule',
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('has_schedule'):
                    logger.info(f"Active schedule: {data['schedule']['name']}")
                    return data['schedule']
                else:
                    logger.debug('No active schedule at this time')
                    return None
            else:
                logger.debug(f'Schedule check failed: {response.status_code}')
                return None
        
        except Exception as e:
            logger.debug(f'Schedule check error: {e}')
            return None
    
    def sync_videos(self):
        """Fetch assigned videos from server"""
        if not self.api_key or not self.device_id:
            logger.warning('Device not registered, attempting registration...')
            if not self.register_device():
                return False
        
        try:
            logger.info('Syncing videos with server...')
            response = requests.get(
                f'{self.server_url}/api/videos/{self.device_id}',
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assigned_videos = data.get('videos', [])
                logger.info(f'Found {len(self.assigned_videos)} assigned video(s)')
                return True
            elif response.status_code == 401:
                logger.error('Authentication failed - API key may be invalid')
                return False
            else:
                logger.error(f'Sync failed: {response.status_code}')
                return False
        
        except Exception as e:
            logger.error(f'Sync error: {e}')
            return False
    
    def download_videos(self):
        """Download missing videos"""
        for video in self.assigned_videos:
            filename = video['filename']
            filepath = self.videos_dir / filename
            
            # Check if video already exists
            if filepath.exists():
                logger.info(f'Video already downloaded: {filename}')
                continue
            
            # Download video
            logger.info(f'Downloading: {filename}')
            try:
                video_url = f"{self.server_url}{video['url']}"
                response = requests.get(
                    video_url,
                    headers=self.get_headers(),
                    stream=True,
                    timeout=30
                )
                
                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Log progress every 10%
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    if int(progress) % 10 == 0:
                                        logger.info(f'Download progress: {int(progress)}%')
                    
                    logger.info(f'Downloaded: {filename} ({downloaded} bytes)')
                else:
                    logger.error(f'Download failed: {response.status_code}')
            
            except Exception as e:
                logger.error(f'Download error for {filename}: {e}')
                if filepath.exists():
                    filepath.unlink()
    
    def cleanup_videos(self):
        """Remove videos that are no longer assigned"""
        assigned_filenames = {video['filename'] for video in self.assigned_videos}
        
        for filepath in self.videos_dir.glob('*'):
            if filepath.is_file() and filepath.name not in assigned_filenames:
                logger.info(f'Removing unassigned video: {filepath.name}')
                try:
                    filepath.unlink()
                except Exception as e:
                    logger.error(f'Failed to remove {filepath.name}: {e}')
    
    def get_playlist(self, schedule=None):
        """Get list of local video files to play based on schedule or assignments (Phase 5)"""
        video_files = []
        
        if schedule:
            # Schedule-based playback
            content_type = schedule.get('content_type')
            
            if content_type == 'video':
                # Single video from schedule
                video_filename = schedule.get('video_filename')
                if video_filename:
                    filepath = self.videos_dir / video_filename
                    if filepath.exists():
                        video_files.append(str(filepath))
                        logger.info(f"Schedule playlist: {video_filename}")
            
            elif content_type == 'playlist':
                # Multiple videos from playlist
                playlist_videos = schedule.get('playlist_videos', [])
                for video in playlist_videos:
                    filename = video.get('filename')
                    if filename:
                        filepath = self.videos_dir / filename
                        if filepath.exists():
                            video_files.append(str(filepath))
                if video_files:
                    logger.info(f"Schedule playlist: {len(video_files)} video(s) from playlist '{schedule.get('content_name')}'")
        
        else:
            # Fallback to regular assignments
            for video in self.assigned_videos:
                filepath = self.videos_dir / video['filename']
                if filepath.exists():
                    video_files.append(str(filepath))
        
        return video_files
    
    def play_videos(self, schedule=None):
        """Play videos in fullscreen loop using mpv (Phase 5: schedule-aware)"""
        playlist = self.get_playlist(schedule)
        
        if not playlist:
            logger.warning('No videos to play')
            return
        
        # Verify all video files exist and have size
        valid_videos = []
        for video_path in playlist:
            if os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                if file_size > 0:
                    valid_videos.append(video_path)
                    logger.info(f'Video file: {os.path.basename(video_path)} ({file_size} bytes)')
                else:
                    logger.error(f'Video file is empty: {video_path}')
            else:
                logger.error(f'Video file not found: {video_path}')
        
        if not valid_videos:
            logger.error('No valid video files to play')
            return
        
        playlist = valid_videos
        logger.info(f'Starting playback of {len(playlist)} video(s)')
        if schedule:
            logger.info(f"Playing from schedule: {schedule.get('name')}")
        
        try:
            # mpv command optimized for Raspberry Pi
            mpv_cmd = [
                'mpv',
                '--fullscreen',
                '--loop-playlist=inf',
                '--no-osc',
                '--no-osd-bar',
                '--vo=gpu',  # Use GPU acceleration
                '--ao=alsa',  # ALSA audio output
                '--hwdec=auto',  # Hardware decoding
                '--profile=low-latency',  # Reduce buffering for smoother playback
                '--cache=yes',
                '--demuxer-max-bytes=50M',  # Limit buffer size
                '--vd-lavc-threads=4'  # Use 4 threads for decoding
            ] + playlist
            
            # Open log file for MPV stderr
            mpv_log_path = os.path.join(INSTALL_DIR, 'logs', 'mpv_output.log')
            mpv_log_file = open(mpv_log_path, 'a')
            
            self.player_process = subprocess.Popen(
                mpv_cmd,
                stdout=mpv_log_file,
                stderr=subprocess.STDOUT  # Redirect stderr to stdout (log file)
            )
            
            logger.info('MPV player started')
            logger.info(f'MPV command: {" ".join(mpv_cmd)}')
            logger.info(f'MPV output: {mpv_log_path}')
            self.current_video = os.path.basename(playlist[0])
            self.current_schedule = schedule  # Track which schedule is playing
        
        except FileNotFoundError:
            logger.error('mpv not found. Please install: sudo apt-get install mpv')
        except Exception as e:
            logger.error(f'Failed to start playback: {e}')
    
    def stop_playback(self):
        """Stop video playback"""
        if self.player_process:
            logger.info('Stopping playback...')
            self.player_process.terminate()
            try:
                self.player_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.player_process.kill()
            self.player_process = None
            self.current_video = None
    
    def is_playing(self):
        """Check if player is running"""
        return self.player_process and self.player_process.poll() is None
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        if not self.api_key or not self.device_id:
            return
        
        try:
            data = {
                'current_video': self.current_video,
                'status': 'playing' if self.is_playing() else 'idle',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            response = requests.post(
                f'{self.server_url}/api/device/heartbeat',
                headers=self.get_headers(),
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug('Heartbeat sent successfully')
            else:
                logger.warning(f'Heartbeat failed: {response.status_code}')
        
        except Exception as e:
            logger.debug(f'Heartbeat error: {e}')
    
    def check_device_config(self):
        """Check and apply device configuration updates (Phase 7)"""
        if not self.api_key or not self.device_id:
            return
        
        try:
            response = requests.get(
                f'{self.server_url}/api/devices/{self.device_id}/config',
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                config = response.json()
                
                # Update display settings
                if 'display' in config:
                    self.update_display_settings(config['display'])
                
                # Update audio settings
                if 'audio' in config:
                    self.update_audio_settings(config['audio'])
                
                # Check for screenshot request
                if 'config' in config and config['config'].get('screenshot_requested'):
                    self.capture_screenshot()
                
                logger.debug('Configuration checked')
            
        except Exception as e:
            logger.debug(f'Config check error: {e}')
    
    def update_display_settings(self, settings):
        """Apply display settings (Phase 7)"""
        try:
            # Apply brightness
            brightness = settings.get('brightness', 100)
            if brightness != self.display_settings.get('brightness'):
                subprocess.run(['vcgencmd', 'display_power', '1'], check=False)
                logger.info(f'Display brightness set to {brightness}%')
                self.display_settings['brightness'] = brightness
            
            # Apply screen rotation
            rotation = settings.get('rotation', 0)
            if rotation != self.display_settings.get('rotation'):
                logger.info(f'Display rotation updated to {rotation}°')
                self.display_settings['rotation'] = rotation
            
            # Check screen on/off times
            screen_on = settings.get('screen_on_time', '08:00')
            screen_off = settings.get('screen_off_time', '22:00')
            now = datetime.now().strftime('%H:%M')
            
            should_be_on = screen_on <= now < screen_off
            if should_be_on and not self.display_settings.get('screen_on', True):
                subprocess.run(['vcgencmd', 'display_power', '1'], check=False)
                logger.info('Screen turned ON')
                self.display_settings['screen_on'] = True
            elif not should_be_on and self.display_settings.get('screen_on', True):
                subprocess.run(['vcgencmd', 'display_power', '0'], check=False)
                logger.info('Screen turned OFF')
                self.display_settings['screen_on'] = False
        
        except Exception as e:
            logger.error(f'Failed to apply display settings: {e}')
    
    def update_audio_settings(self, settings):
        """Apply audio settings (Phase 7)"""
        try:
            # Apply volume
            volume = settings.get('volume', 80)
            if volume != self.audio_settings.get('volume'):
                subprocess.run(['amixer', 'set', 'PCM', f'{volume}%'], check=False)
                logger.info(f'Volume set to {volume}%')
                self.audio_settings['volume'] = volume
            
            # Apply mute
            muted = settings.get('muted', False)
            if muted != self.audio_settings.get('muted'):
                mute_cmd = 'mute' if muted else 'unmute'
                subprocess.run(['amixer', 'set', 'PCM', mute_cmd], check=False)
                logger.info(f'Audio {"muted" if muted else "unmuted"}')
                self.audio_settings['muted'] = muted
        
        except Exception as e:
            logger.error(f'Failed to apply audio settings: {e}')
    
    def capture_screenshot(self):
        """Capture and upload screenshot (Phase 7)"""
        try:
            screenshot_path = '/tmp/screenshot.jpg'
            
            # Capture screenshot using scrot or raspi2png
            result = subprocess.run(
                ['scrot', screenshot_path, '-q', '80'],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(screenshot_path):
                # Upload to server
                with open(screenshot_path, 'rb') as f:
                    files = {'screenshot': f}
                    response = requests.post(
                        f'{self.server_url}/api/devices/{self.device_id}/upload-screenshot',
                        headers=self.get_headers(),
                        files=files,
                        timeout=30
                    )
                
                if response.status_code == 200:
                    logger.info('Screenshot uploaded successfully')
                else:
                    logger.error(f'Screenshot upload failed: {response.status_code}')
                
                # Clean up
                os.remove(screenshot_path)
            else:
                logger.error('Screenshot capture failed')
        
        except Exception as e:
            logger.error(f'Screenshot error: {e}')
    
    def check_emergency_broadcasts(self):
        """Check for active emergency broadcasts (Phase 7)"""
        if not self.api_key or not self.device_id:
            return
        
        try:
            response = requests.get(
                f'{self.server_url}/api/devices/{self.device_id}/emergency-broadcasts',
                headers=self.get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                broadcasts = data.get('broadcasts', [])
                
                if broadcasts:
                    # Get highest priority broadcast
                    emergency = max(broadcasts, key=lambda b: b['priority'])
                    
                    # Check if this is a new or different emergency
                    if not self.current_emergency or emergency['id'] != self.current_emergency.get('id'):
                        logger.warning(f"Emergency broadcast activated: {emergency['title']}")
                        self.activate_emergency_broadcast(emergency)
                
                elif self.emergency_mode:
                    # No active emergencies, deactivate
                    logger.info('Emergency broadcast ended')
                    self.deactivate_emergency_broadcast()
        
        except Exception as e:
            logger.debug(f'Emergency check error: {e}')
    
    def activate_emergency_broadcast(self, emergency):
        """Activate emergency broadcast mode (Phase 7)"""
        try:
            self.emergency_mode = True
            self.current_emergency = emergency
            
            # Acknowledge receipt
            requests.post(
                f"{self.server_url}/api/devices/{self.device_id}/emergency-broadcasts/{emergency['id']}/acknowledge",
                headers=self.get_headers(),
                timeout=5
            )
            
            # Stop current playback
            self.stop_playback()
            
            # If emergency has a video, play it
            if emergency.get('video_id'):
                # Sync and download emergency video if needed
                self.sync_videos()
                self.download_videos()
                
                # Find and play emergency video
                for video in self.assigned_videos:
                    if video['id'] == emergency['video_id']:
                        filepath = self.videos_dir / video['filename']
                        if filepath.exists():
                            self.play_videos(emergency)
                            break
            
            logger.warning(f"Emergency broadcast: {emergency['message']}")
        
        except Exception as e:
            logger.error(f'Failed to activate emergency broadcast: {e}')
    
    def deactivate_emergency_broadcast(self):
        """Deactivate emergency broadcast mode (Phase 7)"""
        self.emergency_mode = False
        self.current_emergency = None
        
        # Stop emergency playback
        self.stop_playback()
        
        # Resume normal playback based on schedule or assignments
        active_schedule = self.get_active_schedule()
        self.play_videos(active_schedule)
    
    def run(self):
        """Main run loop (Phase 5: schedule-aware, Phase 7: client-control)"""
        logger.info('Starting PiCMS Player with schedule and client-control support...')
        
        # Ensure device is registered
        if not self.api_key or not self.device_id:
            if not self.register_device():
                logger.error('Failed to register device. Exiting.')
                sys.exit(1)
        
        last_sync = 0
        last_heartbeat = 0
        last_schedule_check = 0
        last_config_check = 0
        last_emergency_check = 0
        
        while True:
            try:
                current_time = time.time()
                
                # PRIORITY 1: Check for emergency broadcasts (Phase 7)
                if current_time - last_emergency_check >= EMERGENCY_CHECK_INTERVAL:
                    self.check_emergency_broadcasts()
                    last_emergency_check = current_time
                
                # PRIORITY 2: Check device configuration (Phase 7)
                if current_time - last_config_check >= CONFIG_CHECK_INTERVAL:
                    self.check_device_config()
                    last_config_check = current_time
                
                # Skip normal operations if in emergency mode
                if not self.emergency_mode:
                    # Check for active schedule (Phase 5)
                    if current_time - last_schedule_check >= SCHEDULE_CHECK_INTERVAL:
                        active_schedule = self.get_active_schedule()
                        
                        # Check if schedule changed
                        schedule_changed = False
                        if active_schedule and self.current_schedule:
                            # Both have schedules - compare IDs
                            if active_schedule.get('id') != self.current_schedule.get('id'):
                                schedule_changed = True
                                logger.info('Schedule changed, switching content...')
                        elif active_schedule and not self.current_schedule:
                            # New schedule became active
                            schedule_changed = True
                            logger.info('Schedule became active, switching to scheduled content...')
                        elif not active_schedule and self.current_schedule:
                            # Schedule ended
                            schedule_changed = True
                            logger.info('Schedule ended, returning to regular assignments...')
                        
                        # Restart playback if schedule changed
                        if schedule_changed:
                            self.stop_playback()
                            self.play_videos(active_schedule)
                        
                        last_schedule_check = current_time
                    
                    # Sync videos periodically
                    if current_time - last_sync >= SYNC_INTERVAL:
                        if self.sync_videos():
                            self.download_videos()
                            self.cleanup_videos()
                            
                            # Restart playback if not playing and no active schedule
                            if not self.is_playing() and not self.current_schedule:
                                self.play_videos()
                        
                        last_sync = current_time
                    
                    # Check if player crashed (restart with current schedule if any)
                    if not self.is_playing():
                        # Log MPV error if it crashed
                        if self.player_process:
                            try:
                                # Try to get return code and any buffered output
                                returncode = self.player_process.poll()
                                if returncode is not None:
                                    logger.error(f'MPV exited with code: {returncode}')
                                    # Try to read stderr if available
                                    if self.player_process.stderr:
                                        stderr_data = self.player_process.stderr.read()
                                        if stderr_data:
                                            logger.error(f'MPV stderr: {stderr_data.decode("utf-8", errors="ignore")}')
                            except Exception as e:
                                logger.error(f'Error reading MPV output: {e}')
                            finally:
                                self.player_process = None
                        
                        playlist = self.get_playlist(self.current_schedule)
                        if playlist:
                            logger.warning('Player not running, restarting...')
                            self.play_videos(self.current_schedule)
                
                # Send heartbeat
                if current_time - last_heartbeat >= HEARTBEAT_INTERVAL:
                    self.send_heartbeat()
                    last_heartbeat = current_time
                
                # Sleep before next iteration
                time.sleep(5)
            
            except KeyboardInterrupt:
                logger.info('Received shutdown signal')
                break
            except Exception as e:
                logger.error(f'Error in main loop: {e}')
                time.sleep(10)
        
        # Cleanup
        self.stop_playback()
        logger.info('PiCMS Player stopped')


def main():
    """Main entry point"""
    player = PiCMSPlayer()
    player.run()


if __name__ == '__main__':
    main()
