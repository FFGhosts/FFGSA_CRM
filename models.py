"""
PiCMS Database Models
SQLAlchemy ORM models for Video, Device, Assignment, and User
"""
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import enum

db = SQLAlchemy()


class UserRole(enum.Enum):
    """User role enumeration for RBAC (Phase 4.2)"""
    ADMIN = 'admin'        # Full access: manage users, content, devices, settings
    OPERATOR = 'operator'  # Manage content and devices, no user management
    VIEWER = 'viewer'      # Read-only access to dashboard and reports


class User(UserMixin, db.Model):
    """Admin user model for web dashboard authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.VIEWER, nullable=False)  # Phase 4.2
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # type: ignore
    last_login = db.Column(db.DateTime, nullable=True)  # Phase 4.2
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    # Role permission helpers (Phase 4.2)
    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_operator(self):
        """Check if user has operator role"""
        return self.role == UserRole.OPERATOR
    
    @property
    def is_viewer(self):
        """Check if user has viewer role"""
        return self.role == UserRole.VIEWER
    
    @property
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.is_admin
    
    @property
    def can_manage_content(self):
        """Check if user can upload/delete videos and playlists"""
        return self.is_admin or self.is_operator
    
    @property
    def can_manage_devices(self):
        """Check if user can add/remove devices"""
        return self.is_admin or self.is_operator
    
    @property
    def can_send_commands(self):
        """Check if user can send remote commands"""
        return self.is_admin or self.is_operator
    
    @property
    def role_display(self):
        """Get display name for role"""
        return self.role.value.title()
    
    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'


class Video(db.Model):
    """Video content model"""
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    size = db.Column(db.Integer, nullable=False)  # File size in bytes
    mimetype = db.Column(db.String(50), nullable=True)
    
    # Video metadata (extracted from ffprobe)
    width = db.Column(db.Integer, nullable=True)  # Resolution width
    height = db.Column(db.Integer, nullable=True)  # Resolution height
    codec = db.Column(db.String(50), nullable=True)  # Video codec
    bitrate = db.Column(db.Integer, nullable=True)  # Bitrate in kbps
    framerate = db.Column(db.Float, nullable=True)  # Frames per second
    video_format = db.Column(db.String(50), nullable=True)  # Container format
    has_thumbnail = db.Column(db.Boolean, default=False)  # Thumbnail generated flag
    
    # File integrity (Phase 3.4)
    checksum = db.Column(db.String(64), nullable=True, index=True)  # SHA256 hash
    
    # Relationships
    assignments = db.relationship('Assignment', backref='video', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def formatted_size(self):
        """Return human-readable file size"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    @property
    def formatted_duration(self):
        """Return human-readable duration"""
        if not self.duration:
            return "Unknown"
        
        minutes, seconds = divmod(self.duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def __repr__(self):
        return f'<Video {self.title}>'


class Device(db.Model):
    """Raspberry Pi device model"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(100), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Support IPv6
    api_key_hash = db.Column(db.String(255), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    current_video = db.Column(db.String(255), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id'), nullable=True)
    
    # Relationships
    assignments = db.relationship('Assignment', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    group = db.relationship('DeviceGroup', backref='devices', foreign_keys=[group_id])
    
    @staticmethod
    def generate_api_key():
        """Generate a secure random API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key):
        """Hash API key for secure storage"""
        return generate_password_hash(api_key)
    
    def verify_api_key(self, api_key):
        """Verify API key against stored hash"""
        return check_password_hash(self.api_key_hash, api_key)
    
    @property
    def is_online(self):
        """Check if device is online based on last_seen timestamp"""
        if not self.last_seen:
            return False
        
        from config import Config
        timeout = timedelta(minutes=Config.DEVICE_TIMEOUT_MINUTES)
        return datetime.utcnow() - self.last_seen < timeout
    
    @property
    def status(self):
        """Return device status string"""
        return "Online" if self.is_online else "Offline"
    
    def __repr__(self):
        return f'<Device {self.name} ({self.serial})>'


