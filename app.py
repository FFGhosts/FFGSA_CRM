"""
PiCMS - Raspberry Pi Content Management System
Main Flask application entry point
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from flask_mail import Mail

from config import config
from models import db, User

# Global instances
socketio = SocketIO()
mail = Mail()


def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    
    # CSRF Protection (exempted for API routes)
    csrf = CSRFProtect(app)
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "X-Device-Key"]
        }
    })
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config['RATELIMIT_STORAGE_URL'],
        enabled=app.config['RATELIMIT_ENABLED']
    )
    
    # SocketIO initialization (Phase 4.1)
    # Allow localhost origins for development
    cors_origins = app.config['CORS_ORIGINS']
    if cors_origins == ['*']:
        cors_origins = '*'
    socketio.init_app(app, 
                      cors_allowed_origins=cors_origins,
                      async_mode='threading',
                      logger=app.config['DEBUG'],
                      engineio_logger=app.config['DEBUG'])
    
    # Flask-Mail initialization (Phase 6)
    mail.init_app(app)
    
    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'  # type: ignore
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from routes.admin_routes import admin_bp
    from routes.api_routes import api_bp
    from routes.playlist_routes import playlist_bp
    from routes.analytics_routes import analytics_bp
    from routes.device_group_routes import groups_bp
    from routes.client_routes import client_bp
    
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(playlist_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(client_bp)
    
    # Exempt API routes from CSRF protection (they use API key auth)
    csrf.exempt(api_bp)
    
    # Import SocketIO event handlers (Phase 4.1)
    import socketio_events  # noqa: F401
    
    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('admin.dashboard'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def too_large(error):
        return render_template('errors/413.html'), 413
    
    # Store limiter in app for use in blueprints
    app.limiter = limiter  # type: ignore
    
    # Initialize scheduler for automatic backups (Phase 4.5)
    from utils.scheduler import init_scheduler, shutdown_scheduler
    init_scheduler(app)
    
    # Register shutdown handler
    import atexit
    atexit.register(shutdown_scheduler)
    
    return app


def setup_logging(app):
    """Configure application logging"""
    
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists(app.config['LOG_FOLDER']):
            os.mkdir(app.config['LOG_FOLDER'])
        
        # Application log handler
        file_handler = RotatingFileHandler(
            app.config['APP_LOG_FILE'],
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('PiCMS startup')


if __name__ == '__main__':
    app = create_app()
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Create default admin user if none exists
        if User.query.count() == 0:
            from models import UserRole
            admin = User(
                username=app.config['ADMIN_USERNAME'],
                email='admin@picms.local',
                role=UserRole.ADMIN
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            app.logger.info(f"Created default admin user: {admin.username}")
    
    # Run the application with SocketIO
    socketio.run(
        app,
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=app.config['DEBUG'],
        allow_unsafe_werkzeug=True
    )
