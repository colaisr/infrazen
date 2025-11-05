"""
InfraZen FinOps Platform
Flask Application Factory
"""
import os
import json
from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
from flask_migrate import Migrate
from flask_login import LoginManager
from app.core.database import db

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(f'app.config.{config_name.title()}Config')
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth_bp.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.core.models import User
        return User.query.get(int(user_id))
    
    # Add custom Jinja2 filters
    @app.template_filter('from_json')
    def from_json_filter(json_string):
        """Convert JSON string to Python object"""
        if json_string:
            try:
                return json.loads(json_string)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    # Register blueprints
    from app.web.main import main_bp
    from app.api.auth import auth_bp
    from app.api.admin import admin_bp
    from app.api.providers import providers_bp
    from app.api.resources import resources_bp
    from app.api import recommendations_bp
    from app.api.complete_sync import complete_sync_bp
    from app.api.analytics import analytics_bp
    from app.api.business_context import business_context_bp
    from app.api.dashboard import dashboard_bp
    from app.api.chat import chat_api
    from app.providers.beget.routes import beget_bp
    from app.providers.selectel.routes import selectel_bp
    from app.providers.yandex.routes import yandex_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(providers_bp, url_prefix='/api/providers')
    app.register_blueprint(resources_bp, url_prefix='/api/resources')
    app.register_blueprint(complete_sync_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(business_context_bp, url_prefix='/api/business-context')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(chat_api, url_prefix='/api/chat')
    app.register_blueprint(beget_bp, url_prefix='/api/providers/beget')
    app.register_blueprint(selectel_bp, url_prefix='/api/providers/selectel')
    app.register_blueprint(yandex_bp, url_prefix='/api/providers/yandex')
    app.register_blueprint(recommendations_bp, url_prefix='/api')
    
    # All routes are now in the new structure

    # -------------------------
    # Development file logging
    # -------------------------
    try:
        log_level_name = app.config.get('LOG_LEVEL', 'INFO')
        log_level = getattr(logging, str(log_level_name).upper(), logging.INFO)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        app.logger.setLevel(log_level)

        # Write to server.log in project root with rotation
        project_root = os.path.dirname(os.path.dirname(__file__))
        log_path = os.path.join(project_root, 'server.log')

        # Avoid duplicate handlers on reload
        has_file = False
        for h in root_logger.handlers:
            try:
                if isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == log_path:
                    has_file = True
                    break
            except Exception:
                continue
        if not has_file:
            fh = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=2, encoding='utf-8')
            fh.setLevel(log_level)
            fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
            fh.setFormatter(fmt)
            root_logger.addHandler(fh)
    except Exception:
        # Logging setup failures should not break the app
        pass
    
    return app
