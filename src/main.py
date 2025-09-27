import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, session, jsonify, request
from src.models.user import db
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.main import main_bp

app = Flask(__name__, 
           static_folder=os.path.join(os.path.dirname(__file__), 'static'),
           template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

app.config['SECRET_KEY'] = 'infrazen-finops-secret-key-2025'

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

# Demo login endpoint for testing without Google OAuth
@app.route('/api/demo-login', methods=['POST'])
def demo_login():
    """Demo login for testing purposes"""
    session['user'] = {
        'id': 'demo-user-123',
        'email': 'demo@infrazen.com',
        'name': 'Demo User',
        'picture': ''
    }
    return jsonify({'success': True})

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'InfraZen FinOps Platform',
        'version': '1.0.0'
    })

# Static file serving (fallback for development)
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
