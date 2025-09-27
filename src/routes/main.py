from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from src.data.mock_data import get_overview, get_connected_providers, get_resources, get_recommendations, generate_expense_trend, get_usage_summary

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

    overview = get_overview()

    return render_template(
        'dashboard.html',
        user=session['user'],
        active_page='dashboard',
        overview=overview
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
    
    overview = get_overview()
    
    return render_template('connections.html', 
                         user=session['user'],
                         active_page='connections',
                         page_title='Подключения облаков',
                         page_subtitle='Управление подключениями к облачным провайдерам',
                         providers=overview['providers'])

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
    
    overview = get_overview()
    
    return render_template('resources.html', 
                         user=session['user'],
                         active_page='resources',
                         page_title='Ресурсы',
                         page_subtitle='Управление облачными ресурсами',
                         resources=overview['resources'],
                         providers=overview['providers'])

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