class Playlist(db.Model):
    """Playlist model for organizing multiple videos"""
    __tablename__ = 'playlists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    items = db.relationship('PlaylistItem', backref='playlist', lazy='dynamic', 
                          cascade='all, delete-orphan', order_by='PlaylistItem.position')
    assignments = db.relationship('Assignment', backref='playlist', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def total_duration(self):
        """Calculate total duration of all videos in playlist"""
        total = 0
        for item in self.items:
            if item.video and item.video.duration:
                total += item.video.duration
        return total
    
    @property
    def video_count(self):
        """Count videos in playlist"""
        return self.items.count()
    
    @property
    def formatted_duration(self):
        """Return human-readable total duration"""
        duration = self.total_duration
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def __repr__(self):
        return f'<Playlist {self.name}>'


class PlaylistItem(db.Model):
    """Many-to-many relationship between Playlist and Video with ordering"""
    __tablename__ = 'playlist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    video = db.relationship('Video', backref='playlist_items')
    
    # Unique constraint: one video position per playlist
    __table_args__ = (
        db.UniqueConstraint('playlist_id', 'position', name='unique_playlist_position'),
    )
    
    def __repr__(self):
        return f'<PlaylistItem Playlist:{self.playlist_id} Video:{self.video_id} Pos:{self.position}>'


class Assignment(db.Model):
    """Video/Playlist-to-Device assignment model"""
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    priority = db.Column(db.Integer, default=0)  # For future scheduling feature
    
    # Scheduling fields
    start_time = db.Column(db.Time, nullable=True)  # Time of day to start showing content (e.g., 09:00)
    end_time = db.Column(db.Time, nullable=True)    # Time of day to stop showing content (e.g., 17:00)
    days_of_week = db.Column(db.String(20), nullable=True)  # Comma-separated: "0,1,2,3,4" (Mon-Fri) or None for all days
    
    # Constraint: must assign either video OR playlist, not both
    __table_args__ = (
        db.CheckConstraint('(video_id IS NOT NULL AND playlist_id IS NULL) OR (video_id IS NULL AND playlist_id IS NOT NULL)', 
                          name='check_video_or_playlist'),
    )
    
    @property
    def content_type(self):
        """Return type of assigned content"""
        return 'video' if self.video_id else 'playlist'
    
    @property
    def content_name(self):
        """Return name of assigned content"""
        if self.video_id:
            return self.video.title
        elif self.playlist_id:
            return self.playlist.name
        return "Unknown"
    
    @property
    def is_scheduled(self):
        """Check if assignment has scheduling constraints"""
        return self.start_time is not None or self.end_time is not None or self.days_of_week is not None
    
    @property
    def days_list(self):
        """Return list of day numbers from days_of_week string"""
        if not self.days_of_week:
            return None
        return [int(d) for d in self.days_of_week.split(',') if d.strip()]
    
    @property
    def formatted_schedule(self):
        """Return human-readable schedule description"""
        parts = []
        
        # Days
        if self.days_of_week:
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            days = [day_names[int(d)] for d in self.days_of_week.split(',') if d.strip() and int(d) < 7]
            if len(days) == 7 or not days:
                parts.append("Every day")
            elif len(days) == 5 and days == day_names[:5]:
                parts.append("Weekdays")
            elif len(days) == 2 and days == day_names[5:7]:
                parts.append("Weekends")
            else:
                parts.append(", ".join(days))
        else:
            parts.append("Every day")
        
        # Time range
        if self.start_time and self.end_time:
            parts.append(f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}")
        elif self.start_time:
            parts.append(f"After {self.start_time.strftime('%I:%M %p')}")
        elif self.end_time:
            parts.append(f"Until {self.end_time.strftime('%I:%M %p')}")
        else:
            parts.append("All day")
        
        return " • ".join(parts)
    
    def is_active_at(self, check_datetime=None):
        """
        Check if assignment is active at a given datetime
        
        Args:
            check_datetime: datetime to check (defaults to current time)
            
        Returns:
            bool: True if assignment should be active
        """
        if check_datetime is None:
            check_datetime = datetime.now()
        
        # Check day of week (0=Monday, 6=Sunday)
        if self.days_of_week:
            current_day = check_datetime.weekday()
            if str(current_day) not in self.days_of_week.split(','):
                return False
        
        # Check time range
        current_time = check_datetime.time()
        
        if self.start_time and self.end_time:
            # Handle time ranges that cross midnight
            if self.start_time <= self.end_time:
                # Normal range (e.g., 09:00-17:00)
                if not (self.start_time <= current_time <= self.end_time):
                    return False
            else:
                # Crosses midnight (e.g., 22:00-02:00)
                if not (current_time >= self.start_time or current_time <= self.end_time):
                    return False
        elif self.start_time:
            # Only start time set
            if current_time < self.start_time:
                return False
        elif self.end_time:
            # Only end time set
            if current_time > self.end_time:
                return False
        
        return True
    
    def __repr__(self):
        return f'<Assignment Device:{self.device_id} {self.content_type.title()}:{self.video_id or self.playlist_id}>'


# Device Group relationship table (many-to-many)
device_group_members = db.Table('device_group_members',
    db.Column('device_id', db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('device_groups.id', ondelete='CASCADE'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)


class DeviceGroup(db.Model):
    """Device Group model for organizing devices"""
    __tablename__ = 'device_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color for UI
    
    # Relationships
    devices = db.relationship('Device', secondary=device_group_members, backref=db.backref('groups', lazy='dynamic'))
    
    @property
    def device_count(self):
        """Get number of devices in this group"""
        return len(self.devices)
    
    @property
    def online_device_count(self):
        """Get number of online devices in this group"""
        return sum(1 for device in self.devices if device.is_online)
    
    def __repr__(self):
        return f'<DeviceGroup {self.name}>'


class ApiLog(db.Model):
    """API request logging model (optional - can also use file logging)"""
    __tablename__ = 'api_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='SET NULL'), nullable=True)
    endpoint = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    status_code = db.Column(db.Integer, nullable=False)
    response_time = db.Column(db.Float, nullable=True)  # Response time in milliseconds
    
    def __repr__(self):
        return f'<ApiLog {self.method} {self.endpoint} - {self.status_code}>'


# ============================================================================
# REMOTE COMMANDS MODEL (Phase 3.3)
# ============================================================================

class DeviceCommand(db.Model):
    """Remote commands sent to devices"""
    __tablename__ = 'device_commands'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    command_type = db.Column(db.String(50), nullable=False)  # restart, update, clear_cache, etc.
    parameters = db.Column(db.Text, nullable=True)  # JSON parameters
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, acknowledged, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    result = db.Column(db.Text, nullable=True)  # Command result or error message
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('commands', lazy='dynamic'))
    
    @property
    def is_pending(self):
        """Check if command is pending"""
        return self.status == 'pending'
    
    @property
    def is_completed(self):
        """Check if command is completed"""
        return self.status in ('completed', 'failed')
    
    def __repr__(self):
        return f'<DeviceCommand {self.command_type} for Device:{self.device_id} - {self.status}>'


# ANALYTICS MODELS (Phase 3.1)
# ============================================================================

class PlaybackLog(db.Model):
    """Tracks when devices play videos"""
    __tablename__ = 'playback_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_played = db.Column(db.Integer, nullable=True)  # Seconds
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('playback_logs', lazy='dynamic'))
    video = db.relationship('Video', backref=db.backref('playback_logs', lazy='dynamic'))
    playlist = db.relationship('Playlist', backref=db.backref('playback_logs', lazy='dynamic'))
    
    def __repr__(self):
        return f'<PlaybackLog Device:{self.device_id} Video:{self.video_id}>'


class ViewCount(db.Model):
    """Aggregated view counts for videos"""
    __tablename__ = 'view_counts'
    
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, unique=True)
    total_views = db.Column(db.Integer, default=0, nullable=False)
    unique_devices = db.Column(db.Integer, default=0, nullable=False)
    last_viewed = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    video = db.relationship('Video', backref=db.backref('view_count', uselist=False))
    
    def __repr__(self):
        return f'<ViewCount Video:{self.video_id} Views:{self.total_views}>'


