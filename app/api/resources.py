"""
Resources API routes
"""
from flask import Blueprint

resources_bp = Blueprint('resources', __name__)

@resources_bp.route('/')
def list_resources():
    return "Resources API"
