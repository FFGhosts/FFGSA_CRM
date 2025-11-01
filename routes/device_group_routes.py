"""
Device Groups Routes Blueprint
Routes for managing device groups and bulk assignments
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models import db, DeviceGroup, Device, Assignment, Video, Playlist
from forms import DeviceGroupForm, DeviceGroupMemberForm, AssignmentForm

groups_bp = Blueprint('groups', __name__, url_prefix='/groups')


@groups_bp.route('/')
@login_required
def index():
    """List all device groups"""
    groups = DeviceGroup.query.order_by(DeviceGroup.name).all()
    return render_template('device_groups.html', groups=groups)


@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new device group"""
    form = DeviceGroupForm()
    
    if form.validate_on_submit():
        # Check if group name already exists
        existing = DeviceGroup.query.filter_by(name=form.name.data).first()
        if existing:
            flash(f'Group "{form.name.data}" already exists', 'danger')
            return render_template('device_group_create.html', form=form)
        
        group = DeviceGroup(
            name=form.name.data,
            description=form.description.data,
            color=form.color.data or '#6c757d'
        )
        
        db.session.add(group)
        db.session.commit()
        
        flash(f'Device group "{group.name}" created successfully', 'success')
        return redirect(url_for('groups.view', group_id=group.id))
    
    return render_template('device_group_create.html', form=form)


@groups_bp.route('/<int:group_id>')
@login_required
def view(group_id):
    """View device group details"""
    group = DeviceGroup.query.get_or_404(group_id)
    member_form = DeviceGroupMemberForm()
    
    # Get devices not in this group
    all_device_ids = [d.id for d in group.devices]
    available_devices = Device.query.filter(
        ~Device.id.in_(all_device_ids) if all_device_ids else True
    ).filter_by(is_active=True).order_by(Device.name).all()
    
    return render_template('device_group_view.html', 
                          group=group, 
                          member_form=member_form,
                          available_devices=available_devices)


@groups_bp.route('/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(group_id):
    """Edit device group"""
    group = DeviceGroup.query.get_or_404(group_id)
    form = DeviceGroupForm(obj=group)
    
    if form.validate_on_submit():
        # Check if new name conflicts with existing group
        if form.name.data != group.name:
            existing = DeviceGroup.query.filter_by(name=form.name.data).first()
            if existing:
                flash(f'Group "{form.name.data}" already exists', 'danger')
                return render_template('device_group_edit.html', form=form, group=group)
        
        group.name = form.name.data
        group.description = form.description.data
        group.color = form.color.data or '#6c757d'
        
        db.session.commit()
        
        flash(f'Device group "{group.name}" updated successfully', 'success')
        return redirect(url_for('groups.view', group_id=group.id))
    
    return render_template('device_group_edit.html', form=form, group=group)


@groups_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete(group_id):
    """Delete a device group"""
    group = DeviceGroup.query.get_or_404(group_id)
    group_name = group.name
    
    db.session.delete(group)
    db.session.commit()
    
    flash(f'Device group "{group_name}" deleted successfully', 'success')
    return redirect(url_for('groups.index'))


@groups_bp.route('/<int:group_id>/add-devices', methods=['POST'])
@login_required
def add_devices(group_id):
    """Add devices to a group"""
    group = DeviceGroup.query.get_or_404(group_id)
    form = DeviceGroupMemberForm()
    
    if form.validate_on_submit():
        added_count = 0
        for device_id in form.device_ids.data:
            device = Device.query.get(device_id)
            if device and device not in group.devices:
                group.devices.append(device)
                added_count += 1
        
        db.session.commit()
        
        flash(f'Added {added_count} device(s) to group "{group.name}"', 'success')
    else:
        flash('Please select at least one device', 'danger')
    
    return redirect(url_for('groups.view', group_id=group.id))


@groups_bp.route('/<int:group_id>/remove-device/<int:device_id>', methods=['POST'])
@login_required
def remove_device(group_id, device_id):
    """Remove a device from a group"""
    group = DeviceGroup.query.get_or_404(group_id)
    device = Device.query.get_or_404(device_id)
    
    if device in group.devices:
        group.devices.remove(device)
        db.session.commit()
        flash(f'Removed "{device.name}" from group "{group.name}"', 'success')
    else:
        flash(f'Device "{device.name}" is not in group "{group.name}"', 'warning')
    
    return redirect(url_for('groups.view', group_id=group.id))


@groups_bp.route('/<int:group_id>/bulk-assign', methods=['GET', 'POST'])
@login_required
def bulk_assign(group_id):
    """Bulk assign content to all devices in a group"""
    group = DeviceGroup.query.get_or_404(group_id)
    
    if request.method == 'POST':
        content_type = request.form.get('content_type')
        
        if content_type == 'video':
            video_ids = request.form.getlist('video_ids')
            if not video_ids:
                flash('Please select at least one video', 'danger')
                return redirect(url_for('groups.bulk_assign', group_id=group.id))
            
            assigned_count = 0
            for device in group.devices:
                for video_id in video_ids:
                    # Check if assignment already exists
                    existing = Assignment.query.filter_by(
                        device_id=device.id,
                        video_id=int(video_id)
                    ).first()
                    
                    if not existing:
                        assignment = Assignment(
                            device_id=device.id,
                            video_id=int(video_id)
                        )
                        db.session.add(assignment)
                        assigned_count += 1
            
            db.session.commit()
            flash(f'Created {assigned_count} assignment(s) for {len(group.devices)} device(s) in group "{group.name}"', 'success')
            
        elif content_type == 'playlist':
            playlist_ids = request.form.getlist('playlist_ids')
            if not playlist_ids:
                flash('Please select at least one playlist', 'danger')
                return redirect(url_for('groups.bulk_assign', group_id=group.id))
            
            assigned_count = 0
            for device in group.devices:
                for playlist_id in playlist_ids:
                    # Check if assignment already exists
                    existing = Assignment.query.filter_by(
                        device_id=device.id,
                        playlist_id=int(playlist_id)
                    ).first()
                    
                    if not existing:
                        assignment = Assignment(
                            device_id=device.id,
                            playlist_id=int(playlist_id)
                        )
                        db.session.add(assignment)
                        assigned_count += 1
            
            db.session.commit()
            flash(f'Created {assigned_count} assignment(s) for {len(group.devices)} device(s) in group "{group.name}"', 'success')
        
        return redirect(url_for('groups.view', group_id=group.id))
    
    # GET request - show bulk assign form
    videos = Video.query.order_by(Video.title).all()
    playlists = Playlist.query.order_by(Playlist.name).all()
    
    return render_template('device_group_bulk_assign.html',
                          group=group,
                          videos=videos,
                          playlists=playlists)


@groups_bp.route('/<int:group_id>/clear-assignments', methods=['POST'])
@login_required
def clear_assignments(group_id):
    """Clear all assignments for devices in a group"""
    group = DeviceGroup.query.get_or_404(group_id)
    
    deleted_count = 0
    for device in group.devices:
        count = Assignment.query.filter_by(device_id=device.id).delete()
        deleted_count += count
    
    db.session.commit()
    
    flash(f'Cleared {deleted_count} assignment(s) from {len(group.devices)} device(s) in group "{group.name}"', 'success')
    return redirect(url_for('groups.view', group_id=group.id))
