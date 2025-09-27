from flask import Blueprint, render_template, session, redirect, url_for

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
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('dashboard.html', 
                         user=session['user'],
                         active_page='dashboard')

@main_bp.route('/connections')
def connections():
    """Cloud connections page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='connections',
                         page_title='Подключения облаков',
                         page_subtitle='Управление подключениями к облачным провайдерам')

@main_bp.route('/resources')
def resources():
    """Resources page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='resources',
                         page_title='Ресурсы',
                         page_subtitle='Управление облачными ресурсами')

@main_bp.route('/analytics')
def analytics():
    """Cost analytics page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='analytics',
                         page_title='Аналитика расходов',
                         page_subtitle='Детальный анализ облачных расходов')

@main_bp.route('/recommendations')
def recommendations():
    """Recommendations page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='recommendations',
                         page_title='Рекомендации',
                         page_subtitle='Рекомендации по оптимизации расходов')

@main_bp.route('/business-context')
def business_context():
    """Business context page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='business-context',
                         page_title='Бизнес-контекст',
                         page_subtitle='Привязка ресурсов к бизнес-целям')

@main_bp.route('/reports')
def reports():
    """Reports page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='reports',
                         page_title='Отчёты',
                         page_subtitle='Создание и управление отчётами')

@main_bp.route('/settings')
def settings():
    """Settings page"""
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    return render_template('page.html', 
                         user=session['user'],
                         active_page='settings',
                         page_title='Настройки',
                         page_subtitle='Настройки платформы и пользователя')
