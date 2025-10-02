"""
InfraZen FinOps Platform
Application entry point
"""
import os
from app import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5001))
    
    print(f"🚀 Starting InfraZen FinOps Platform")
    print(f"📍 Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"🌐 Server: http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug)
