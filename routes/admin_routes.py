"""
Admin Routes Blueprint
Web dashboard routes for video management, device management, and assignments
"""
import os
import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func

from models import db, User, Video, Device, Assignment, Playlist, UserRole, UserActivity, Tag, Category, Notification
from forms import (LoginForm, VideoUploadForm, VideoEditForm, DeviceAddForm, DeviceEditForm, AssignmentForm,
                   UserCreateForm, UserEditForm, PasswordChangeForm)
from utils.video_utils import (extract_video_metadata, generate_thumbnail, delete_thumbnail,
                                get_thumbnail_path, VideoProcessingError)
from utils.permissions import admin_required, content_manager_required, device_manager_required, log_activity

admin_bp = Blueprint('admin', __name__)


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page with form validation"""
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been disabled. Contact an administrator.', 'danger')
                return render_template('login.html', form=form)
            
            # Update last login timestamp
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=form.remember.data)
            
            # Log activity
            log_activity('login', details={'method': 'password'})
            
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('admin.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)


@admin_bp.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin.login'))


# ============================================================================
# DASHBOARD
# ============================================================================

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with statistics"""
    
    # Get statistics
    total_videos = Video.query.count()
    total_devices = Device.query.count()
    
    # Count online devices (last seen within timeout period)
    online_devices = sum(1 for device in Device.query.all() if device.is_online)
    
    total_assignments = Assignment.query.count()
    
    # Recent videos
    recent_videos = Video.query.order_by(Video.uploaded_at.desc()).limit(5).all()
    
    # Recent device activity
    recent_devices = Device.query.order_by(Device.last_seen.desc().nullslast()).limit(5).all()
    
    # Storage usage
    total_storage = sum(video.size for video in Video.query.all())
    
    return render_template('index.html',
                         total_videos=total_videos,
                         total_devices=total_devices,
                         online_devices=online_devices,
                         total_assignments=total_assignments,
                         recent_videos=recent_videos,
                         recent_devices=recent_devices,
                         total_storage=total_storage)


# ============================================================================
# VIDEO MANAGEMENT
# ============================================================================

