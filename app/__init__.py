"""
InfraZen FinOps Platform
Flask Application Factory
"""
import os
from flask import Flask
from flask_migrate import Migrate
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
    
    # Register blueprints
    from app.web.main import main_bp
    from app.api.auth import auth_bp
    from app.api.providers import providers_bp
    from app.api.resources import resources_bp
    from app.providers.beget.routes import beget_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(providers_bp, url_prefix='/api/providers')
    app.register_blueprint(resources_bp, url_prefix='/api/resources')
    app.register_blueprint(beget_bp, url_prefix='/api/providers/beget')
    
    # All routes are now in the new structure
    
    return app
