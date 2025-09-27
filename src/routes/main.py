from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from src.data.mock_data import get_overview
from src.models.beget import BegetConnection, BegetResource, BegetDomain, BegetDatabase, BegetFTPAccount

main_bp = Blueprint('main', __name__)

def require_auth():
    """Check if user is authenticated"""
    if 'user' not in session:
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
            'id': 'demo-user-123',
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
        # Real user: show only real database connections
        from src.models.beget import BegetConnection
        
        # Get real connections from database
        beget_connections = BegetConnection.query.filter_by(user_id=user['id']).all()
        
        # Convert to provider format
        providers = []
        for conn in beget_connections:
            providers.append({
                'id': f"beget-{conn.id}",
                'code': 'beget',
                'name': 'Beget',
                'status': 'connected' if conn.is_active else 'disconnected',
                'added_at': conn.created_at.isoformat() if conn.created_at else '2024-01-01',
                'details': {
                    'connection_name': conn.connection_name,
                    'username': conn.username,
                    'domains_count': conn.domains_count,
                    'databases_count': conn.databases_count,
                    'ftp_accounts_count': conn.ftp_accounts_count
                }
            })
    
    return render_template('connections.html', 
                         user=user,
                         active_page='connections',
                         page_title='Подключения облаков',
                         page_subtitle='Управление подключениями к облачным провайдерам',
                         providers=providers,
                         is_demo_user=is_demo_user)

@main_bp.route('/resources')
def resources():
    """Resources page"""
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
        resources = overview['resources']
        providers = overview['providers']
    else:
        # Real user: show real database data
        resources = get_real_user_resources(user['id'])
        providers = get_real_user_providers(user['id'])
    
    return render_template('resources.html', 
                         user=user,
                         active_page='resources',
                         page_title='Ресурсы',
                         page_subtitle='Управление облачными ресурсами',
                         resources=resources,
                         providers=providers,
                         is_demo_user=is_demo_user)

@main_bp.route('/analytics')
def analytics():
    """Cost analytics page"""
    if 'user' not in session:
        session['user'] = {
            'id': 'demo-user-123',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }
    return render_template('page.html', 
                         user=session['user'],
                         active_page='analytics',
                         page_title='Аналитика расходов',
                         page_subtitle='Детальный анализ облачных расходов')

@main_bp.route('/recommendations')
def recommendations():
    """Recommendations page"""
    if 'user' not in session:
        session['user'] = {
            'id': 'demo-user-123',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }
    return render_template('page.html', 
                         user=session['user'],
                         active_page='recommendations',
                         page_title='Рекомендации',
                         page_subtitle='Рекомендации по оптимизации расходов')

@main_bp.route('/business-context')
def business_context():
    """Business context page"""
    if 'user' not in session:
        session['user'] = {
            'id': 'demo-user-123',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }
    return render_template('page.html', 
                         user=session['user'],
                         active_page='business-context',
                         page_title='Бизнес-контекст',
                         page_subtitle='Привязка ресурсов к бизнес-целям')

@main_bp.route('/reports')
def reports():
    """Reports page"""
    if 'user' not in session:
        session['user'] = {
            'id': 'demo-user-123',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }
    return render_template('page.html', 
                         user=session['user'],
                         active_page='reports',
                         page_title='Отчёты',
                         page_subtitle='Создание и управление отчётами')

@main_bp.route('/settings')
def settings():
    """Settings page"""
    if 'user' not in session:
        session['user'] = {
            'id': 'demo-user-123',
            'email': 'demo@infrazen.com',
            'name': 'Demo User',
            'picture': ''
        }
    return render_template('page.html', 
                         user=session['user'],
                         active_page='settings',
                         page_title='Настройки',
                         page_subtitle='Настройки платформы и пользователя')


@main_bp.route('/api/demo/overview')
def api_demo_overview():
    """JSON overview for demo data"""
    return jsonify(get_overview())


@main_bp.route('/api/demo/providers')
def api_demo_providers():
    return jsonify(get_connected_providers())


@main_bp.route('/api/demo/resources')
def api_demo_resources():
    return jsonify(get_resources())


@main_bp.route('/api/demo/recommendations')
def api_demo_recommendations():
    return jsonify(get_recommendations())


@main_bp.route('/api/demo/usage')
def api_demo_usage():
    return jsonify(get_usage_summary())


@main_bp.route('/api/demo/trend')
def api_demo_trend():
    return jsonify(generate_expense_trend())






# Helper functions for real user data
def get_real_user_overview(user_id):
    """Get overview data for a real user from database"""
    # Get user's connections
    connections = BegetConnection.query.filter_by(user_id=user_id).all()
    
    # Calculate totals
    total_connections = len(connections)
    active_connections = len([c for c in connections if c.is_active])
    
    # Get resources from all connections
    all_resources = []
    for conn in connections:
        all_resources.extend(conn.resources)
    
    # Calculate costs (mock for now - in real implementation, get from API)
    total_cost = sum([conn.domains_count * 150 + conn.databases_count * 50 + conn.ftp_accounts_count * 25 for conn in connections])
    
    return {
        'kpis': {
            'total_expenses_rub': total_cost,
            'potential_savings_rub': int(total_cost * 0.1),  # 10% savings estimate
            'active_resources': len(all_resources),
            'connected_providers': total_connections
        },
        'providers': [{
            'id': f"beget-{conn.id}",
            'code': 'beget',
            'name': 'Beget',
            'status': 'connected' if conn.is_active else 'disconnected',
            'added_at': conn.created_at.isoformat() if conn.created_at else '2024-01-01',
            'details': {
                'connection_name': conn.connection_name,
                'username': conn.username,
                'domains_count': conn.domains_count,
                'databases_count': conn.databases_count,
                'ftp_accounts_count': conn.ftp_accounts_count
            }
        } for conn in connections],
        'trend': [],  # Empty trend for real users initially
        'resources': all_resources,
        'recommendations': [],  # Empty for real users initially
        'usage': {
            'cpu': {'used_vcpu': 0, 'available_vcpu': 100, 'percent': 0},
            'ram': {'used_gb': 0, 'available_gb': 100, 'percent': 0},
            'storage': {'used_tb': 0, 'available_tb': 10, 'percent': 0},
            'network': {'used_tb': 0, 'limit_tb': 10, 'percent': 0}
        }
    }


def get_real_user_resources(user_id):
    """Get resources for a real user from database"""
    connections = BegetConnection.query.filter_by(user_id=user_id).all()
    all_resources = []
    
    for conn in connections:
        all_resources.extend(conn.resources)
    
    return all_resources


def get_real_user_providers(user_id):
    """Get providers for a real user from database"""
    connections = BegetConnection.query.filter_by(user_id=user_id).all()
    
    return [{
        'id': f"beget-{conn.id}",
        'code': 'beget',
        'name': 'Beget',
        'status': 'connected' if conn.is_active else 'disconnected',
        'added_at': conn.created_at.isoformat() if conn.created_at else '2024-01-01',
        'details': {
            'connection_name': conn.connection_name,
            'username': conn.username,
            'domains_count': conn.domains_count,
            'databases_count': conn.databases_count,
            'ftp_accounts_count': conn.ftp_accounts_count
        }
    } for conn in connections]
