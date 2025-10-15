"""
Main web interface routes
"""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash, current_app
from datetime import datetime
import json
import sys
import os

# Import from new structure
from app.core.utils.mock_data import get_overview
from app.core.database import db
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.sync import SyncSnapshot
from app.core.models.user import User
from app.core.models.provider_catalog import ProviderCatalog

main_bp = Blueprint('main', __name__)

def require_auth():
    """Check if user is authenticated and session is valid"""
    user_data = session.get('user')
    if not user_data:
        return redirect(url_for('auth.login'))
    
    # Allow demo user to pass through without validation
    if user_data.get('id') == 'demo-user-123':
        return None
    
    # For real users, validate session
    user_id = user_data.get('db_id')
    if not user_id:
        session.clear()
        return redirect(url_for('auth.login'))
    
    # Check if user still exists in database
    user = User.find_by_id(user_id)
    if not user:
        session.clear()
        flash('Your account no longer exists. Please contact support.', 'error')
        return redirect(url_for('auth.login'))
    
    # Check if user is still active
    if not user.is_active:
        session.clear()
        flash('Your account has been deactivated. Please contact support.', 'error')
        return redirect(url_for('auth.login'))
    
    return None

@main_bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    # Allow demo session fallback without forcing login
    if 'user' not in session:
        session['user'] = {
            'id': 'demo-user-123',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }

    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        # Demo user: show mock data
        overview = get_overview()
    else:
        # Real user: show real database data
        overview = get_real_user_overview(user['id'])

    return render_template(
        'dashboard.html',
        user=user,
        active_page='dashboard',
        overview=overview,
        is_demo_user=is_demo_user
    )