class DeviceUsage(db.Model):
    """Daily device usage statistics"""
    __tablename__ = 'device_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    total_playtime = db.Column(db.Integer, default=0, nullable=False)  # Seconds
    videos_played = db.Column(db.Integer, default=0, nullable=False)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('usage_stats', lazy='dynamic'))
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('device_id', 'date', name='unique_device_date'),
    )
    
    def __repr__(self):
        return f'<DeviceUsage Device:{self.device_id} Date:{self.date}>'


# USER ACTIVITY LOGGING (Phase 4.2)
# ============================================================================

class UserActivity(db.Model):
    """Logs user actions for audit trail and activity monitoring"""
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(100), nullable=False, index=True)  # login, upload_video, delete_device, etc.
    resource_type = db.Column(db.String(50), nullable=True)  # video, device, user, playlist
    resource_id = db.Column(db.Integer, nullable=True)  # ID of affected resource
    details = db.Column(db.Text, nullable=True)  # JSON details about the action
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UserActivity {self.user.username}: {self.action} at {self.timestamp}>'


# SCHEDULING MODELS (Phase 4.3)
# ============================================================================

class Schedule(db.Model):
    """Content scheduling with time-based playback control"""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Content references (one of these must be set)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), nullable=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), nullable=True)
    
    # Target devices (NULL = all devices)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=True)
    device_group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id', ondelete='CASCADE'), nullable=True)
    
    # Time scheduling
    start_time = db.Column(db.Time, nullable=False)  # Daily start time (e.g., 09:00)
    end_time = db.Column(db.Time, nullable=False)    # Daily end time (e.g., 17:00)
    
    # Day of week selection (JSON array: [0=Monday, 1=Tuesday, ..., 6=Sunday])
    days_of_week = db.Column(db.String(20), nullable=True)  # e.g., "0,1,2,3,4" for Mon-Fri
    
    # Date range (optional - for seasonal/holiday content)
    start_date = db.Column(db.Date, nullable=True)  # Schedule active from this date
    end_date = db.Column(db.Date, nullable=True)    # Schedule active until this date
    
    # Priority for conflict resolution (higher = more important)
    priority = db.Column(db.Integer, default=0, nullable=False)
    
    # Recurrence (Phase 5)
    is_recurring = db.Column(db.Boolean, default=True)  # Repeat based on pattern
    recurrence_type = db.Column(db.String(20), default='weekly')  # none, daily, weekly, monthly, yearly
    recurrence_interval = db.Column(db.Integer, default=1)  # Repeat every N periods
    recurrence_end_date = db.Column(db.Date, nullable=True)  # Stop repeating after this date
    
    # Display options (Phase 5)
    is_all_day = db.Column(db.Boolean, default=False)  # All-day event (ignores start/end time)
    color = db.Column(db.String(7), default='#3788d8')  # Calendar display color
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video = db.relationship('Video', backref=db.backref('schedules', lazy='dynamic'))
    playlist = db.relationship('Playlist', backref=db.backref('schedules', lazy='dynamic'))
    device = db.relationship('Device', backref=db.backref('schedules', lazy='dynamic'))
    device_group = db.relationship('DeviceGroup', backref=db.backref('schedules', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref('created_schedules', lazy='dynamic'))
    
    @property
    def content_type(self):
        """Get the type of content scheduled"""
        if self.video_id:
            return 'video'
        elif self.playlist_id:
            return 'playlist'
        return None
    
    @property
    def content_name(self):
        """Get the name of the scheduled content"""
        if self.video:
            return self.video.title
        elif self.playlist:
            return self.playlist.name
        return 'Unknown'
    
    @property
    def target_description(self):
        """Get description of schedule target"""
        if self.device:
            return f"Device: {self.device.name}"
        elif self.device_group:
            return f"Group: {self.device_group.name}"
        return "All Devices"
    
    @property
    def days_list(self):
        """Get list of day indices as integers"""
        if not self.days_of_week:
            return list(range(7))  # All days
        return [int(d) for d in self.days_of_week.split(',') if d]
    
    @property
    def days_display(self):
        """Get human-readable day names"""
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if not self.days_of_week:
            return 'Every day'
        days = self.days_list
        if len(days) == 7:
            return 'Every day'
        elif days == [0, 1, 2, 3, 4]:
            return 'Weekdays'
        elif days == [5, 6]:
            return 'Weekends'
        return ', '.join([day_names[d] for d in days])
    
    def is_active_on_date(self, check_date):
        """Check if schedule is active on a given date"""
        if not self.is_active:
            return False
        
        # Check date range
        if self.start_date and check_date < self.start_date:
            return False
        if self.end_date and check_date > self.end_date:
            return False
        
        # Check day of week
        weekday = check_date.weekday()  # 0=Monday, 6=Sunday
        if self.days_of_week:
            if weekday not in self.days_list:
                return False
        
        return True
    
    def is_active_at_time(self, check_time):
        """Check if schedule is active at a given time"""
        if not self.is_active:
            return False
        
        # Handle overnight schedules (e.g., 22:00 - 02:00)
        if self.end_time < self.start_time:
            return check_time >= self.start_time or check_time <= self.end_time
        else:
            return self.start_time <= check_time <= self.end_time
    
    def get_recurrence_description(self):
        """Get human-readable recurrence description"""
        if not self.is_recurring or self.recurrence_type == 'none':
            return 'Does not repeat'
        
        interval_text = ''
        if self.recurrence_interval > 1:
            interval_text = f'every {self.recurrence_interval} '
        else:
            interval_text = 'every '
        
        type_map = {
            'daily': 'day',
            'weekly': 'week',
            'monthly': 'month',
            'yearly': 'year'
        }
        
        base = f"Repeats {interval_text}{type_map.get(self.recurrence_type, self.recurrence_type)}"
        
        if self.recurrence_end_date:
            base += f" until {self.recurrence_end_date.strftime('%Y-%m-%d')}"
        
        return base
    
    def __repr__(self):
        return f'<Schedule {self.name}: {self.start_time}-{self.end_time}>'


class ScheduleException(db.Model):
    """Date-specific schedule overrides for holidays, special events, or blackouts (Phase 5)"""
    __tablename__ = 'schedule_exceptions'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id', ondelete='CASCADE'), nullable=False)
    exception_date = db.Column(db.Date, nullable=False)
    exception_type = db.Column(db.String(20), nullable=False)  # 'blackout', 'override', 'special'
    
    # Override content (optional - only for 'override' type)
    override_video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='SET NULL'), nullable=True)
    override_playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='SET NULL'), nullable=True)
    
    # Description
    reason = db.Column(db.Text, nullable=True)  # e.g., "Christmas Day", "Company Holiday"
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    schedule = db.relationship('Schedule', backref=db.backref('exceptions', lazy='dynamic', cascade='all, delete-orphan'))
    override_video = db.relationship('Video')
    override_playlist = db.relationship('Playlist')
    creator = db.relationship('User')
    
    def __repr__(self):
        return f'<ScheduleException {self.exception_type} on {self.exception_date}>'


