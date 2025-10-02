"""
Providers API routes
"""
from flask import Blueprint

providers_bp = Blueprint('providers', __name__)

@providers_bp.route('/')
def list_providers():
    return "Providers API"