@main_bp.route('/connections')
def connections():
    """Cloud connections page"""
    if 'user' not in session:
        session['user'] = {
            'id': '106509284268867883869',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        # Demo user: show mock data (Yandex Cloud + Selectel + mock Beget)
        overview = get_overview()
        providers = overview['providers']
    else:
        # Real user: show only real database connections using unified models
        
        # Get real providers from database (handle SQLite precision issue)
        all_providers = CloudProvider.query.all()
        user_id_int = int(float(user['id']))
        cloud_providers = [p for p in all_providers if int(float(p.user_id)) == user_id_int]
        
        # Convert to provider format
        providers = []
        for provider in cloud_providers:
            # Get resource counts for this provider
            resource_count = Resource.query.filter_by(provider_id=provider.id).count()
            
            # Get resource count from last successful sync snapshot
            last_snapshot = SyncSnapshot.query.filter_by(
                provider_id=provider.id, 
                sync_status='success'
            ).order_by(SyncSnapshot.sync_completed_at.desc()).first()
            last_snapshot_resources = last_snapshot.total_resources_found if last_snapshot else 0
            
            # Calculate provider costs from latest sync snapshot (billing-first approach)
            total_daily_cost = 0.0
            total_monthly_cost = 0.0
            
            if last_snapshot:
                # Use cost from sync snapshot if available (billing-first approach)
                sync_config = {}
                if last_snapshot.sync_config:
                    try:
                        sync_config = json.loads(last_snapshot.sync_config)
                    except Exception:
                        # Malformed JSON in sync_config should not break the page
                        sync_config = {}
                # Support both 'total_cost' (old) and 'total_daily_cost' (new Selectel format)
                total_cost_from_sync = sync_config.get('total_daily_cost', sync_config.get('total_cost', 0))
                
                # Check if this is billing-first sync (has billing validation or sync_method)
                billing_validation = sync_config.get('billing_validation', {})
                is_billing_first = billing_validation.get('valid', False) or sync_config.get('sync_method') == 'billing_first'
                
                if is_billing_first and total_cost_from_sync > 0:
                    # Use validated cost from billing-first sync
                    total_daily_cost = total_cost_from_sync
                    total_monthly_cost = total_cost_from_sync * 30
                else:
                    # Fallback to resource-based calculation for old syncs
                    provider_resources = Resource.query.filter_by(provider_id=provider.id, is_active=True).all()
                    total_daily_cost = sum(resource.daily_cost or 0 for resource in provider_resources)
                    total_monthly_cost = sum((resource.daily_cost or 0) * 30 for resource in provider_resources)
            else:
                # No sync snapshot - use resource table
                provider_resources = Resource.query.filter_by(provider_id=provider.id, is_active=True).all()
                total_daily_cost = sum(resource.daily_cost or 0 for resource in provider_resources)
                total_monthly_cost = sum((resource.daily_cost or 0) * 30 for resource in provider_resources)
            
            providers.append({
                'id': f"{provider.provider_type}-{provider.id}",
                'code': provider.provider_type,
                'name': provider.provider_type.title(),
                'provider_type': provider.provider_type,  # Add this field for template
                'connection_name': provider.connection_name,
                'status': 'connected' if provider.is_active else 'disconnected',
                'last_sync': provider.last_sync,
                'added_at': provider.created_at.strftime('%d.%m.%Y в %H:%M') if provider.created_at else '01.01.2024 в 00:00',
                'provider_metadata': provider.provider_metadata,  # Add this line
                'total_daily_cost': round(total_daily_cost, 2),
                'total_monthly_cost': round(total_monthly_cost, 2),
                'last_snapshot_resources': last_snapshot_resources,  # Add resource count from last snapshot
                'details': {
                    'connection_name': provider.connection_name,
                    'account_id': provider.account_id,
                    'resource_count': resource_count,
                    'last_sync': provider.last_sync.isoformat() if provider.last_sync else None
                }
            })
    
    # Get enabled providers from catalog for "Available Providers" section
    enabled_providers = ProviderCatalog.query.filter_by(is_enabled=True).all()
    
    return render_template('connections.html', 
                        user=user,
                        active_page='connections',
                        page_title='Подключения облаков',
                        page_subtitle='Управление подключениями к облачным провайдерам',
                        providers=providers,
                        enabled_providers=enabled_providers,
                        is_demo_user=is_demo_user)

@main_bp.route('/resources')
def resources():
    """Resources overview page"""
    if 'user' not in session:
        session['user'] = {
            'id': '106509284268867883869',  # Use the actual user ID from the database
            'email': 'real@infrazen.com',
            'name': 'Real User',
            'picture': ''
        }
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        # Demo user: show mock data
        overview = get_overview()
        resources = overview['resources']
        providers = overview['providers']
        # Group resources by provider for demo
        resources_by_provider = {}
        for resource in resources:
            provider_id = resource.get('provider_id', 'demo-provider')
            if provider_id not in resources_by_provider:
                resources_by_provider[provider_id] = []
            resources_by_provider[provider_id].append(resource)
    else:
        # Real user: show real database data
        try:
            # Use the string user_id directly since it's stored as floating point in SQLite
            user_id_str = user['id']
            resources = get_real_user_resources(user_id_str)
            providers = get_real_user_providers(user_id_str)
            # Get latest snapshot metadata for performance data
            snapshot_metadata = get_latest_snapshot_metadata(user_id_str)
            # Group resources by provider
            resources_by_provider = {}
            for resource in resources:
                provider_id = resource.provider.id
                if provider_id not in resources_by_provider:
                    resources_by_provider[provider_id] = []
                resources_by_provider[provider_id].append(resource)
            
        except Exception as e:
            print(f"Error loading resources: {e}")
            # Fallback to empty data
            resources = []
            providers = []
            snapshot_metadata = {}
            resources_by_provider = {}
    
    return render_template('resources.html', 
                        user=user,
                        active_page='resources',
                        page_title='Ресурсы',
                        page_subtitle='Обзор всех облачных ресурсов',
                        resources=resources,
                        providers=providers,
                        resources_by_provider=resources_by_provider,
                        snapshot_metadata=snapshot_metadata,
                        is_demo_user=is_demo_user)

@main_bp.route('/analytics')
def analytics():
    """Analytics page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        # Demo user: show mock data
        overview = get_overview()
    else:
        # Real user: show real database data
        overview = get_real_user_overview(user['id'])
    
    return render_template('page.html', 
                        user=user,
                        active_page='analytics',
                        page_title='Аналитика',
                        page_subtitle='Детальная аналитика расходов и использования',
                        overview=overview,
                        is_demo_user=is_demo_user)

@main_bp.route('/recommendations')
def recommendations():
    """Recommendations page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'

    # Render real recommendations page; data will be fetched via API from client-side JS
    return render_template('recommendations.html', 
                        user=user,
                        active_page='recommendations',
                        page_title='Рекомендации',
                        page_subtitle='Оптимизация расходов и рекомендации',
                        is_demo_user=is_demo_user)

@main_bp.route('/business_context')
def business_context():
    """Business context page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        overview = get_overview()
    else:
        overview = get_real_user_overview(user['id'])
    
    return render_template('page.html', 
                        user=user,
                        active_page='business_context',
                        page_title='Бизнес-контекст',
                        page_subtitle='Управление бизнес-контекстом ресурсов',
                        overview=overview,
                        is_demo_user=is_demo_user)

@main_bp.route('/reports')
def reports():
    """Reports page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        overview = get_overview()
    else:
        overview = get_real_user_overview(user['id'])
    
    return render_template('page.html', 
                        user=user,
                        active_page='reports',
                        page_title='Отчеты',
                        page_subtitle='Детальные отчеты по расходам',
                        overview=overview,
                        is_demo_user=is_demo_user)

@main_bp.route('/settings')
def settings():
    """Settings page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    user = session['user']
    is_demo_user = user.get('id') == 'demo-user-123'
    
    if is_demo_user:
        overview = get_overview()
    else:
        overview = get_real_user_overview(user['id'])
    
    return render_template('settings.html', 
                        user=user,
                        active_page='settings',
                        page_title='Settings',
                        page_subtitle='Manage your account settings',
                        overview=overview,
                        is_demo_user=is_demo_user,
                        google_client_id=current_app.config.get('GOOGLE_CLIENT_ID'))

# Helper functions for real user data
def get_real_user_overview(user_id):
    """Get overview data for a real user from database using unified models"""
    
    # Get user's unified cloud providers
    providers = CloudProvider.query.filter_by(user_id=user_id).all()
    
    # Calculate totals
    total_connections = len(providers)
    active_connections = len([p for p in providers if p.is_active])
    
    total_expenses_rub = 0
    potential_savings_rub = 0
    active_resources = 0
    
    for provider in providers:
        # Assuming provider_metadata contains billing_info and recommendations
        if provider.provider_metadata:
            metadata = json.loads(provider.provider_metadata)
            total_expenses_rub += metadata.get('total_monthly_cost', 0)
            # Sum potential savings from recommendations
            for rec in metadata.get('recommendations', []):
                potential_savings_rub += rec.get('savings_rub', 0)
        
        # Count active resources for this provider
        active_resources += Resource.query.filter_by(provider_id=provider.id, status='active').count()
    
    # Mock trend data for now
    from datetime import timedelta
    trend = [
        {'date': (datetime.now() - timedelta(days=i)).isoformat(), 'cost': (10000 + i * 100 + (i % 5) * 500)} 
        for i in range(30, 0, -1)
    ]
    
    # Mock usage data for now
    usage = {
        'cpu': {'used_vcpu': 50, 'available_vcpu': 100, 'percent': 50},
        'ram': {'used_gb': 64, 'available_gb': 128, 'percent': 50},
        'storage': {'used_tb': 5, 'available_tb': 10, 'percent': 50},
        'network': {'used_tb': 2, 'limit_tb': 10, 'percent': 20}
    }
    
    # Format providers for dashboard display
    formatted_providers = []
    for provider in providers:
        formatted_providers.append({
            'id': provider.id,
            'code': provider.provider_type,
            'name': provider.connection_name,
            'status': 'connected' if provider.is_active else 'disconnected',
            'added_at': provider.created_at.strftime('%d.%m.%Y') if provider.created_at else 'Неизвестно',
            'last_sync': provider.last_sync.strftime('%d.%m.%Y %H:%M') if provider.last_sync else 'Никогда'
        })
    
    return {
        'kpis': {
            'total_expenses_rub': total_expenses_rub,
            'potential_savings_rub': potential_savings_rub,
            'active_resources': active_resources,
            'connected_providers': total_connections
        },
        'providers': formatted_providers,
        'trend': trend,
        'resources': [], # Resources are fetched separately
        'recommendations': [], # Recommendations are fetched separately
        'usage': usage
    }

def get_real_user_resources(user_id):
    """Get resources for a real user from database - show resources from latest snapshot for each provider"""
    from app.core.models.sync import SyncSnapshot, ResourceState
    
    # Get all providers and filter by user_id in Python to avoid floating point precision issues
    all_providers = CloudProvider.query.all()
    # Convert scientific notation to integer string for comparison
    user_id_int = int(float(user_id))
    providers = [p for p in all_providers if int(float(p.user_id)) == user_id_int]
    all_resources = []
    
    for provider in providers:
        # Get the latest successful sync snapshot for this provider
        latest_snapshot = SyncSnapshot.query.filter_by(
            provider_id=provider.id, 
            sync_status='success'
        ).order_by(SyncSnapshot.created_at.desc()).first()
        
        if latest_snapshot:
            # Get resources from the latest snapshot
            resource_states = ResourceState.query.filter_by(
                sync_snapshot_id=latest_snapshot.id
            ).all()
            
            # Get the actual Resource objects
            resource_ids = [rs.resource_id for rs in resource_states if rs.resource_id]
            if resource_ids:
                provider_resources = Resource.query.filter(Resource.id.in_(resource_ids)).all()
                
                # Separate resources with and without performance data
                resources_with_performance = []
                resources_without_performance = []
                
                for resource in provider_resources:
                    tags = resource.get_all_tags()
                    has_performance = 'cpu_avg_usage' in tags or 'memory_avg_usage_mb' in tags
                    
                    if has_performance:
                        resources_with_performance.append(resource)
                    else:
                        resources_without_performance.append(resource)
                
                # Add performance resources first, then others
                all_resources.extend(resources_with_performance)
                all_resources.extend(resources_without_performance)
        else:
            # Fallback: if no snapshots, show all resources (for backward compatibility)
            provider_resources = Resource.query.filter_by(provider_id=provider.id).all()
            
            # Separate resources with and without performance data
            resources_with_performance = []
            resources_without_performance = []
            
            for resource in provider_resources:
                tags = resource.get_all_tags()
                has_performance = 'cpu_avg_usage' in tags or 'memory_avg_usage_mb' in tags
                
                if has_performance:
                    resources_with_performance.append(resource)
                else:
                    resources_without_performance.append(resource)
            
            # Add performance resources first, then others
            all_resources.extend(resources_with_performance)
            all_resources.extend(resources_without_performance)
    
    return all_resources

def get_real_user_providers(user_id):
    """Get providers for a real user from database using unified models"""
    
    # Get all providers and filter by user_id in Python to avoid floating point precision issues
    all_providers = CloudProvider.query.all()
    # Convert scientific notation to integer string for comparison
    user_id_int = int(float(user_id))
    providers = [p for p in all_providers if int(float(p.user_id)) == user_id_int]
    
    return [{
        'id': provider.id,  # Use the actual database ID
        'provider_type': provider.provider_type,
        'connection_name': provider.connection_name,
        'code': provider.provider_type,
        'name': provider.provider_type.title(),
        'status': 'connected' if provider.is_active else 'disconnected',
        'added_at': provider.created_at.isoformat() if provider.created_at else '2024-01-01',
        'details': {
            'connection_name': provider.connection_name,
            'account_id': provider.account_id,
            'last_sync': provider.last_sync.isoformat() if provider.last_sync else None
        }
    } for provider in providers]

def get_latest_snapshot_metadata(user_id):
    """Get the latest snapshot metadata for performance data"""
    from app.core.models.sync import SyncSnapshot
    import json
    
    # Get all providers and filter by user_id in Python to avoid floating point precision issues
    all_providers = CloudProvider.query.all()
    # Convert scientific notation to integer string for comparison
    user_id_int = int(float(user_id))
    providers = [p for p in all_providers if int(float(p.user_id)) == user_id_int]
    metadata = {}
    
    for provider in providers:
        if provider.last_sync:
            # Get the latest successful sync snapshot for this provider
            latest_snapshot = SyncSnapshot.query.filter(
                SyncSnapshot.provider_id == provider.id,
                SyncSnapshot.sync_status == 'success'
            ).order_by(SyncSnapshot.sync_completed_at.desc()).first()
            
            if latest_snapshot and latest_snapshot.metadata:
                # Ensure metadata is JSON serializable by converting to dict
                try:
                    # Convert to JSON and back to ensure serialization
                    json_str = json.dumps(latest_snapshot.metadata, default=str)
                    clean_metadata = json.loads(json_str)
                    metadata[provider.id] = clean_metadata
                except (TypeError, ValueError) as e:
                    print(f"Warning: Could not serialize metadata for provider {provider.id}: {e}")
                    # Fallback to empty dict
                    metadata[provider.id] = {}
    
    return metadata