# CONTENT ORGANIZATION MODELS (Phase 4.4)
# ============================================================================

# Association tables for many-to-many relationships
video_tags = db.Table('video_tags',
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

playlist_tags = db.Table('playlist_tags',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

video_categories = db.Table('video_categories',
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id', ondelete='CASCADE'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True)
)

playlist_categories = db.Table('playlist_categories',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True)
)


class Tag(db.Model):
    """Tags for organizing content (flexible, user-created)"""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color for display
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    videos = db.relationship('Video', secondary=video_tags, backref=db.backref('tags', lazy='dynamic'))
    playlists = db.relationship('Playlist', secondary=playlist_tags, backref=db.backref('tags', lazy='dynamic'))
    created_by = db.relationship('User', backref=db.backref('created_tags', lazy='dynamic'))
    
    @property
    def video_count(self):
        """Count of videos with this tag"""
        return len(self.videos)
    
    @property
    def playlist_count(self):
        """Count of playlists with this tag"""
        return len(self.playlists)
    
    @property
    def total_usage(self):
        """Total usage count"""
        return self.video_count + self.playlist_count
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class Category(db.Model):
    """Categories for organizing content (hierarchical, predefined)"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)  # For hierarchy
    color = db.Column(db.String(7), default='#0d6efd')  # Hex color for display
    icon = db.Column(db.String(50), nullable=True)  # Bootstrap icon name
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    videos = db.relationship('Video', secondary=video_categories, backref=db.backref('categories', lazy='dynamic'))
    playlists = db.relationship('Playlist', secondary=playlist_categories, backref=db.backref('categories', lazy='dynamic'))
    parent = db.relationship('Category', remote_side=[id], backref='subcategories')
    created_by = db.relationship('User', backref=db.backref('created_categories', lazy='dynamic'))
    
    @property
    def video_count(self):
        """Count of videos in this category"""
        return len(self.videos)
    
    @property
    def playlist_count(self):
        """Count of playlists in this category"""
        return len(self.playlists)
    
    @property
    def total_usage(self):
        """Total usage count"""
        return self.video_count + self.playlist_count
    
    @property
    def full_path(self):
        """Get full category path (e.g., 'Parent > Child')"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def __repr__(self):
        return f'<Category {self.name}>'


# ============================================================================
# NOTIFICATION SYSTEM MODELS (Phase 6)
# ============================================================================

class NotificationType(enum.Enum):
    """Notification type enumeration"""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    DEVICE_ALERT = 'device_alert'
    SYSTEM_ALERT = 'system_alert'


class NotificationPriority(enum.Enum):
    """Notification priority levels"""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'


class Notification(db.Model):
    """System notifications for users (Phase 6)"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)  # NULL = all users
    notification_type = db.Column(db.Enum(NotificationType), nullable=False, default=NotificationType.INFO)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    
    # Categorization
    category = db.Column(db.String(50), nullable=True)  # e.g., 'device', 'upload', 'backup', 'system'
    
    # Related entity linking
    related_entity_type = db.Column(db.String(50), nullable=True)  # e.g., 'device', 'video', 'schedule'
    related_entity_id = db.Column(db.Integer, nullable=True)
    
    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_dismissed = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # Auto-cleanup old notifications
    
    # Action
    action_url = db.Column(db.String(500), nullable=True)  # Link to relevant page
    icon = db.Column(db.String(50), nullable=True)  # Bootstrap icon class
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def age_hours(self):
        """Get notification age in hours"""
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds() / 3600
    
    @property
    def type_badge_class(self):
        """Get Bootstrap badge class for notification type"""
        type_classes = {
            NotificationType.INFO: 'bg-info',
            NotificationType.SUCCESS: 'bg-success',
            NotificationType.WARNING: 'bg-warning',
            NotificationType.ERROR: 'bg-danger',
            NotificationType.DEVICE_ALERT: 'bg-primary',
            NotificationType.SYSTEM_ALERT: 'bg-dark'
        }
        return type_classes.get(self.notification_type, 'bg-secondary')
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<Notification {self.title} ({self.notification_type.value})>'


class NotificationPreference(db.Model):
    """User notification preferences (Phase 6)"""
    __tablename__ = 'notification_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Global toggles
    email_enabled = db.Column(db.Boolean, default=True, nullable=False)
    browser_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # Device alerts
    device_offline_email = db.Column(db.Boolean, default=True, nullable=False)
    device_offline_browser = db.Column(db.Boolean, default=True, nullable=False)
    
    # Upload notifications
    upload_complete_email = db.Column(db.Boolean, default=False, nullable=False)
    upload_complete_browser = db.Column(db.Boolean, default=True, nullable=False)
    
    # Backup notifications
    backup_success_email = db.Column(db.Boolean, default=True, nullable=False)
    backup_success_browser = db.Column(db.Boolean, default=True, nullable=False)
    backup_failure_email = db.Column(db.Boolean, default=True, nullable=False)
    backup_failure_browser = db.Column(db.Boolean, default=True, nullable=False)
    
    # System alerts
    system_error_email = db.Column(db.Boolean, default=True, nullable=False)
    system_error_browser = db.Column(db.Boolean, default=True, nullable=False)
    schedule_conflict_email = db.Column(db.Boolean, default=True, nullable=False)
    schedule_conflict_browser = db.Column(db.Boolean, default=True, nullable=False)
    storage_warning_email = db.Column(db.Boolean, default=True, nullable=False)
    storage_warning_browser = db.Column(db.Boolean, default=True, nullable=False)
    
    # Reports
    daily_summary_email = db.Column(db.Boolean, default=False, nullable=False)
    weekly_report_email = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notification_preferences', uselist=False))
    
    def should_notify(self, category: str, channel: str) -> bool:
        """
        Check if notification should be sent for given category and channel
        
        Args:
            category: Notification category (e.g., 'device_offline', 'backup_success')
            channel: 'email' or 'browser'
        
        Returns:
            bool: True if notification should be sent
        """
        # Check global toggle
        if channel == 'email' and not self.email_enabled:
            return False
        if channel == 'browser' and not self.browser_enabled:
            return False
        
        # Check specific preference
        pref_name = f"{category}_{channel}"
        return getattr(self, pref_name, False)
    
    def __repr__(self):
        return f'<NotificationPreference user_id={self.user_id}>'


# ============================================================================
# PHASE 7: CLIENT-SIDE ENHANCEMENTS MODELS
# ============================================================================

class DeviceConfig(db.Model):
    """Device-specific configuration key-value pairs (Phase 7)"""
    __tablename__ = 'device_config'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    config_key = db.Column(db.String(100), nullable=False)
    config_value = db.Column(db.Text)
    config_type = db.Column(db.String(50), default='string')  # string, int, bool, json
    description = db.Column(db.Text)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('configs', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('device_id', 'config_key', name='uix_device_config'),
    )
    
    def get_typed_value(self):
        """Return value with proper type conversion"""
        if self.config_type == 'int':
            return int(self.config_value) if self.config_value else 0
        elif self.config_type == 'bool':
            return self.config_value.lower() == 'true' if self.config_value else False
        elif self.config_type == 'json':
            import json
            return json.loads(self.config_value) if self.config_value else {}
        return self.config_value
    
    def __repr__(self):
        return f'<DeviceConfig {self.device_id}:{self.config_key}={self.config_value}>'


class DisplaySettings(db.Model):
    """Display configuration for Raspberry Pi devices (Phase 7)"""
    __tablename__ = 'display_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True)
    resolution_width = db.Column(db.Integer, default=1920)
    resolution_height = db.Column(db.Integer, default=1080)
    rotation = db.Column(db.Integer, default=0)  # 0, 90, 180, 270
    screen_on_time = db.Column(db.String(5), default='08:00')
    screen_off_time = db.Column(db.String(5), default='22:00')
    brightness = db.Column(db.Integer, default=100)  # 0-100
    screen_saver_enabled = db.Column(db.Boolean, default=False)
    screen_saver_delay = db.Column(db.Integer, default=300)  # seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('display_settings', uselist=False, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<DisplaySettings device={self.device_id} res={self.resolution_width}x{self.resolution_height}>'


class NetworkConfig(db.Model):
    """Network configuration for Raspberry Pi devices (Phase 7)"""
    __tablename__ = 'network_config'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True)
    connection_type = db.Column(db.String(20), default='ethernet')  # ethernet, wifi
    wifi_ssid = db.Column(db.String(100))
    wifi_password = db.Column(db.String(100))
    wifi_security = db.Column(db.String(20), default='WPA2')
    use_dhcp = db.Column(db.Boolean, default=True)
    static_ip = db.Column(db.String(15))
    static_gateway = db.Column(db.String(15))
    static_dns = db.Column(db.String(15))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('network_config', uselist=False, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<NetworkConfig device={self.device_id} type={self.connection_type}>'


class SystemUpdate(db.Model):
    """System software updates for Raspberry Pi clients (Phase 7)"""
    __tablename__ = 'system_update'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False, unique=True)
    release_date = db.Column(db.Date, default=datetime.utcnow)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    checksum = db.Column(db.String(64))
    is_critical = db.Column(db.Boolean, default=False)
    min_version = db.Column(db.String(20))  # Minimum version required
    status = db.Column(db.String(20), default='available')  # available, deprecated, mandatory
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_updates')
    device_updates = db.relationship('DeviceUpdate', backref='update', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SystemUpdate v{self.version} {self.status}>'


class DeviceUpdate(db.Model):
    """Track update status per device (Phase 7)"""
    __tablename__ = 'device_update'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    update_id = db.Column(db.Integer, db.ForeignKey('system_update.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, downloading, installing, completed, failed
    download_progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('updates', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<DeviceUpdate device={self.device_id} update={self.update_id} status={self.status}>'


class DeviceScreenshot(db.Model):
    """Screenshots captured from Raspberry Pi devices (Phase 7)"""
    __tablename__ = 'device_screenshot'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('screenshots', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<DeviceScreenshot device={self.device_id} at={self.captured_at}>'


class AudioSettings(db.Model):
    """Audio configuration for Raspberry Pi devices (Phase 7)"""
    __tablename__ = 'audio_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True)
    volume = db.Column(db.Integer, default=80)  # 0-100
    muted = db.Column(db.Boolean, default=False)
    audio_output = db.Column(db.String(50), default='hdmi')  # hdmi, analog, usb
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('audio_settings', uselist=False, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<AudioSettings device={self.device_id} vol={self.volume} muted={self.muted}>'


class EmergencyBroadcast(db.Model):
    """Emergency broadcast messages (Phase 7)"""
    __tablename__ = 'emergency_broadcast'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete='SET NULL'))
    priority = db.Column(db.Integer, default=1)  # 1=low, 5=critical
    duration = db.Column(db.Integer)  # Duration in seconds, null = until manually cancelled
    target_all_devices = db.Column(db.Boolean, default=True)
    target_device_group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id', ondelete='SET NULL'))
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    video = db.relationship('Video', backref='emergency_broadcasts')
    device_group = db.relationship('DeviceGroup', backref='emergency_broadcasts')
    creator = db.relationship('User', backref='emergency_broadcasts')
    device_statuses = db.relationship('EmergencyBroadcastDevice', backref='broadcast', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def is_active(self):
        """Check if broadcast is currently active"""
        if self.status != 'active':
            return False
        now = datetime.utcnow()
        if now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True
    
    def __repr__(self):
        return f'<EmergencyBroadcast {self.title} status={self.status}>'


class EmergencyBroadcastDevice(db.Model):
    """Track emergency broadcast delivery per device (Phase 7)"""
    __tablename__ = 'emergency_broadcast_device'
    
    id = db.Column(db.Integer, primary_key=True)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('emergency_broadcast.id', ondelete='CASCADE'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, acknowledged, displayed, error
    acknowledged_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    device = db.relationship('Device', backref=db.backref('emergency_broadcast_statuses', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (
        db.UniqueConstraint('broadcast_id', 'device_id', name='uix_broadcast_device'),
    )
    
    def __repr__(self):
        return f'<EmergencyBroadcastDevice broadcast={self.broadcast_id} device={self.device_id} status={self.status}>'




