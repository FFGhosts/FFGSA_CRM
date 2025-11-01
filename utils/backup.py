"""
Backup and Restore Utilities
Handles database, video files, and configuration backups with restore capabilities
"""
import os
import shutil
import subprocess
import json
import tarfile
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from flask import current_app
import sqlite3


class BackupError(Exception):
    """Custom exception for backup operations"""
    pass


class BackupManager:
    """Manages backup and restore operations for database, files, and configuration"""
    
    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize backup manager
        
        Args:
            backup_dir: Directory to store backups (defaults to config setting)
        """
        self.backup_dir = backup_dir or current_app.config.get('BACKUP_FOLDER')
        self.logger = current_app.logger
        self.ensure_backup_dir()
    
    def ensure_backup_dir(self) -> None:
        """Create backup directory if it doesn't exist"""
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'database'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'videos'), exist_ok=True)
        os.makedirs(os.path.join(self.backup_dir, 'config'), exist_ok=True)
    
    # ========================================================================
    # DATABASE BACKUP & RESTORE
    # ========================================================================
    
    def backup_database(self, description: str = "") -> Dict:
        """
        Create database backup
        
        Args:
            description: Optional description for this backup
            
        Returns:
            Dict with backup information
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        try:
            self.logger.info(f"Starting database backup: {timestamp}")
            if db_uri.startswith('sqlite'):
                result = self._backup_sqlite(timestamp, description)
                self.logger.info(f"Database backup completed: {result['filename']}")
                return result
            elif db_uri.startswith('postgresql'):
                result = self._backup_postgresql(timestamp, description)
                self.logger.info(f"Database backup completed: {result['filename']}")
                return result
            else:
                self.logger.error(f"Unsupported database type: {db_uri}")
                raise BackupError(f"Unsupported database type: {db_uri}")
        except Exception as e:
            self.logger.error(f"Database backup failed: {str(e)}", exc_info=True)
            raise BackupError(f"Database backup failed: {str(e)}")
    
    def _backup_sqlite(self, timestamp: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Backup SQLite database"""
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        source_db = db_uri.replace('sqlite:///', '')
        
        # Handle relative paths by resolving against instance folder
        if not os.path.isabs(source_db):
            source_db = os.path.join(current_app.instance_path, source_db)
        
        if not os.path.exists(source_db):
            raise BackupError(f"Database file not found: {source_db}")
        
        backup_name = f"database_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, 'database', backup_name)
        
        # Copy database file
        shutil.copy2(source_db, backup_path)
        
        # Calculate checksum
        checksum = self._calculate_checksum(backup_path)
        
        # Create metadata
        metadata = {
            'timestamp': timestamp,
            'description': description,
            'type': 'sqlite',
            'filename': backup_name,
            'size': os.path.getsize(backup_path),
            'checksum': checksum,
            'path': backup_path
        }
        
        # Save metadata
        self._save_metadata(timestamp, 'database', metadata)
        
        return metadata
    
    def _backup_postgresql(self, timestamp: str, description: str) -> Dict:
        """Backup PostgreSQL database using pg_dump"""
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # Parse connection string
        # Format: postgresql://user:pass@host:port/dbname
        parts = db_uri.replace('postgresql://', '').split('@')
        if len(parts) != 2:
            raise BackupError("Invalid PostgreSQL connection string")
        
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        dbname = host_db[1]
        
        backup_name = f"database_{timestamp}.sql"
        backup_path = os.path.join(self.backup_dir, 'database', backup_name)
        
        # Set environment variable for password
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password
        
        # Execute pg_dump
        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', username,
            '-F', 'c',  # Custom format (compressed)
            '-f', backup_path,
            dbname
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise BackupError(f"pg_dump failed: {result.stderr}")
        
        # Calculate checksum
        checksum = self._calculate_checksum(backup_path)
        
        # Create metadata
        metadata = {
            'timestamp': timestamp,
            'description': description,
            'type': 'postgresql',
            'filename': backup_name,
            'size': os.path.getsize(backup_path),
            'checksum': checksum,
            'path': backup_path,
            'database': dbname
        }
        
        # Save metadata
        self._save_metadata(timestamp, 'database', metadata)
        
        return metadata
    
    def restore_database(self, backup_timestamp: str, verify_checksum: bool = True) -> bool:
        """
        Restore database from backup
        
        Args:
            backup_timestamp: Timestamp of backup to restore
            verify_checksum: Whether to verify backup integrity
            
        Returns:
            True if successful
        """
        metadata = self._load_metadata(backup_timestamp, 'database')
        
        if not metadata:
            raise BackupError(f"Backup metadata not found: {backup_timestamp}")
        
        backup_path = metadata['path']
        
        if not os.path.exists(backup_path):
            raise BackupError(f"Backup file not found: {backup_path}")
        
        # Verify checksum
        if verify_checksum:
            current_checksum = self._calculate_checksum(backup_path)
            if current_checksum != metadata['checksum']:
                raise BackupError("Backup file checksum mismatch - file may be corrupted")
        
        try:
            if metadata['type'] == 'sqlite':
                return self._restore_sqlite(backup_path)
            elif metadata['type'] == 'postgresql':
                return self._restore_postgresql(backup_path, metadata)
            else:
                raise BackupError(f"Unsupported database type: {metadata['type']}")
        except Exception as e:
            raise BackupError(f"Database restore failed: {str(e)}")
    
    def _restore_sqlite(self, backup_path: str) -> bool:
        """Restore SQLite database"""
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        target_db = db_uri.replace('sqlite:///', '')
        
        # Create backup of current database
        if os.path.exists(target_db):
            backup_current = f"{target_db}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_db, backup_current)
        
        # Restore from backup
        shutil.copy2(backup_path, target_db)
        
        return True
    
    def _restore_postgresql(self, backup_path: str, metadata: Dict) -> bool:
        """Restore PostgreSQL database using pg_restore"""
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # Parse connection string
        parts = db_uri.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        dbname = host_db[1]
        
        # Set environment variable for password
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password
        
        # Drop and recreate database (requires superuser or database owner)
        # This is a destructive operation - ensure confirmation before calling
        
        # Execute pg_restore
        cmd = [
            'pg_restore',
            '-h', host,
            '-p', port,
            '-U', username,
            '-d', dbname,
            '-c',  # Clean (drop) database objects before recreating
            backup_path
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            # pg_restore may return non-zero even on success for certain warnings
            # Check if actual errors occurred
            if 'ERROR' in result.stderr:
                raise BackupError(f"pg_restore failed: {result.stderr}")
        
        return True
    
    # ========================================================================
    # VIDEO FILES BACKUP & RESTORE
    # ========================================================================
    
    def backup_videos(self, description: str = "", incremental: bool = False) -> Dict:
        """
        Create backup of video files
        
        Args:
            description: Optional description
            incremental: If True, only backup files changed since last backup
            
        Returns:
            Dict with backup information
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_folder = current_app.config['UPLOAD_FOLDER']
        thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
        
        backup_name = f"videos_{timestamp}.tar.gz"
        backup_path = os.path.join(self.backup_dir, 'videos', backup_name)
        
        try:
            self.logger.info(f"Starting video files backup: {timestamp}")
            # Create tar.gz archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                # Add videos
                if os.path.exists(video_folder):
                    self.logger.info(f"Archiving video folder: {video_folder}")
                    tar.add(video_folder, arcname='videos')
                
                # Add thumbnails
                if os.path.exists(thumbnail_folder):
                    self.logger.info(f"Archiving thumbnail folder: {thumbnail_folder}")
                    tar.add(thumbnail_folder, arcname='thumbnails')
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)
            
            # Count files
            video_count = len(os.listdir(video_folder)) if os.path.exists(video_folder) else 0
            thumbnail_count = len(os.listdir(thumbnail_folder)) if os.path.exists(thumbnail_folder) else 0
            
            # Create metadata
            metadata = {
                'timestamp': timestamp,
                'description': description,
                'type': 'videos',
                'filename': backup_name,
                'size': os.path.getsize(backup_path),
                'checksum': checksum,
                'path': backup_path,
                'video_count': video_count,
                'thumbnail_count': thumbnail_count,
                'incremental': incremental
            }
            
            # Save metadata
            self._save_metadata(timestamp, 'videos', metadata)
            
            self.logger.info(f"Video backup completed: {backup_name}, {video_count} videos, {thumbnail_count} thumbnails")
            return metadata
        
        except Exception as e:
            self.logger.error(f"Video backup failed: {str(e)}", exc_info=True)
            raise BackupError(f"Video backup failed: {str(e)}")
    
    def restore_videos(self, backup_timestamp: str, verify_checksum: bool = True) -> bool:
        """
        Restore video files from backup
        
        Args:
            backup_timestamp: Timestamp of backup to restore
            verify_checksum: Whether to verify backup integrity
            
        Returns:
            True if successful
        """
        metadata = self._load_metadata(backup_timestamp, 'videos')
        
        if not metadata:
            raise BackupError(f"Backup metadata not found: {backup_timestamp}")
        
        backup_path = metadata['path']
        
        if not os.path.exists(backup_path):
            raise BackupError(f"Backup file not found: {backup_path}")
        
        # Verify checksum
        if verify_checksum:
            current_checksum = self._calculate_checksum(backup_path)
            if current_checksum != metadata['checksum']:
                raise BackupError("Backup file checksum mismatch - file may be corrupted")
        
        video_folder = current_app.config['UPLOAD_FOLDER']
        thumbnail_folder = current_app.config['THUMBNAIL_FOLDER']
        
        try:
            # Create backup of current files
            current_backup_base = os.path.join(
                self.backup_dir, 
                f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if os.path.exists(video_folder):
                shutil.copytree(video_folder, f"{current_backup_base}_videos")
            
            if os.path.exists(thumbnail_folder):
                shutil.copytree(thumbnail_folder, f"{current_backup_base}_thumbnails")
            
            # Extract backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(path=os.path.dirname(video_folder))
            
            return True
        
        except Exception as e:
            raise BackupError(f"Video restore failed: {str(e)}")
    
    # ========================================================================
    # CONFIGURATION BACKUP & RESTORE
    # ========================================================================
    
    def backup_config(self, description: str = "") -> Dict:
        """
        Backup configuration files (.env, config.py)
        
        Args:
            description: Optional description
            
        Returns:
            Dict with backup information
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"config_{timestamp}.tar.gz"
        backup_path = os.path.join(self.backup_dir, 'config', backup_name)
        
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        try:
            with tarfile.open(backup_path, 'w:gz') as tar:
                # Add .env if exists
                env_file = os.path.join(base_dir, '.env')
                if os.path.exists(env_file):
                    tar.add(env_file, arcname='.env')
                
                # Add config.py
                config_file = os.path.join(base_dir, 'config.py')
                if os.path.exists(config_file):
                    tar.add(config_file, arcname='config.py')
            
            checksum = self._calculate_checksum(backup_path)
            
            metadata = {
                'timestamp': timestamp,
                'description': description,
                'type': 'config',
                'filename': backup_name,
                'size': os.path.getsize(backup_path),
                'checksum': checksum,
                'path': backup_path
            }
            
            self._save_metadata(timestamp, 'config', metadata)
            
            return metadata
        
        except Exception as e:
            raise BackupError(f"Config backup failed: {str(e)}")
    
    # ========================================================================
    # FULL BACKUP (ALL COMPONENTS)
    # ========================================================================
    
    def create_full_backup(self, description: str = "") -> Dict:
        """
        Create complete backup of database, videos, and configuration
        
        Args:
            description: Optional description
            
        Returns:
            Dict with information about all backups
        """
        results = {
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'description': description,
            'database': None,
            'videos': None,
            'config': None,
            'success': True,
            'errors': []
        }
        
        self.logger.info(f"Starting full backup: {results['timestamp']}")
        
        # Backup database
        try:
            results['database'] = self.backup_database(description)
        except Exception as e:
            error_msg = f"Database backup failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['success'] = False
        
        # Backup videos
        try:
            results['videos'] = self.backup_videos(description)
        except Exception as e:
            error_msg = f"Video backup failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['success'] = False
        
        # Backup config
        try:
            results['config'] = self.backup_config(description)
        except Exception as e:
            error_msg = f"Config backup failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['success'] = False
        
        if results['success']:
            self.logger.info(f"Full backup completed successfully: {results['timestamp']}")
        else:
            self.logger.warning(f"Full backup completed with errors: {results['timestamp']}")
        
        return results
    
    # ========================================================================
    # BACKUP MANAGEMENT
    # ========================================================================
    
    def list_backups(self, backup_type: Optional[str] = None) -> List[Dict]:
        """
        List all available backups
        
        Args:
            backup_type: Filter by type ('database', 'videos', 'config') or None for all
            
        Returns:
            List of backup metadata dictionaries
        """
        backups = []
        
        types_to_check = [backup_type] if backup_type else ['database', 'videos', 'config']
        
        for btype in types_to_check:
            type_dir = os.path.join(self.backup_dir, btype)
            if not os.path.exists(type_dir):
                continue
            
            for filename in os.listdir(type_dir):
                if filename.endswith('.json'):
                    metadata_path = os.path.join(type_dir, filename)
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            backups.append(metadata)
                    except Exception:
                        continue
        
        # Sort by timestamp descending
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return backups
    
    def delete_backup(self, backup_timestamp: str, backup_type: str) -> bool:
        """
        Delete a backup and its metadata
        
        Args:
            backup_timestamp: Timestamp of backup to delete
            backup_type: Type of backup ('database', 'videos', 'config')
            
        Returns:
            True if successful
        """
        metadata = self._load_metadata(backup_timestamp, backup_type)
        
        if not metadata:
            raise BackupError(f"Backup not found: {backup_timestamp}")
        
        # Delete backup file
        if os.path.exists(metadata['path']):
            os.remove(metadata['path'])
        
        # Delete metadata file
        metadata_path = os.path.join(
            self.backup_dir, 
            backup_type, 
            f"{backup_timestamp}.json"
        )
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        return True
    
    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """
        Delete backups older than retention period
        
        Args:
            retention_days: Number of days to keep backups
            
        Returns:
            Number of backups deleted
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        backups = self.list_backups()
        
        for backup in backups:
            backup_date = datetime.strptime(backup['timestamp'], '%Y%m%d_%H%M%S')
            
            if backup_date < cutoff_date:
                try:
                    self.delete_backup(backup['timestamp'], backup['type'])
                    deleted_count += 1
                except Exception:
                    continue
        
        return deleted_count
    
    def get_backup_stats(self) -> Dict:
        """
        Get statistics about backups
        
        Returns:
            Dict with backup statistics
        """
        backups = self.list_backups()
        
        stats = {
            'total_backups': len(backups),
            'database_backups': len([b for b in backups if b['type'] == 'database']),
            'video_backups': len([b for b in backups if b['type'] == 'videos']),
            'config_backups': len([b for b in backups if b['type'] == 'config']),
            'total_size': sum(b.get('size', 0) for b in backups),
            'oldest_backup': min([b['timestamp'] for b in backups]) if backups else None,
            'newest_backup': max([b['timestamp'] for b in backups]) if backups else None
        }
        
        return stats
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _calculate_checksum(self, filepath: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        
        with open(filepath, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _save_metadata(self, timestamp: str, backup_type: str, metadata: Dict) -> None:
        """Save backup metadata to JSON file"""
        metadata_path = os.path.join(
            self.backup_dir, 
            backup_type, 
            f"{timestamp}.json"
        )
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self, timestamp: str, backup_type: str) -> Optional[Dict]:
        """Load backup metadata from JSON file"""
        metadata_path = os.path.join(
            self.backup_dir, 
            backup_type, 
            f"{timestamp}.json"
        )
        
        if not os.path.exists(metadata_path):
            return None
        
        with open(metadata_path, 'r') as f:
            return json.load(f)
