"""
Playlist Routes Blueprint
Routes for playlist management, CRUD operations, and video assignments
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from sqlalchemy import func

from models import db, Playlist, PlaylistItem, Video, Assignment, Device, Tag, Category
from forms import PlaylistCreateForm, PlaylistEditForm, PlaylistAddVideoForm

playlist_bp = Blueprint('playlist', __name__, url_prefix='/playlists')


# ============================================================================
# PLAYLIST MANAGEMENT ROUTES
# ============================================================================

@playlist_bp.route('/')
@login_required
def index():
    """Display all playlists"""
    playlists = Playlist.query.order_by(Playlist.updated_at.desc()).all()
    
    # Add statistics for each playlist
    for playlist in playlists:
        playlist.assigned_devices = Assignment.query.filter_by(playlist_id=playlist.id).count()
    
    return render_template('playlists.html', playlists=playlists)


@playlist_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new playlist"""
    form = PlaylistCreateForm()
    
    if form.validate_on_submit():
        playlist = Playlist(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        
        db.session.add(playlist)
        db.session.flush()  # Get playlist ID before adding relationships
        
        # Handle tags
        tag_ids = request.form.getlist('tags')
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            playlist.tags.extend(tags)
        
        # Handle categories
        category_ids = request.form.getlist('categories')
        if category_ids:
            categories = Category.query.filter(Category.id.in_(category_ids)).all()
            playlist.categories.extend(categories)
        
        db.session.commit()
        
        flash(f'Playlist "{playlist.name}" created successfully!', 'success')
        return redirect(url_for('playlist.edit', id=playlist.id))
    
    # Get all tags and categories for selection
    all_tags = Tag.query.order_by(Tag.name).all()
    all_categories = Category.query.order_by(Category.name).all()
    
    return render_template('playlist_create.html', form=form, all_tags=all_tags, all_categories=all_categories)


@playlist_bp.route('/<int:id>')
@login_required
def view(id):
    """View playlist details"""
    playlist = Playlist.query.get_or_404(id)
    items = PlaylistItem.query.filter_by(playlist_id=id).order_by(PlaylistItem.position).all()
    
    # Get assigned devices
    assignments = Assignment.query.filter_by(playlist_id=id).all()
    
    return render_template('playlist_view.html', 
                         playlist=playlist, 
                         items=items,
                         assignments=assignments)


@playlist_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit playlist details and manage videos"""
    playlist = Playlist.query.get_or_404(id)
    form = PlaylistEditForm(obj=playlist)
    add_video_form = PlaylistAddVideoForm()
    
    if form.validate_on_submit() and 'submit' in request.form:
        playlist.name = form.name.data
        playlist.description = form.description.data
        playlist.is_active = form.is_active.data
        
        # Update tags
        tag_ids = request.form.getlist('tags')
        playlist.tags = []
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            playlist.tags = tags
        
        # Update categories
        category_ids = request.form.getlist('categories')
        playlist.categories = []
        if category_ids:
            categories = Category.query.filter(Category.id.in_(category_ids)).all()
            playlist.categories = categories
        
        db.session.commit()
        flash(f'Playlist "{playlist.name}" updated successfully!', 'success')
        return redirect(url_for('playlist.edit', id=playlist.id))
    
    # Get playlist items ordered by position
    items = PlaylistItem.query.filter_by(playlist_id=id).order_by(PlaylistItem.position).all()
    
    # Get all tags and categories for selection
    all_tags = Tag.query.order_by(Tag.name).all()
    all_categories = Category.query.order_by(Category.name).all()
    
    return render_template('playlist_edit.html', 
                         playlist=playlist, 
                         form=form,
                         all_tags=all_tags,
                         all_categories=all_categories,
                         add_video_form=add_video_form,
                         items=items)


@playlist_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a playlist"""
    playlist = Playlist.query.get_or_404(id)
    name = playlist.name
    
    # Check if playlist is assigned to any devices
    assignment_count = Assignment.query.filter_by(playlist_id=id).count()
    if assignment_count > 0:
        flash(f'Cannot delete playlist "{name}". It is assigned to {assignment_count} device(s).', 'danger')
        return redirect(url_for('playlist.index'))
    
    db.session.delete(playlist)
    db.session.commit()
    
    flash(f'Playlist "{name}" deleted successfully!', 'success')
    return redirect(url_for('playlist.index'))


# ============================================================================
# PLAYLIST ITEM MANAGEMENT ROUTES
# ============================================================================

@playlist_bp.route('/<int:id>/add-video', methods=['POST'])
@login_required
def add_video(id):
    """Add a video to playlist"""
    playlist = Playlist.query.get_or_404(id)
    form = PlaylistAddVideoForm()
    
    if form.validate_on_submit():
        video_id = form.video_id.data
        
        # Check if video exists
        video = Video.query.get(video_id)
        if not video:
            flash('Selected video does not exist.', 'danger')
            return redirect(url_for('playlist.edit', id=id))
        
        # Check if video already in playlist
        existing = PlaylistItem.query.filter_by(
            playlist_id=id,
            video_id=video_id
        ).first()
        
        if existing:
            flash(f'Video "{video.title}" is already in this playlist.', 'warning')
            return redirect(url_for('playlist.edit', id=id))
        
        try:
            # Get next position - always append to end
            max_position = db.session.query(func.max(PlaylistItem.position)).filter_by(
                playlist_id=id
            ).scalar()
            position = (max_position + 1) if max_position is not None else 0
            
            # Create playlist item
            item = PlaylistItem(
                playlist_id=id,
                video_id=video_id,
                position=position
            )
            
            db.session.add(item)
            db.session.commit()
            
            flash(f'Video "{video.title}" added to playlist!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding video: {str(e)}', 'danger')
    else:
        # Show form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('playlist.edit', id=id))


@playlist_bp.route('/<int:id>/remove-video/<int:item_id>', methods=['POST'])
@login_required
def remove_video(id, item_id):
    """Remove a video from playlist"""
    playlist = Playlist.query.get_or_404(id)
    item = PlaylistItem.query.get_or_404(item_id)
    
    # Verify item belongs to this playlist
    if item.playlist_id != id:
        flash('Invalid operation.', 'danger')
        return redirect(url_for('playlist.edit', id=id))
    
    video_title = item.video.title if item.video else "Unknown"
    
    db.session.delete(item)
    db.session.commit()
    
    # Reorder remaining items
@playlist_bp.route('/<int:id>/reorder', methods=['POST'])
@login_required
def reorder(id):
    """Reorder videos in playlist (AJAX endpoint)"""
    playlist = Playlist.query.get_or_404(id)
    
    try:
        # Get new order from request
        new_order = request.json.get('order', [])
        
        if not new_order:
            return jsonify({'success': False, 'message': 'No order provided'}), 400
        
        # First, set all positions to negative values to avoid unique constraint conflicts
        items = PlaylistItem.query.filter_by(playlist_id=id).all()
        for item in items:
            item.position = -item.id
        db.session.flush()
        
        # Then update to new positions
        for idx, item_id in enumerate(new_order):
            item = PlaylistItem.query.get(item_id)
            if item and item.playlist_id == id:
                item.position = idx
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Playlist reordered successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
        
        return jsonify({'success': True, 'message': 'Playlist reordered successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def reorder_playlist_items(playlist_id):
    """Reorder playlist items to ensure sequential positions"""
    items = PlaylistItem.query.filter_by(playlist_id=playlist_id).order_by(
        PlaylistItem.position
    ).all()
    
    for idx, item in enumerate(items):
        item.position = idx
    
    db.session.commit()