@admin_bp.route('/videos')
@login_required
def videos():
    """List all videos with search, filter, and sort"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get search query
    search = request.args.get('search', '').strip()
    
    # Get filter parameters
    resolution_filter = request.args.get('resolution', '')
    size_filter = request.args.get('size', '')
    date_filter = request.args.get('date', '')
    
    # Get sort parameters
    sort_by = request.args.get('sort', 'uploaded_at')
    sort_dir = request.args.get('dir', 'desc')
    
    # Build query
    query = Video.query
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Video.title.ilike(f'%{search}%'),
                Video.filename.ilike(f'%{search}%'),
                Video.description.ilike(f'%{search}%')
            )
        )
    
    # Apply resolution filter
    if resolution_filter:
        if resolution_filter == '4k':
            query = query.filter(Video.height >= 2160)
        elif resolution_filter == '1080p':
            query = query.filter(Video.height >= 1080, Video.height < 2160)
        elif resolution_filter == '720p':
            query = query.filter(Video.height >= 720, Video.height < 1080)
        elif resolution_filter == 'sd':
            query = query.filter(Video.height < 720)
    
    # Apply size filter
    if size_filter:
        if size_filter == 'large':
            query = query.filter(Video.size > 500 * 1024 * 1024)  # > 500 MB
        elif size_filter == 'medium':
            query = query.filter(Video.size > 100 * 1024 * 1024, Video.size <= 500 * 1024 * 1024)  # 100-500 MB
        elif size_filter == 'small':
            query = query.filter(Video.size <= 100 * 1024 * 1024)  # <= 100 MB
    
    # Apply date filter
    if date_filter:
        from datetime import datetime, timedelta
        today = datetime.now()
        if date_filter == 'today':
            query = query.filter(Video.uploaded_at >= today.replace(hour=0, minute=0, second=0))
        elif date_filter == 'week':
            query = query.filter(Video.uploaded_at >= today - timedelta(days=7))
        elif date_filter == 'month':
            query = query.filter(Video.uploaded_at >= today - timedelta(days=30))
    
    # Apply sorting
    sort_column = getattr(Video, sort_by, Video.uploaded_at)
    if sort_dir == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Paginate results
    videos_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all tags and categories for filters
    all_tags = Tag.query.order_by(Tag.name).all()
    all_categories = Category.query.order_by(Category.name).all()
    
    return render_template('upload.html', 
                         videos=videos_pagination,
                         search=search,
                         resolution_filter=resolution_filter,
                         size_filter=size_filter,
                         date_filter=date_filter,
                         sort_by=sort_by,
                         sort_dir=sort_dir,
                         all_tags=all_tags,
                         all_categories=all_categories)


@admin_bp.route('/videos/upload', methods=['POST'])
@login_required
@content_manager_required
def upload_video():
    """Handle video upload - Admin/Operator only"""
    
    if 'video' not in request.files:
        flash('No video file selected.', 'danger')
        return redirect(url_for('admin.videos'))
    
    file = request.files['video']
    
    if file.filename == '':
        flash('No video file selected.', 'danger')
        return redirect(url_for('admin.videos'))
    
    # Validate file extension
    if not allowed_file(file.filename):
        flash(f'Invalid file type. Allowed types: {", ".join(current_app.config["ALLOWED_EXTENSIONS"])}', 'danger')
        return redirect(url_for('admin.videos'))
    
    # Secure the filename
    filename = secure_filename(file.filename)  # type: ignore
    
    # Make filename unique if it already exists
    base, ext = os.path.splitext(filename)
    counter = 1
    while Video.query.filter_by(filename=filename).first():
        filename = f"{base}_{counter}{ext}"
        counter += 1
    
    # Save file
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Get file size
    file_size = os.path.getsize(filepath)
    
    # Get title from form or use filename
    title = request.form.get('title', base)
    description = request.form.get('description', '')
    
    # Extract video metadata
    metadata = {}
    try:
        metadata = extract_video_metadata(filepath)
        current_app.logger.info(f'Extracted metadata for {filename}: {metadata}')
    except VideoProcessingError as e:
        current_app.logger.warning(f'Failed to extract metadata for {filename}: {e}')
        # Continue without metadata
    
    # Calculate file checksum
    checksum = None
    try:
        from utils.video_utils import calculate_checksum
        checksum = calculate_checksum(filepath)
        current_app.logger.info(f'Calculated checksum for {filename}: {checksum[:16]}...')
    except Exception as e:
        current_app.logger.warning(f'Failed to calculate checksum for {filename}: {e}')
        # Continue without checksum
    
    # Create video record with metadata
    video = Video(
        filename=filename,
        title=title,
        description=description,
        size=file_size,
        mimetype=file.content_type,
        duration=metadata.get('duration'),
        width=metadata.get('width'),
        height=metadata.get('height'),
        codec=metadata.get('codec'),
        bitrate=metadata.get('bitrate'),
        framerate=metadata.get('framerate'),
        video_format=metadata.get('format'),
        checksum=checksum
    )
    
    db.session.add(video)
    db.session.commit()
    
    # Generate thumbnail
    try:
        thumbnail_path = get_thumbnail_path(filename, current_app.config['THUMBNAIL_FOLDER'])
        if generate_thumbnail(filepath, thumbnail_path):
            video.has_thumbnail = True
            db.session.commit()
            current_app.logger.info(f'Generated thumbnail for {filename}')
    except VideoProcessingError as e:
        current_app.logger.warning(f'Failed to generate thumbnail for {filename}: {e}')
        # Continue without thumbnail
    
    # Handle tags
    tag_ids = request.form.getlist('tags')
    if tag_ids:
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        video.tags.extend(tags)
    
    # Handle categories
    category_ids = request.form.getlist('categories')
    if category_ids:
        categories = Category.query.filter(Category.id.in_(category_ids)).all()
        video.categories.extend(categories)
    
    db.session.commit()
    
    log_activity('upload_video', 'video', video.id, {
        'filename': filename,
        'title': title,
        'size_bytes': file_size,
        'tags': len(tag_ids),
        'categories': len(category_ids)
    })
    
    # Create upload complete notification
    from utils.notifications import NotificationService
    NotificationService.create_upload_complete_alert(current_user.id, title)
    
    current_app.logger.info(f'Video uploaded: {filename} by user {current_user.username}')
    flash(f'Video "{title}" uploaded successfully!', 'success')
    
    return redirect(url_for('admin.videos'))


@admin_bp.route('/videos/delete/<int:video_id>', methods=['POST'])
@login_required
@content_manager_required
def delete_video(video_id):
    """Delete a video and its thumbnail - Admin/Operator only"""
    video = Video.query.get_or_404(video_id)
    
    video_title = video.title
    video_filename = video.filename
    
    # Delete video file from filesystem
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete thumbnail if it exists
    if video.has_thumbnail:
        thumbnail_path = get_thumbnail_path(video.filename, current_app.config['THUMBNAIL_FOLDER'])
        delete_thumbnail(thumbnail_path)
    
    # Delete from database (cascade will handle assignments)
    db.session.delete(video)
    db.session.commit()
    
    log_activity('delete_video', 'video', video_id, {
        'title': video_title,
        'filename': video_filename
    })
    
    current_app.logger.info(f'Video deleted: {video_filename} by user {current_user.username}')
    flash(f'Video "{video_title}" deleted successfully.', 'success')
    
    return redirect(url_for('admin.videos'))


@admin_bp.route('/thumbnails/<path:filename>')
@login_required
def serve_thumbnail(filename):
    """Serve video thumbnail images"""
    return send_from_directory(current_app.config['THUMBNAIL_FOLDER'], filename)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


# ============================================================================
# DEVICE MANAGEMENT
# ============================================================================

@admin_bp.route('/devices')
@login_required
def devices():
    """List all devices with search, filter, and sort"""
    # Get search query
    search = request.args.get('search', '').strip()
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    online_filter = request.args.get('online', '')
    
    # Get sort parameters
    sort_by = request.args.get('sort', 'name')
    sort_dir = request.args.get('dir', 'asc')
    
    # Build query
    query = Device.query
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                Device.name.ilike(f'%{search}%'),
                Device.serial.ilike(f'%{search}%'),
                Device.location.ilike(f'%{search}%')
            )
        )
    
    # Apply status filter
    if status_filter == 'active':
        query = query.filter(Device.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(Device.is_active == False)
    
    # Apply online filter
    if online_filter == 'online':
        query = query.filter(Device.is_online == True)
    elif online_filter == 'offline':
        query = query.filter(Device.is_online == False)
    
    # Apply sorting
    sort_column = getattr(Device, sort_by, Device.name)
    if sort_dir == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    devices_list = query.all()
    
    return render_template('devices.html', 
                         devices=devices_list,
                         search=search,
                         status_filter=status_filter,
                         online_filter=online_filter,
                         sort_by=sort_by,
                         sort_dir=sort_dir)


@admin_bp.route('/devices/add', methods=['POST'])
@login_required
@device_manager_required
def add_device():
    """Manually add a device - Admin/Operator only"""
    name = request.form.get('name')
    serial = request.form.get('serial')
    
    if not name or not serial:
        flash('Device name and serial are required.', 'danger')
        return redirect(url_for('admin.devices'))
    
    # Check if serial already exists
    if Device.query.filter_by(serial=serial).first():
        flash(f'Device with serial "{serial}" already exists.', 'danger')
        return redirect(url_for('admin.devices'))
    
    # Generate API key
    api_key = Device.generate_api_key()
    
    # Create device
    device = Device(
        name=name,
        serial=serial,
        api_key_hash=Device.hash_api_key(api_key)
    )
    
    db.session.add(device)
    db.session.commit()
    
    current_app.logger.info(f'Device added: {serial} by user {current_user.username}')
    flash(f'Device "{name}" added. API Key: {api_key} (save this key, it won\'t be shown again!)', 'success')
    
    return redirect(url_for('admin.devices'))


@admin_bp.route('/devices/delete/<int:device_id>', methods=['POST'])
@login_required
@device_manager_required
def delete_device(device_id):
    """Delete a device - Admin/Operator only"""
    device = Device.query.get_or_404(device_id)
    
    device_name = device.name
    db.session.delete(device)
    db.session.commit()
    
    current_app.logger.info(f'Device deleted: {device.serial} by user {current_user.username}')
    flash(f'Device "{device_name}" deleted successfully.', 'success')
    
    return redirect(url_for('admin.devices'))


@admin_bp.route('/devices/regenerate-key/<int:device_id>', methods=['POST'])
@login_required
def regenerate_device_key(device_id):
    """Regenerate API key for a device"""
    device = Device.query.get_or_404(device_id)
    
    # Generate new API key
    new_api_key = Device.generate_api_key()
    device.api_key_hash = Device.hash_api_key(new_api_key)
    
    db.session.commit()
    
    current_app.logger.info(f'API key regenerated for device: {device.serial} by user {current_user.username}')
    flash(f'New API Key for "{device.name}": {new_api_key} (save this key, it won\'t be shown again!)', 'warning')
    
    return redirect(url_for('admin.devices'))


@admin_bp.route('/devices/<int:device_id>/command', methods=['POST'])
@login_required
@device_manager_required
def send_device_command(device_id):
    """Send a remote command to a device - Admin/Operator only"""
    from models import DeviceCommand
    
    device = Device.query.get_or_404(device_id)
    command_type = request.form.get('command_type')
    
    if not command_type:
        flash('Command type is required', 'danger')
        return redirect(url_for('admin.devices'))
    
    valid_commands = ['restart', 'update', 'clear_cache', 'sync_now']
    if command_type not in valid_commands:
        flash(f'Invalid command type. Must be one of: {", ".join(valid_commands)}', 'danger')
        return redirect(url_for('admin.devices'))
    
    # Create command
    command = DeviceCommand(
        device_id=device.id,
        command_type=command_type,
        status='pending'
    )
    db.session.add(command)
    db.session.commit()
    
    command_names = {
        'restart': 'Restart Device',
        'update': 'Update Player',
        'clear_cache': 'Clear Cache',
        'sync_now': 'Force Sync'
    }
    
    current_app.logger.info(f'Command "{command_type}" sent to device {device.serial} by user {current_user.username}')
    flash(f'Command "{command_names.get(command_type, command_type)}" sent to device "{device.name}"', 'success')
    
    return redirect(url_for('admin.devices'))


@admin_bp.route('/devices/<int:device_id>/commands')
@login_required
def device_commands(device_id):
    """View command history for a device"""
    from models import DeviceCommand
    
    device = Device.query.get_or_404(device_id)
    commands = DeviceCommand.query.filter_by(device_id=device.id).order_by(DeviceCommand.created_at.desc()).limit(50).all()
    
    return render_template('device_commands.html', device=device, commands=commands)


# ============================================================================
# ASSIGNMENT MANAGEMENT
# ============================================================================

@admin_bp.route('/assignments')
@login_required
def assignments():
    """Manage video/playlist assignments to devices"""
    devices_list = Device.query.order_by(Device.name).all()
    videos_list = Video.query.order_by(Video.title).all()
    playlists_list = Playlist.query.filter_by(is_active=True).order_by(Playlist.name).all()
    
    # Get all assignments with relationships
    assignments_list = Assignment.query.all()
    
    return render_template('assignments.html',
                         devices=devices_list,
                         videos=videos_list,
                         playlists=playlists_list,
                         assignments=assignments_list)


@admin_bp.route('/assignments/assign', methods=['POST'])
@login_required
def assign_video():
    """Assign video(s) or playlist(s) to device(s)"""
    device_ids = request.form.getlist('device_ids')
    content_type = request.form.get('content_type', 'video')
    
    if content_type == 'video':
        content_ids = request.form.getlist('video_ids')
        content_field = 'video_id'
        content_name = 'video'
    else:
        content_ids = request.form.getlist('playlist_ids')
        content_field = 'playlist_id'
        content_name = 'playlist'
    
    if not device_ids or not content_ids:
        flash(f'Please select at least one device and one {content_name}.', 'danger')
        return redirect(url_for('admin.assignments'))
    
    # Convert to integers
    device_ids = [int(d_id) for d_id in device_ids]
    content_ids = [int(c_id) for c_id in content_ids]
    
    # Get scheduling parameters
    enable_schedule = request.form.get('enable_schedule') == '1'
    start_time = None
    end_time = None
    days_of_week = None
    
    if enable_schedule:
        # Parse time fields
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        if start_time_str:
            from datetime import datetime
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        if end_time_str:
            from datetime import datetime
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Get selected days
        days = []
        if request.form.get('days_monday'):
            days.append('0')
        if request.form.get('days_tuesday'):
            days.append('1')
        if request.form.get('days_wednesday'):
            days.append('2')
        if request.form.get('days_thursday'):
            days.append('3')
        if request.form.get('days_friday'):
            days.append('4')
        if request.form.get('days_saturday'):
            days.append('5')
        if request.form.get('days_sunday'):
            days.append('6')
        
        if days:
            days_of_week = ','.join(days)
    
    assignments_created = 0
    assignments_skipped = 0
    
    for device_id in device_ids:
        # Clear existing assignments for this device first
        Assignment.query.filter_by(device_id=device_id).delete()
        
        for content_id in content_ids:
            # Create new assignment
            if content_type == 'video':
                assignment = Assignment(
                    device_id=device_id,
                    video_id=content_id,
                    playlist_id=None,
                    start_time=start_time,
                    end_time=end_time,
                    days_of_week=days_of_week
                )
            else:
                assignment = Assignment(
                    device_id=device_id,
                    video_id=None,
                    playlist_id=content_id,
                    start_time=start_time,
                    end_time=end_time,
                    days_of_week=days_of_week
                )
            
            db.session.add(assignment)
            assignments_created += 1
    
    db.session.commit()
    
    current_app.logger.info(f'Assignments created: {assignments_created} by user {current_user.username}')
    flash(f'Created {assignments_created} {content_name} assignment(s).', 'success')
    
    return redirect(url_for('admin.assignments'))


@admin_bp.route('/assignments/delete/<int:assignment_id>', methods=['POST'])
@login_required
@content_manager_required
def delete_assignment(assignment_id):
    """Delete an assignment - Admin/Operator only"""
    assignment = Assignment.query.get_or_404(assignment_id)
    
    db.session.delete(assignment)
    db.session.commit()
    
    current_app.logger.info(f'Assignment deleted: {assignment_id} by user {current_user.username}')
    flash('Assignment deleted successfully.', 'success')
    
    return redirect(url_for('admin.assignments'))


@admin_bp.route('/assignments/clear-device/<int:device_id>', methods=['POST'])
@login_required
def clear_device_assignments(device_id):
    """Clear all assignments for a device"""
    device = Device.query.get_or_404(device_id)
    
    count = Assignment.query.filter_by(device_id=device_id).delete()
    db.session.commit()
    
    current_app.logger.info(f'Cleared {count} assignment(s) for device: {device.serial} by user {current_user.username}')
    flash(f'Cleared {count} assignment(s) for device "{device.name}".', 'success')
    
    return redirect(url_for('admin.assignments'))


# ============================================================================
# STORAGE MANAGEMENT (Phase 3.5)
# ============================================================================

@admin_bp.route('/monitoring')
@login_required
def realtime_monitoring():
    """Real-time device monitoring dashboard (Phase 4.1)"""
    devices = Device.query.all()
    return render_template('realtime_dashboard.html', devices=devices)


@admin_bp.route('/storage')
@login_required
def storage_management():
    """Storage management dashboard"""
    from utils.storage_management import get_storage_statistics, find_unused_videos, find_old_videos, find_large_videos
    
    # Get storage statistics
    stats = get_storage_statistics()
    
    # Find problematic videos
    unused_videos = find_unused_videos(days_threshold=30)
    old_videos = find_old_videos(days_threshold=90)
    large_videos = find_large_videos(size_threshold_mb=100)
    
    return render_template('storage_management.html',
                          stats=stats,
                          unused_videos=unused_videos,
                          old_videos=old_videos,
                          large_videos=large_videos)


@admin_bp.route('/storage/cleanup', methods=['POST'])
@login_required
def storage_cleanup():
    """Bulk delete videos"""
    from utils.storage_management import delete_videos_bulk, calculate_potential_space_savings
    
    video_ids = request.form.getlist('video_ids', type=int)
    
    if not video_ids:
        flash('No videos selected for deletion', 'warning')
        return redirect(url_for('admin.storage_management'))
    
    # Calculate space savings
    savings = calculate_potential_space_savings(video_ids)
    
    # Perform deletion
    result = delete_videos_bulk(
        video_ids,
        delete_files=True,
        video_folder=current_app.config['UPLOAD_FOLDER'],
        thumbnail_folder=current_app.config['THUMBNAIL_FOLDER']
    )
    
    if result['deleted'] > 0:
        flash(f'Successfully deleted {result["deleted"]} video(s), freed {savings["total_size_gb"]:.2f} GB', 'success')
    
    if result['failed'] > 0:
        flash(f'Failed to delete {result["failed"]} video(s). Check logs for details.', 'danger')
        for error in result['errors']:
            current_app.logger.error(f'Storage cleanup error: {error}')
    
    current_app.logger.info(f'Storage cleanup by user {current_user.username}: deleted {result["deleted"]}, failed {result["failed"]}')
    
    return redirect(url_for('admin.storage_management'))


@admin_bp.route('/storage/analyze/<int:video_id>')
@login_required
def analyze_video_usage(video_id):
    """Analyze detailed usage for a specific video"""
    from utils.storage_management import get_video_usage_info
    
    usage_info = get_video_usage_info(video_id)
    
    if not usage_info:
        flash('Video not found', 'danger')
        return redirect(url_for('admin.storage_management'))
    
    return jsonify(usage_info)


# ============================================================================
# USER MANAGEMENT ROUTES (Phase 4.2)
# ============================================================================

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users - Admin only"""
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users_list)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user - Admin only"""
    form = UserCreateForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data if form.email.data else None,
            role=UserRole[form.role.data],
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        log_activity('create_user', 'user', user.id, {
            'username': user.username,
            'role': user.role.value
        })
        
        flash(f'User {user.username} created successfully', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('user_create.html', form=form)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user - Admin only"""
    user = User.query.get_or_404(user_id)
    
    form = UserEditForm(
        original_username=user.username,
        original_email=user.email
    )
    
    if form.validate_on_submit():
        old_role = user.role.value
        
        user.username = form.username.data
        user.email = form.email.data if form.email.data else None
        user.role = UserRole[form.role.data]
        user.is_active = form.is_active.data
        
        db.session.commit()
        
        log_activity('edit_user', 'user', user.id, {
            'username': user.username,
            'role_changed': old_role != user.role.value,
            'new_role': user.role.value
        })
        
        flash(f'User {user.username} updated successfully', 'success')
        return redirect(url_for('admin.users'))
    
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role.name
        form.is_active.data = user.is_active
    
    return render_template('user_edit.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user - Admin only"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = User.query.filter_by(role=UserRole.ADMIN, is_active=True).count()
        if admin_count <= 1:
            flash('Cannot delete the last admin user', 'danger')
            return redirect(url_for('admin.users'))
    
    username = user.username
    
    log_activity('delete_user', 'user', user.id, {
        'username': username,
        'role': user.role.value
    })
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status - Admin only"""
    user = User.query.get_or_404(user_id)
    
    # Prevent disabling yourself
    if user.id == current_user.id:
        flash('You cannot disable your own account', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'enabled' if user.is_active else 'disabled'
    log_activity('toggle_user_status', 'user', user.id, {
        'username': user.username,
        'status': status
    })
    
    flash(f'User {user.username} {status}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change own password"""
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        log_activity('change_password', details={'self': True})
        
        flash('Password changed successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('change_password.html', form=form)


@admin_bp.route('/users/<int:user_id>/activity')
@login_required
@admin_required
def user_activity(user_id):
    """View user activity log - Admin only"""
    user = User.query.get_or_404(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    activities = UserActivity.query.filter_by(user_id=user_id)\
        .order_by(UserActivity.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('user_activity.html', user=user, activities=activities)


# ============================================================================
# SCHEDULING ROUTES (Phase 4.3)
# ============================================================================

@admin_bp.route('/schedules')
@login_required
def schedules():
    """List all content schedules"""
    from models import Schedule
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    schedules = Schedule.query\
        .order_by(Schedule.start_time.asc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('schedules.html', schedules=schedules)


@admin_bp.route('/schedules/create', methods=['GET', 'POST'])
@login_required
@content_manager_required
def create_schedule():
    """Create new content schedule"""
    from models import Schedule, Playlist, Video
    from forms import ScheduleCreateForm
    from datetime import datetime
    
    form = ScheduleCreateForm()
    
    # Populate device choices
    devices = Device.query.filter_by(is_active=True).order_by(Device.name).all()
    form.device_id.choices = [(d.id, d.name) for d in devices]
    
    # Populate content choices based on selected type
    if request.method == 'POST' or request.args.get('content_type'):
        content_type = form.content_type.data or request.args.get('content_type')
        if content_type == 'video':
            videos = Video.query.order_by(Video.title).all()
            form.content_id.choices = [(v.id, v.title) for v in videos]
        else:
            playlists = Playlist.query.order_by(Playlist.name).all()
            form.content_id.choices = [(p.id, p.name) for p in playlists]
    else:
        form.content_id.choices = []
    
    if form.validate_on_submit():
        # Parse date fields if provided
        start_date = None
        end_date = None
        recurrence_end_date = None
        
        if form.start_date.data:
            try:
                start_date = datetime.strptime(form.start_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format. Use YYYY-MM-DD', 'danger')
                return render_template('schedule_create.html', form=form)
        
        if form.end_date.data:
            try:
                end_date = datetime.strptime(form.end_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid end date format. Use YYYY-MM-DD', 'danger')
                return render_template('schedule_create.html', form=form)
        
        if form.recurrence_end_date.data:
            try:
                recurrence_end_date = datetime.strptime(form.recurrence_end_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid recurrence end date format. Use YYYY-MM-DD', 'danger')
                return render_template('schedule_create.html', form=form)
        
        # Convert days_of_week list to comma-separated string
        days_of_week = ','.join(form.days_of_week.data) if form.days_of_week.data else None
        
        # Determine content references
        video_id = None
        playlist_id = None
        if form.content_type.data == 'video':
            video_id = form.content_id.data
        else:
            playlist_id = form.content_id.data
        
        # Create schedule name from content
        if form.content_type.data == 'video':
            video = Video.query.get(form.content_id.data)
            schedule_name = f"{video.title} - {form.start_time.data.strftime('%H:%M')}-{form.end_time.data.strftime('%H:%M')}"
        else:
            playlist = Playlist.query.get(form.content_id.data)
            schedule_name = f"{playlist.name} - {form.start_time.data.strftime('%H:%M')}-{form.end_time.data.strftime('%H:%M')}"
        
        schedule = Schedule(
            name=schedule_name,
            device_id=form.device_id.data,
            video_id=video_id,
            playlist_id=playlist_id,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            start_date=start_date,
            end_date=end_date,
            days_of_week=days_of_week,
            priority=form.priority.data,
            is_recurring=(form.recurrence_type.data != 'NONE'),
            recurrence_type=form.recurrence_type.data.lower() if form.recurrence_type.data else 'weekly',
            recurrence_interval=form.recurrence_interval.data or 1,
            recurrence_end_date=recurrence_end_date,
            is_all_day=form.is_all_day.data,
            color=form.color.data or '#3788d8',
            is_active=form.is_active.data,
            created_by=current_user.id
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        log_activity('create_schedule', 'schedule', schedule.id, 
                    f'Created schedule for {schedule.device.name}')
        
        flash('Schedule created successfully!', 'success')
        return redirect(url_for('admin.schedules'))
    
    return render_template('schedule_create.html', form=form)


@admin_bp.route('/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
@content_manager_required
def edit_schedule(schedule_id):
    """Edit existing schedule"""
    from models import Schedule, Playlist, Video
    from forms import ScheduleEditForm
    from datetime import datetime
    
    schedule = Schedule.query.get_or_404(schedule_id)
    form = ScheduleEditForm(obj=schedule)
    
    # Populate device choices
    devices = Device.query.filter_by(is_active=True).order_by(Device.name).all()
    form.device_id.choices = [(d.id, d.name) for d in devices]
    
    # Populate content choices
    if form.content_type.data == 'video':
        videos = Video.query.order_by(Video.title).all()
        form.content_id.choices = [(v.id, v.title) for v in videos]
    else:
        playlists = Playlist.query.order_by(Playlist.name).all()
        form.content_id.choices = [(p.id, p.name) for p in playlists]
    
    if request.method == 'GET':
        # Pre-populate form fields
        form.device_id.data = schedule.device_id
        form.content_type.data = 'video' if schedule.video_id else 'playlist'
        form.content_id.data = schedule.video_id if schedule.video_id else schedule.playlist_id
        form.start_time.data = schedule.start_time
        form.end_time.data = schedule.end_time
        form.start_date.data = schedule.start_date.strftime('%Y-%m-%d') if schedule.start_date else ''
        form.end_date.data = schedule.end_date.strftime('%Y-%m-%d') if schedule.end_date else ''
        form.days_of_week.data = schedule.days_of_week.split(',') if schedule.days_of_week else []
        form.priority.data = schedule.priority
        form.recurrence_type.data = 'NONE' if not schedule.is_recurring else 'DAILY'
        form.recurrence_interval.data = 1
        form.recurrence_end_date.data = ''
        form.is_active.data = schedule.is_active
    
    if form.validate_on_submit():
        # Parse date fields
        start_date = None
        end_date = None
        recurrence_end_date = None
        
        if form.start_date.data:
            try:
                start_date = datetime.strptime(form.start_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format. Use YYYY-MM-DD', 'danger')
                return render_template('schedule_edit.html', form=form, schedule=schedule)
        
        if form.end_date.data:
            try:
                end_date = datetime.strptime(form.end_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid end date format. Use YYYY-MM-DD', 'danger')
                return render_template('schedule_edit.html', form=form, schedule=schedule)
        
        if form.recurrence_end_date.data:
            try:
                recurrence_end_date = datetime.strptime(form.recurrence_end_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid recurrence end date format. Use YYYY-MM-DD', 'danger')
                return render_template('schedule_edit.html', form=form, schedule=schedule)
        
        # Update schedule
        schedule.device_id = form.device_id.data
        
        # Update content references
        if form.content_type.data == 'video':
            schedule.video_id = form.content_id.data
            schedule.playlist_id = None
        else:
            schedule.playlist_id = form.content_id.data
            schedule.video_id = None
        
        schedule.start_time = form.start_time.data
        schedule.end_time = form.end_time.data
        schedule.start_date = start_date
        schedule.end_date = end_date
        schedule.days_of_week = ','.join(form.days_of_week.data) if form.days_of_week.data else None
        schedule.priority = form.priority.data
        schedule.is_recurring = (form.recurrence_type.data != 'NONE')
        schedule.recurrence_type = form.recurrence_type.data.lower() if form.recurrence_type.data else 'weekly'
        schedule.recurrence_interval = form.recurrence_interval.data or 1
        schedule.recurrence_end_date = recurrence_end_date
        schedule.is_all_day = form.is_all_day.data
        schedule.color = form.color.data or '#3788d8'
        schedule.is_active = form.is_active.data
        
        db.session.commit()
        
        log_activity('edit_schedule', 'schedule', schedule.id,
                    f'Updated schedule for {schedule.device.name}')
        
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('admin.schedules'))
    
    return render_template('schedule_edit.html', form=form, schedule=schedule)


@admin_bp.route('/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required
@content_manager_required
def delete_schedule(schedule_id):
    """Delete a schedule"""
    from models import Schedule
    
    schedule = Schedule.query.get_or_404(schedule_id)
    device_name = schedule.device.name
    
    db.session.delete(schedule)
    db.session.commit()
    
    log_activity('delete_schedule', 'schedule', schedule_id,
                f'Deleted schedule for {device_name}')
    
    flash('Schedule deleted successfully!', 'success')
    return redirect(url_for('admin.schedules'))


@admin_bp.route('/schedules/<int:schedule_id>/toggle', methods=['POST'])
@login_required
@content_manager_required
def toggle_schedule(schedule_id):
    """Toggle schedule active status"""
    from models import Schedule
    
    schedule = Schedule.query.get_or_404(schedule_id)
    schedule.is_active = not schedule.is_active
    db.session.commit()
    
    status = 'activated' if schedule.is_active else 'deactivated'
    log_activity('toggle_schedule', 'schedule', schedule_id,
                f'{status.capitalize()} schedule for {schedule.device.name}')
    
    flash(f'Schedule {status}!', 'success')
    return redirect(url_for('admin.schedules'))


@admin_bp.route('/schedules/calendar')
@login_required
def schedule_calendar():
    """Calendar view of schedules (Phase 5)"""
    from models import Device, DeviceGroup
    
    devices = Device.query.order_by(Device.name).all()
    device_groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    
    return render_template('schedule_calendar.html', 
                         devices=devices,
                         device_groups=device_groups)


@admin_bp.route('/schedules/calendar/events')
@login_required
def schedule_calendar_events():
    """Get calendar events for FullCalendar (Phase 5)"""
    from datetime import datetime, timedelta
    from utils.schedule_utils import generate_calendar_events
    
    # Get date range from query parameters
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    device_id = request.args.get('device_id', type=int)
    device_group_id = request.args.get('device_group_id', type=int)
    
    try:
        start_date = datetime.fromisoformat(start_str.replace('Z', '')).date()
        end_date = datetime.fromisoformat(end_str.replace('Z', '')).date()
    except (ValueError, AttributeError):
        # Default to current month
        today = datetime.now().date()
        start_date = today.replace(day=1)
        # Get last day of month
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    events = generate_calendar_events(start_date, end_date, device_id, device_group_id)
    
    return jsonify(events)


@admin_bp.route('/schedules/<int:schedule_id>/conflicts')
@login_required
def check_schedule_conflicts(schedule_id):
    """Check for schedule conflicts (Phase 5)"""
    from models import Schedule
    from utils.schedule_utils import get_schedule_conflicts
    from datetime import date
    
    schedule = Schedule.query.get_or_404(schedule_id)
    conflicts = get_schedule_conflicts(schedule, date.today())
    
    return jsonify({
        'has_conflicts': len(conflicts) > 0,
        'conflict_count': len(conflicts),
        'conflicts': [c.to_dict() for c in conflicts]
    })


@admin_bp.route('/schedules/preview')
@login_required
def schedule_preview():
    """Preview schedule timeline for a device (Phase 5)"""
    from models import Device
    from utils.schedule_utils import get_schedule_preview
    from datetime import datetime, date
    
    device_id = request.args.get('device_id', type=int)
    preview_date_str = request.args.get('date')
    
    if not device_id:
        return jsonify({'error': 'device_id is required'}), 400
    
    device = Device.query.get_or_404(device_id)
    
    try:
        preview_date = datetime.strptime(preview_date_str, '%Y-%m-%d').date() if preview_date_str else date.today()
    except ValueError:
        preview_date = date.today()
    
    timeline = get_schedule_preview(device_id, preview_date)
    
    return jsonify({
        'device_id': device.id,
        'device_name': device.name,
        'preview_date': preview_date.isoformat(),
        'timeline': timeline
    })


# ============================================================================
# TAGS & CATEGORIES ROUTES (Phase 4.4)
# ============================================================================

@admin_bp.route('/tags')
@login_required
def tags():
    """List all tags"""
    from models import Tag
    tags_list = Tag.query.order_by(Tag.name).all()
    return render_template('tags.html', tags=tags_list)


@admin_bp.route('/tags/create', methods=['POST'])
@login_required
@content_manager_required
def create_tag():
    """Create new tag"""
    from models import Tag
    
    name = request.form.get('name', '').strip()
    color = request.form.get('color', '#6c757d')
    
    if not name:
        flash('Tag name is required', 'danger')
        return redirect(url_for('admin.tags'))
    
    # Check if tag already exists
    existing = Tag.query.filter_by(name=name).first()
    if existing:
        flash(f'Tag "{name}" already exists', 'warning')
        return redirect(url_for('admin.tags'))
    
    tag = Tag(name=name, color=color, created_by_id=current_user.id)
    db.session.add(tag)
    db.session.commit()
    
    log_activity('create_tag', 'tag', tag.id, f'Created tag: {name}')
    flash(f'Tag "{name}" created successfully!', 'success')
    return redirect(url_for('admin.tags'))


@admin_bp.route('/tags/<int:tag_id>/edit', methods=['POST'])
@login_required
@content_manager_required
def edit_tag(tag_id):
    """Edit tag"""
    from models import Tag
    
    tag = Tag.query.get_or_404(tag_id)
    name = request.form.get('name', '').strip()
    color = request.form.get('color', tag.color)
    
    if not name:
        flash('Tag name is required', 'danger')
        return redirect(url_for('admin.tags'))
    
    # Check if new name conflicts with existing tag
    if name != tag.name:
        existing = Tag.query.filter_by(name=name).first()
        if existing:
            flash(f'Tag "{name}" already exists', 'warning')
            return redirect(url_for('admin.tags'))
    
    old_name = tag.name
    tag.name = name
    tag.color = color
    db.session.commit()
    
    log_activity('edit_tag', 'tag', tag_id, f'Updated tag from "{old_name}" to "{name}"')
    flash(f'Tag updated successfully!', 'success')
    return redirect(url_for('admin.tags'))


@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
@content_manager_required
def delete_tag(tag_id):
    """Delete tag"""
    from models import Tag
    
    tag = Tag.query.get_or_404(tag_id)
    tag_name = tag.name
    usage_count = tag.total_usage
    
    db.session.delete(tag)
    db.session.commit()
    
    log_activity('delete_tag', 'tag', tag_id, f'Deleted tag "{tag_name}" (used {usage_count} times)')
    flash(f'Tag "{tag_name}" deleted successfully!', 'success')
    return redirect(url_for('admin.tags'))


@admin_bp.route('/categories')
@login_required
def categories():
    """List all categories"""
    from models import Category
    categories_list = Category.query.order_by(Category.name).all()
    return render_template('categories.html', categories=categories_list)


@admin_bp.route('/categories/create', methods=['POST'])
@login_required
@admin_required
def create_category():
    """Create new category"""
    from models import Category
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', '#0d6efd')
    icon = request.form.get('icon', '')
    parent_id = request.form.get('parent_id')
    
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('admin.categories'))
    
    # Check if category already exists
    existing = Category.query.filter_by(name=name).first()
    if existing:
        flash(f'Category "{name}" already exists', 'warning')
        return redirect(url_for('admin.categories'))
    
    category = Category(
        name=name,
        description=description,
        color=color,
        icon=icon,
        parent_id=int(parent_id) if parent_id and parent_id != '' else None,
        created_by_id=current_user.id
    )
    db.session.add(category)
    db.session.commit()
    
    log_activity('create_category', 'category', category.id, f'Created category: {name}')
    flash(f'Category "{name}" created successfully!', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<int:category_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Edit category"""
    from models import Category
    
    category = Category.query.get_or_404(category_id)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    color = request.form.get('color', category.color)
    icon = request.form.get('icon', category.icon)
    parent_id = request.form.get('parent_id')
    
    if not name:
        flash('Category name is required', 'danger')
        return redirect(url_for('admin.categories'))
    
    # Check if new name conflicts with existing category
    if name != category.name:
        existing = Category.query.filter_by(name=name).first()
        if existing:
            flash(f'Category "{name}" already exists', 'warning')
            return redirect(url_for('admin.categories'))
    
    # Prevent circular parent relationships
    if parent_id and int(parent_id) == category_id:
        flash('Category cannot be its own parent', 'danger')
        return redirect(url_for('admin.categories'))
    
    old_name = category.name
    category.name = name
    category.description = description
    category.color = color
    category.icon = icon
    category.parent_id = int(parent_id) if parent_id and parent_id != '' else None
    db.session.commit()
    
    log_activity('edit_category', 'category', category_id, f'Updated category from "{old_name}" to "{name}"')
    flash(f'Category updated successfully!', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Delete category"""
    from models import Category
    
    category = Category.query.get_or_404(category_id)
    category_name = category.name
    usage_count = category.total_usage
    
    # Check if category has subcategories
    if category.subcategories:
        flash(f'Cannot delete category "{category_name}" - it has {len(category.subcategories)} subcategories', 'danger')
        return redirect(url_for('admin.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    log_activity('delete_category', 'category', category_id, 
                f'Deleted category "{category_name}" (used {usage_count} times)')
    flash(f'Category "{category_name}" deleted successfully!', 'success')
    return redirect(url_for('admin.categories'))


# ============================================================================
# BACKUP & RESTORE ROUTES (Phase 4.5)
# ============================================================================

@admin_bp.route('/backup')
@login_required
@admin_required
def backup_restore():
    """Backup and restore management page"""
    from utils.backup import BackupManager
    
    try:
        backup_manager = BackupManager()
        backups = backup_manager.list_backups()
        stats = backup_manager.get_backup_stats()
    except Exception as e:
        current_app.logger.error(f'Error loading backups: {e}')
        backups = []
        stats = {}
    
    return render_template('backup_restore.html', backups=backups, stats=stats)


@admin_bp.route('/backup/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Create a new backup"""
    from utils.backup import BackupManager, BackupError
    
    backup_type = request.form.get('backup_type', 'full')
    description = request.form.get('description', '')
    
    try:
        backup_manager = BackupManager()
        
        if backup_type == 'full':
            skip_videos = request.form.get('skip_videos') == 'true'
            result = backup_manager.create_full_backup(description, skip_videos=skip_videos)
            if result['success']:
                msg = 'Full backup created successfully!'
                if result.get('skipped'):
                    msg += f" (Skipped: {', '.join(result['skipped'])})"
                log_activity('create_backup', 'backup', None, {'type': 'full', 'timestamp': result['timestamp'], 'skipped': result.get('skipped', [])})
                flash(msg, 'success')
            else:
                log_activity('create_backup_failed', 'backup', None, {'type': 'full', 'errors': result['errors']})
                flash(f'Backup completed with errors: {", ".join(result["errors"])}', 'warning')
        
        elif backup_type == 'database':
            result = backup_manager.backup_database(description)
            log_activity('create_backup', 'backup', None, {'type': 'database', 'timestamp': result['timestamp']})
            flash(f'Database backup created successfully!', 'success')
        
        elif backup_type == 'videos':
            result = backup_manager.backup_videos(description)
            log_activity('create_backup', 'backup', None, {'type': 'videos', 'timestamp': result['timestamp']})
            flash(f'Video files backup created successfully!', 'success')
        
        elif backup_type == 'config':
            result = backup_manager.backup_config(description)
            log_activity('create_backup', 'backup', None, {'type': 'config', 'timestamp': result['timestamp']})
            flash(f'Configuration backup created successfully!', 'success')
        
        else:
            flash(f'Invalid backup type: {backup_type}', 'danger')
    
    except BackupError as e:
        current_app.logger.error(f'Backup failed: {e}')
        log_activity('create_backup_failed', 'backup', None, {'type': backup_type, 'error': str(e)})
        flash(f'Backup failed: {str(e)}', 'danger')
    
    except Exception as e:
        current_app.logger.error(f'Unexpected backup error: {e}')
        flash(f'Unexpected error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_restore'))


@admin_bp.route('/backup/restore', methods=['POST'])
@login_required
@admin_required
def restore_backup():
    """Restore from a backup"""
    from utils.backup import BackupManager, BackupError
    
    backup_timestamp = request.form.get('backup_timestamp')
    backup_type = request.form.get('backup_type')
    verify_checksum = request.form.get('verify_checksum', 'true') == 'true'
    
    if not backup_timestamp or not backup_type:
        flash('Missing backup information', 'danger')
        return redirect(url_for('admin.backup_restore'))
    
    try:
        backup_manager = BackupManager()
        
        if backup_type == 'database':
            backup_manager.restore_database(backup_timestamp, verify_checksum)
            log_activity('restore_backup', 'backup', None, {'type': 'database', 'timestamp': backup_timestamp})
            flash('Database restored successfully! Application will restart.', 'success')
        
        elif backup_type == 'videos':
            backup_manager.restore_videos(backup_timestamp, verify_checksum)
            log_activity('restore_backup', 'backup', None, {'type': 'videos', 'timestamp': backup_timestamp})
            flash('Video files restored successfully!', 'success')
        
        else:
            flash(f'Restore not supported for type: {backup_type}', 'danger')
    
    except BackupError as e:
        current_app.logger.error(f'Restore failed: {e}')
        log_activity('restore_backup_failed', 'backup', None, 
                    {'type': backup_type, 'timestamp': backup_timestamp, 'error': str(e)})
        flash(f'Restore failed: {str(e)}', 'danger')
    
    except Exception as e:
        current_app.logger.error(f'Unexpected restore error: {e}')
        flash(f'Unexpected error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_restore'))


@admin_bp.route('/backup/delete', methods=['POST'])
@login_required
@admin_required
def delete_backup():
    """Delete a backup"""
    from utils.backup import BackupManager, BackupError
    
    backup_timestamp = request.form.get('backup_timestamp')
    backup_type = request.form.get('backup_type')
    
    if not backup_timestamp or not backup_type:
        flash('Missing backup information', 'danger')
        return redirect(url_for('admin.backup_restore'))
    
    try:
        backup_manager = BackupManager()
        backup_manager.delete_backup(backup_timestamp, backup_type)
        
        log_activity('delete_backup', 'backup', None, {'type': backup_type, 'timestamp': backup_timestamp})
        flash('Backup deleted successfully!', 'success')
    
    except BackupError as e:
        current_app.logger.error(f'Delete backup failed: {e}')
        flash(f'Delete failed: {str(e)}', 'danger')
    
    except Exception as e:
        current_app.logger.error(f'Unexpected delete error: {e}')
        flash(f'Unexpected error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_restore'))


@admin_bp.route('/backup/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup_backups():
    """Clean up old backups"""
    from utils.backup import BackupManager
    
    retention_days = int(request.form.get('retention_days', current_app.config['BACKUP_RETENTION_DAYS']))
    
    try:
        backup_manager = BackupManager()
        deleted_count = backup_manager.cleanup_old_backups(retention_days)
        
        log_activity('cleanup_backups', 'backup', None, 
                    {'retention_days': retention_days, 'deleted_count': deleted_count})
        flash(f'Cleaned up {deleted_count} old backup(s)', 'success')
    
    except Exception as e:
        current_app.logger.error(f'Backup cleanup failed: {e}')
        flash(f'Cleanup failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_restore'))


@admin_bp.route('/backup/download/<backup_type>/<timestamp>')
@login_required
@admin_required
def download_backup(backup_type, timestamp):
    """Download a backup file"""
    from utils.backup import BackupManager
    
    try:
        backup_manager = BackupManager()
        metadata = backup_manager._load_metadata(timestamp, backup_type)
        
        if not metadata:
            flash('Backup not found', 'danger')
            return redirect(url_for('admin.backup_restore'))
        
        backup_path = metadata['path']
        filename = metadata['filename']
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'danger')
            return redirect(url_for('admin.backup_restore'))
        
        log_activity('download_backup', 'backup', None, {'type': backup_type, 'timestamp': timestamp})
        
        return send_from_directory(
            os.path.dirname(backup_path),
            os.path.basename(backup_path),
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        current_app.logger.error(f'Backup download failed: {e}')
        flash(f'Download failed: {str(e)}', 'danger')
        return redirect(url_for('admin.backup_restore'))


# ============================================================================
# NOTIFICATION ROUTES (Phase 6)
# ============================================================================

@admin_bp.route('/notifications')
@login_required
def notifications():
    """Notification center page"""
    from utils.notifications import NotificationService
    
    # Get filter parameters
    show_read = request.args.get('show_read', 'false') == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Query notifications
    query = db.session.query(Notification).filter_by(
        user_id=current_user.id,
        is_dismissed=False
    )
    
    if not show_read:
        query = query.filter_by(is_read=False)
    
    # Paginate
    pagination = query.order_by(
        Notification.priority.desc(),
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    notifications_list = pagination.items
    
    # Get unread count
    unread_count = NotificationService.get_unread_count(current_user.id)
    
    return render_template('notifications.html',
                         notifications=notifications_list,
                         pagination=pagination,
                         show_read=show_read,
                         unread_count=unread_count)


@admin_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    from utils.notifications import NotificationService
    
    if NotificationService.mark_as_read(notification_id, current_user.id):
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404


@admin_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    from utils.notifications import NotificationService
    
    count = NotificationService.mark_all_as_read(current_user.id)
    
    return jsonify({'success': True, 'count': count})


@admin_bp.route('/notifications/<int:notification_id>/dismiss', methods=['POST'])
@login_required
def dismiss_notification(notification_id):
    """Dismiss notification"""
    from utils.notifications import NotificationService
    
    if NotificationService.dismiss_notification(notification_id, current_user.id):
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404


@admin_bp.route('/api/notifications/unread')
@login_required
def get_unread_notifications():
    """Get unread notifications for current user (for badge)"""
    from utils.notifications import NotificationService
    
    notifications_list = NotificationService.get_unread_notifications(
        current_user.id,
        limit=5
    )
    
    return jsonify({
        'count': len(notifications_list),
        'notifications': [{
            'id': n.id,
            'type': n.notification_type.value,
            'title': n.title,
            'message': n.message,
            'priority': n.priority.value,
            'icon': n.icon,
            'action_url': n.action_url,
            'created_at': n.created_at.isoformat(),
            'age_hours': n.age_hours
        } for n in notifications_list]
    })


@admin_bp.route('/notification-preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Notification preferences page"""
    from models import NotificationPreference
    
    # Get or create preferences for user
    prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            # Update global toggles
            prefs.email_enabled = request.form.get('email_enabled') == 'on'
            prefs.browser_enabled = request.form.get('browser_enabled') == 'on'
            
            # Update event-specific preferences
            event_types = [
                'device_offline',
                'upload_complete',
                'backup_success',
                'backup_failure',
                'system_error',
                'schedule_conflict',
                'storage_warning'
            ]
            
            for event_type in event_types:
                setattr(prefs, f'{event_type}_email', request.form.get(f'{event_type}_email') == 'on')
                setattr(prefs, f'{event_type}_browser', request.form.get(f'{event_type}_browser') == 'on')
            
            # Update report preferences
            prefs.daily_summary_email = request.form.get('daily_summary_email') == 'on'
            prefs.weekly_report_email = request.form.get('weekly_report_email') == 'on'
            
            db.session.commit()
            
            log_activity('update_notification_preferences', 'user', current_user.id)
            flash('Notification preferences updated successfully!', 'success')
            
        except Exception as e:
            current_app.logger.error(f'Error updating notification preferences: {e}')
            flash('Failed to update preferences', 'danger')
        
        return redirect(url_for('admin.notification_preferences'))
    
    return render_template('notification_preferences.html', prefs=prefs)


