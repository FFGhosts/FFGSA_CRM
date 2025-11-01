"""
PiCMS Forms Module
Provides Flask-WTF forms with validation for all user inputs
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, SelectMultipleField, SubmitField, IntegerField, TimeField
from wtforms.validators import DataRequired, Length, Email, Optional, ValidationError, Regexp, NumberRange
from models import User, Device, Video
import re


class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    remember = BooleanField('Remember Me')


class VideoUploadForm(FlaskForm):
    """Video file upload form"""
    file = FileField('Video File', validators=[
        FileRequired(message='Please select a video file'),
        FileAllowed(['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'], 
                   message='Invalid file type. Allowed: mp4, avi, mkv, mov, wmv, flv, webm')
    ])
    title = StringField('Title', validators=[
        Optional(),
        Length(max=255, message='Title must be less than 255 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=1000, message='Description must be less than 1000 characters')
    ])


class VideoEditForm(FlaskForm):
    """Video metadata edit form"""
    title = StringField('Title', validators=[
        DataRequired(message='Title is required'),
        Length(min=1, max=255, message='Title must be between 1 and 255 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=1000, message='Description must be less than 1000 characters')
    ])


class DeviceAddForm(FlaskForm):
    """Add new device form"""
    name = StringField('Device Name', validators=[
        DataRequired(message='Device name is required'),
        Length(min=3, max=100, message='Device name must be between 3 and 100 characters'),
        Regexp(r'^[a-zA-Z0-9\s\-_]+$', message='Device name can only contain letters, numbers, spaces, hyphens, and underscores')
    ])
    location = StringField('Location', validators=[
        Optional(),
        Length(max=200, message='Location must be less than 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    
    def validate_name(self, field):
        """Check if device name already exists"""
        if Device.query.filter_by(name=field.data.strip()).first():
            raise ValidationError('A device with this name already exists')


class DeviceEditForm(FlaskForm):
    """Edit device form"""
    name = StringField('Device Name', validators=[
        DataRequired(message='Device name is required'),
        Length(min=3, max=100, message='Device name must be between 3 and 100 characters'),
        Regexp(r'^[a-zA-Z0-9\s\-_]+$', message='Device name can only contain letters, numbers, spaces, hyphens, and underscores')
    ])
    location = StringField('Location', validators=[
        Optional(),
        Length(max=200, message='Location must be less than 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    is_active = BooleanField('Active')


class AssignmentForm(FlaskForm):
    """Video/Playlist-to-device assignment form"""
    device_id = SelectField('Device', coerce=int, validators=[
        DataRequired(message='Please select a device')
    ])
    content_type = SelectField('Content Type', choices=[
        ('video', 'Single Video'),
        ('playlist', 'Playlist')
    ], validators=[DataRequired()])
    video_id = SelectField('Video', coerce=int, validators=[Optional()])
    playlist_id = SelectField('Playlist', coerce=int, validators=[Optional()])
    
    # Scheduling fields
    enable_schedule = BooleanField('Enable Time-Based Scheduling', default=False)
    start_time = TimeField('Start Time', validators=[Optional()])
    end_time = TimeField('End Time', validators=[Optional()])
    days_monday = BooleanField('Monday', default=False)
    days_tuesday = BooleanField('Tuesday', default=False)
    days_wednesday = BooleanField('Wednesday', default=False)
    days_thursday = BooleanField('Thursday', default=False)
    days_friday = BooleanField('Friday', default=False)
    days_saturday = BooleanField('Saturday', default=False)
    days_sunday = BooleanField('Sunday', default=False)
    
    def __init__(self, *args, **kwargs):
        super(AssignmentForm, self).__init__(*args, **kwargs)
        from models import Playlist
        # Populate device choices
        self.device_id.choices = [(0, 'Select Device...')] + [
            (d.id, f"{d.name} - {d.location or 'No location'}")
            for d in Device.query.filter_by(is_active=True).order_by(Device.name).all()
        ]
        # Populate video choices
        self.video_id.choices = [(0, 'Select Video...')] + [
            (v.id, v.title or v.filename)
            for v in Video.query.order_by(Video.title).all()
        ]
        # Populate playlist choices
        self.playlist_id.choices = [(0, 'Select Playlist...')] + [
            (p.id, p.name)
            for p in Playlist.query.filter_by(is_active=True).order_by(Playlist.name).all()
        ]
    
    def validate_device_id(self, field):
        """Ensure a valid device is selected"""
        if field.data == 0:
            raise ValidationError('Please select a valid device')
    
    def validate(self, **kwargs):
        """Ensure either video or playlist is selected based on content_type"""
        if not super(AssignmentForm, self).validate(**kwargs):
            return False
        
        if self.content_type.data == 'video':
            if not self.video_id.data or self.video_id.data == 0:
                self.video_id.errors.append('Please select a video')
                return False
        elif self.content_type.data == 'playlist':
            if not self.playlist_id.data or self.playlist_id.data == 0:
                self.playlist_id.errors.append('Please select a playlist')
                return False
        
        # Validate scheduling if enabled
        if self.enable_schedule.data:
            # Check if at least one day is selected
            days_selected = any([
                self.days_monday.data, self.days_tuesday.data, self.days_wednesday.data,
                self.days_thursday.data, self.days_friday.data, self.days_saturday.data,
                self.days_sunday.data
            ])
            if not days_selected:
                self.days_monday.errors.append('Please select at least one day')
                return False
        
        return True
    
    def get_days_of_week(self):
        """Convert day checkboxes to comma-separated string"""
        if not self.enable_schedule.data:
            return None
        
        days = []
        if self.days_monday.data:
            days.append('0')
        if self.days_tuesday.data:
            days.append('1')
        if self.days_wednesday.data:
            days.append('2')
        if self.days_thursday.data:
            days.append('3')
        if self.days_friday.data:
            days.append('4')
        if self.days_saturday.data:
            days.append('5')
        if self.days_sunday.data:
            days.append('6')
        
        return ','.join(days) if days else None
    
    def set_days_of_week(self, days_string):
        """Set day checkboxes from comma-separated string"""
        if not days_string:
            return
        
        days = days_string.split(',')
        self.days_monday.data = '0' in days
        self.days_tuesday.data = '1' in days
        self.days_wednesday.data = '2' in days
        self.days_thursday.data = '3' in days
        self.days_friday.data = '4' in days
        self.days_saturday.data = '5' in days
        self.days_sunday.data = '6' in days


class BulkAssignmentForm(FlaskForm):
    """Bulk video-to-devices assignment form"""
    device_ids = SelectMultipleField('Devices', coerce=int, validators=[
        DataRequired(message='Please select at least one device')
    ])
    video_id = SelectField('Video', coerce=int, validators=[
        DataRequired(message='Please select a video')
    ])
    
    def __init__(self, *args, **kwargs):
        super(BulkAssignmentForm, self).__init__(*args, **kwargs)
        # Populate device choices
        self.device_ids.choices = [
            (d.id, f"{d.name} - {d.location or 'No location'}")
            for d in Device.query.filter_by(is_active=True).order_by(Device.name).all()
        ]
        # Populate video choices
        self.video_id.choices = [(0, 'Select Video...')] + [
            (v.id, v.title or v.filename)
            for v in Video.query.order_by(Video.title).all()
        ]
    
    def validate_video_id(self, field):
        """Ensure a valid video is selected"""
        if field.data == 0:
            raise ValidationError('Please select a valid video')


class UserRegistrationForm(FlaskForm):
    """New user registration form (for future multi-user support)"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers, and underscores')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address'),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', 
               message='Password must contain uppercase, lowercase, and numbers')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password')
    ])
    
    def validate_username(self, field):
        """Check if username already exists"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')
    
    def validate_email(self, field):
        """Check if email already exists"""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')
    
    def validate_confirm_password(self, field):
        """Ensure passwords match"""
        if field.data != self.password.data:
            raise ValidationError('Passwords must match')


class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', 
               message='Password must contain uppercase, lowercase, and numbers')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password')
    ])
    
    def validate_confirm_password(self, field):
        """Ensure passwords match"""
        if field.data != self.new_password.data:
            raise ValidationError('Passwords must match')


class PlaylistCreateForm(FlaskForm):
    """Form for creating a new playlist"""
    name = StringField('Playlist Name', validators=[
        DataRequired(message='Playlist name is required'),
        Length(min=3, max=255, message='Name must be between 3 and 255 characters')
    ])
    description = TextAreaField('Description', validators=[
        Length(max=1000, message='Description cannot exceed 1000 characters')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Create Playlist')


class PlaylistEditForm(FlaskForm):
    """Form for editing an existing playlist"""
    name = StringField('Playlist Name', validators=[
        DataRequired(message='Playlist name is required'),
        Length(min=3, max=255, message='Name must be between 3 and 255 characters')
    ])
    description = TextAreaField('Description', validators=[
        Length(max=1000, message='Description cannot exceed 1000 characters')
    ])
    is_active = BooleanField('Active')
    submit = SubmitField('Update Playlist')


class PlaylistAddVideoForm(FlaskForm):
    """Form for adding a video to a playlist"""
    video_id = SelectField('Select Video', coerce=int, validators=[
        DataRequired(message='Please select a video'),
        NumberRange(min=1, message='Please select a valid video')
    ])
    position = IntegerField('Position', validators=[
        Optional(),
        NumberRange(min=0, message='Position must be 0 or greater')
    ])
    submit = SubmitField('Add Video')
    
    def __init__(self, *args, **kwargs):
        super(PlaylistAddVideoForm, self).__init__(*args, **kwargs)
        from models import Video
        from utils.video_utils import format_resolution
        # Populate video choices with title, resolution, and duration
        videos = Video.query.order_by(Video.title).all()
        choices = [(0, '-- Select Video --')]
        for v in videos:
            # Build descriptive label
            info_parts = [v.title]
            if v.width and v.height:
                info_parts.append(f"{format_resolution(v.width, v.height)}")
            if v.duration:
                info_parts.append(v.formatted_duration)
            label = f"{info_parts[0]} - {', '.join(info_parts[1:])}" if len(info_parts) > 1 else info_parts[0]
            choices.append((v.id, label))
        self.video_id.choices = choices


class DeviceGroupForm(FlaskForm):
    """Form for creating/editing device groups"""
    name = StringField('Group Name', validators=[
        DataRequired(message='Group name is required'),
        Length(min=2, max=100, message='Group name must be between 2 and 100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    color = StringField('Color', validators=[
        Optional(),
        Regexp(r'^#[0-9A-Fa-f]{6}$', message='Must be a valid hex color (e.g., #FF5733)')
    ], default='#6c757d')
    submit = SubmitField('Save Group')


class DeviceGroupMemberForm(FlaskForm):
    """Form for managing devices in a group"""
    device_ids = SelectMultipleField('Select Devices', coerce=int, validators=[
        DataRequired(message='Please select at least one device')
    ])
    submit = SubmitField('Add Devices')
    
    def __init__(self, *args, **kwargs):
        super(DeviceGroupMemberForm, self).__init__(*args, **kwargs)
        from models import Device
        # Populate device choices
        devices = Device.query.filter_by(is_active=True).order_by(Device.name).all()
        self.device_ids.choices = [(d.id, f"{d.name} ({d.serial})") for d in devices]


# USER MANAGEMENT FORMS (Phase 4.2)
# ============================================================================

class UserCreateForm(FlaskForm):
    """Form for creating new users"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters'),
        Regexp(r'^[a-zA-Z0-9_-]+$', message='Username can only contain letters, numbers, underscores, and hyphens')
    ])
    email = StringField('Email', validators=[
        Optional(),
        Email(message='Invalid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, max=100, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm password')
    ])
    role = SelectField('Role', choices=[
        ('ADMIN', 'Admin - Full access'),
        ('OPERATOR', 'Operator - Manage content and devices'),
        ('VIEWER', 'Viewer - Read-only access')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Create User')
    
    def validate_username(self, field):
        """Check if username already exists"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists')
    
    def validate_email(self, field):
        """Check if email already exists"""
        if field.data and User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')
    
    def validate_confirm_password(self, field):
        """Check if passwords match"""
        if field.data != self.password.data:
            raise ValidationError('Passwords must match')


class UserEditForm(FlaskForm):
    """Form for editing existing users"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters'),
        Regexp(r'^[a-zA-Z0-9_-]+$', message='Username can only contain letters, numbers, underscores, and hyphens')
    ])
    email = StringField('Email', validators=[
        Optional(),
        Email(message='Invalid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ])
    role = SelectField('Role', choices=[
        ('ADMIN', 'Admin - Full access'),
        ('OPERATOR', 'Operator - Manage content and devices'),
        ('VIEWER', 'Viewer - Read-only access')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active')
    submit = SubmitField('Update User')
    
    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, field):
        """Check if username already exists (excluding current user)"""
        if field.data != self.original_username:
            if User.query.filter_by(username=field.data).first():
                raise ValidationError('Username already exists')
    
    def validate_email(self, field):
        """Check if email already exists (excluding current user)"""
        if field.data and field.data != self.original_email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already registered')


class PasswordChangeForm(FlaskForm):
    """Form for changing user password"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=6, max=100, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm new password')
    ])
    submit = SubmitField('Change Password')
    
    def validate_confirm_password(self, field):
        """Check if passwords match"""
        if field.data != self.new_password.data:
            raise ValidationError('Passwords must match')


class ScheduleCreateForm(FlaskForm):
    """Form for creating content schedules"""
    device_id = SelectField('Device', coerce=int, validators=[
        DataRequired(message='Device is required')
    ])
    content_type = SelectField('Content Type', 
        choices=[('video', 'Video'), ('playlist', 'Playlist')],
        validators=[DataRequired(message='Content type is required')]
    )
    content_id = SelectField('Content', coerce=int, validators=[
        DataRequired(message='Content is required')
    ])
    start_time = TimeField('Start Time', format='%H:%M', validators=[
        DataRequired(message='Start time is required')
    ])
    end_time = TimeField('End Time', format='%H:%M', validators=[
        DataRequired(message='End time is required')
    ])
    start_date = StringField('Start Date (Optional)', validators=[Optional()])
    end_date = StringField('End Date (Optional)', validators=[Optional()])
    days_of_week = SelectMultipleField('Days of Week',
        choices=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday')
        ],
        validators=[Optional()]
    )
    priority = IntegerField('Priority (1-10)', validators=[
        DataRequired(message='Priority is required'),
        NumberRange(min=1, max=10, message='Priority must be between 1 and 10')
    ], default=5)
    recurrence_type = SelectField('Recurrence',
        choices=[
            ('NONE', 'One-time'),
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly')
        ],
        default='NONE',
        validators=[Optional()]
    )
    recurrence_interval = IntegerField('Repeat Every (N days/weeks/months)', validators=[
        Optional(),
        NumberRange(min=1, max=365, message='Interval must be between 1 and 365')
    ], default=1)
    recurrence_end_date = StringField('Recurrence End Date (Optional)', validators=[Optional()])
    is_all_day = BooleanField('All Day Event', default=False)  # Phase 5
    color = StringField('Calendar Color', validators=[Optional()], default='#3788d8')  # Phase 5
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Create Schedule')
    
    def validate_end_time(self, field):
        """Ensure end time is after start time"""
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('End time must be after start time')


class ScheduleEditForm(FlaskForm):
    """Form for editing content schedules"""
    device_id = SelectField('Device', coerce=int, validators=[
        DataRequired(message='Device is required')
    ])
    content_type = SelectField('Content Type', 
        choices=[('video', 'Video'), ('playlist', 'Playlist')],
        validators=[DataRequired(message='Content type is required')]
    )
    content_id = SelectField('Content', coerce=int, validators=[
        DataRequired(message='Content is required')
    ])
    start_time = TimeField('Start Time', format='%H:%M', validators=[
        DataRequired(message='Start time is required')
    ])
    end_time = TimeField('End Time', format='%H:%M', validators=[
        DataRequired(message='End time is required')
    ])
    start_date = StringField('Start Date (Optional)', validators=[Optional()])
    end_date = StringField('End Date (Optional)', validators=[Optional()])
    days_of_week = SelectMultipleField('Days of Week',
        choices=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday')
        ],
        validators=[Optional()]
    )
    priority = IntegerField('Priority (1-10)', validators=[
        DataRequired(message='Priority is required'),
        NumberRange(min=1, max=10, message='Priority must be between 1 and 10')
    ], default=5)
    recurrence_type = SelectField('Recurrence',
        choices=[
            ('NONE', 'One-time'),
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly')
        ],
        default='NONE',
        validators=[Optional()]
    )
    recurrence_interval = IntegerField('Repeat Every (N days/weeks/months)', validators=[
        Optional(),
        NumberRange(min=1, max=365, message='Interval must be between 1 and 365')
    ], default=1)
    recurrence_end_date = StringField('Recurrence End Date (Optional)', validators=[Optional()])
    is_all_day = BooleanField('All Day Event', default=False)  # Phase 5
    color = StringField('Calendar Color', validators=[Optional()], default='#3788d8')  # Phase 5
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Update Schedule')
    
    def validate_end_time(self, field):
        """Ensure end time is after start time"""
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('End time must be after start time')


