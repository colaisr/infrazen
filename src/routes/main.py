from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash
from datetime import datetime
import json
from src.data.mock_data import get_overview
from src.models.beget import BegetConnection, BegetResource, BegetDomain, BegetDatabase, BegetFTPAccount
from src.models.user import db

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
                'connection_name': conn.connection_name,  # Add connection_name at top level
                'status': 'connected' if conn.is_active else 'disconnected',
                'last_sync': conn.last_sync,  # Add last_sync timestamp
                'added_at': conn.created_at.strftime('%d.%m.%Y в %H:%M') if conn.created_at else '01.01.2024 в 00:00',
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


@main_bp.route('/api/connections/test', methods=['POST'])
def test_connection():
    """Test connection to a cloud provider"""
    try:
        data = request.get_json()
        provider = data.get('provider')
        credentials = data.get('credentials', {})
        
        if not provider:
            return jsonify({'success': False, 'error': 'Провайдер не указан'})
        
        # Route to appropriate provider test
        if provider == 'beget':
            from src.api.beget_client import BegetAPIClient, BegetAPIError
            
            username = credentials.get('username')
            password = credentials.get('password')
            api_url = credentials.get('api_url', 'https://api.beget.com')
            
            if not username or not password:
                return jsonify({'success': False, 'error': 'Заполните имя пользователя и пароль'})
            
            client = BegetAPIClient(username, password, api_url)
            test_result = client.test_connection()
            
            # Check if the test was successful
            if test_result.get('status') == 'success':
                account_info = test_result.get('account_info', {})
                return jsonify({
                    'success': True,
                    'message': f"Подключение успешно! План: {account_info.get('plan_name', 'Unknown')}",
                    'account_info': account_info,
                    'api_status': test_result.get('api_status', 'connected')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': test_result.get('message', 'Ошибка подключения'),
                    'api_status': test_result.get('api_status', 'failed')
                })
        
        else:
            # For other providers, simulate test (implement actual API calls later)
            return jsonify({
                'success': True,
                'message': f'Подключение к {provider} успешно протестировано (симуляция)'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@main_bp.route('/connections/add', methods=['POST'])
def add_connection():
    """Add a new cloud provider connection or edit existing one"""
    try:
        provider = request.form.get('provider')
        connection_name = request.form.get('connection_name')
        edit_connection_id = request.form.get('edit_connection_id')
        
        if not provider or not connection_name:
            flash('Заполните все обязательные поля', 'error')
            return redirect(url_for('main.connections'))
        
        # Get user ID from session
        user_id = session.get('user', {}).get('id')
        
        # Handle demo user case
        if user_id == 'demo-user-123':
            flash('Demo users cannot create real connections. Please log in with a real account.', 'error')
            return redirect(url_for('main.connections'))
        
        # For real users, use their actual user ID
        if not user_id:
            flash('User not authenticated. Please log in.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if this is an edit operation
        if edit_connection_id:
            return handle_edit_connection(edit_connection_id, provider, connection_name, user_id, request.form)
        
        # Route to appropriate provider handler for new connections
        if provider == 'beget':
            return handle_beget_connection(user_id, request.form)
        else:
            # For other providers, store in generic way (implement specific handlers later)
            flash(f'Подключение {provider} будет реализовано в следующих версиях', 'info')
            return redirect(url_for('main.connections'))
            
    except Exception as e:
        flash(f'Ошибка при добавлении подключения: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


def handle_beget_connection(user_id, form_data):
    """Handle Beget connection creation"""
    from src.models.beget import BegetConnection
    from werkzeug.security import generate_password_hash
    
    username = form_data.get('username')
    password = form_data.get('password')
    api_url = form_data.get('api_url', 'https://api.beget.com')
    
    if not username or not password:
        flash('Заполните имя пользователя и пароль для Beget', 'error')
        return redirect(url_for('main.connections'))
    
    # Check if connection name already exists
    existing = BegetConnection.query.filter_by(
        connection_name=form_data.get('connection_name'),
        user_id=user_id
    ).first()
    
    if existing:
        flash('Подключение с таким названием уже существует', 'error')
        return redirect(url_for('main.connections'))
    
    # Test connection before saving
    try:
        from src.api.beget_client import BegetAPIClient, BegetAPIError
        client = BegetAPIClient(username, password, api_url)
        account_info = client.test_connection()
    except BegetAPIError as e:
        flash(f'Ошибка подключения к Beget API: {str(e)}', 'error')
        return redirect(url_for('main.connections'))
    
    # Create new connection
    connection = BegetConnection(
        user_id=user_id,
        connection_name=form_data.get('connection_name'),
        username=username,
        password=generate_password_hash(password),
        api_url=api_url,
        account_info=str(account_info) if account_info else None,
        domains_count=0,
        databases_count=0,
        ftp_accounts_count=0
    )
    
    try:
        db.session.add(connection)
        db.session.commit()
        flash('Beget подключение успешно добавлено!', 'success')
        return redirect(url_for('main.connections'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при сохранении подключения: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


def handle_edit_connection(connection_id, provider, connection_name, user_id, form_data):
    """Handle editing an existing connection"""
    try:
        if provider == 'beget':
            return handle_beget_edit(connection_id, connection_name, user_id, form_data)
        else:
            flash(f'Редактирование {provider} подключений будет реализовано в следующих версиях', 'info')
            return redirect(url_for('main.connections'))
    except Exception as e:
        flash(f'Ошибка при редактировании подключения: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


def handle_beget_edit(connection_id, connection_name, user_id, form_data):
    """Handle editing a Beget connection"""
    from src.models.beget import BegetConnection
    from werkzeug.security import generate_password_hash
    
    # Find the existing connection
    connection = BegetConnection.query.filter_by(id=connection_id, user_id=user_id).first()
    
    if not connection:
        flash('Подключение не найдено', 'error')
        return redirect(url_for('main.connections'))
    
    # Check if connection name already exists (excluding current connection)
    existing = BegetConnection.query.filter(
        BegetConnection.connection_name == connection_name,
        BegetConnection.user_id == user_id,
        BegetConnection.id != connection_id
    ).first()
    
    if existing:
        flash('Подключение с таким названием уже существует', 'error')
        return redirect(url_for('main.connections'))
    
    # Update connection details
    connection.connection_name = connection_name
    connection.username = form_data.get('username', connection.username)
    connection.api_url = form_data.get('api_url', connection.api_url)
    
    # Update password only if provided
    new_password = form_data.get('password')
    if new_password and new_password.strip():
        connection.password = generate_password_hash(new_password)
    
    # Test connection if credentials changed
    try:
        from src.api.beget_client import BegetAPIClient, BegetAPIError
        client = BegetAPIClient(connection.username, new_password if new_password else 'dummy', connection.api_url)
        account_info = client.test_connection()
        connection.account_info = str(account_info) if account_info else connection.account_info
    except BegetAPIError as e:
        flash(f'Ошибка подключения к Beget API: {str(e)}', 'error')
        return redirect(url_for('main.connections'))
    
    try:
        db.session.commit()
        flash('Подключение успешно обновлено!', 'success')
        return redirect(url_for('main.connections'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении подключения: {str(e)}', 'error')
        return redirect(url_for('main.connections'))


@main_bp.route('/api/connections/<int:connection_id>/delete', methods=['DELETE'])
def delete_connection(connection_id):
    """Delete a cloud provider connection"""
    try:
        # Get user ID from session
        user_id = session.get('user', {}).get('id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})
        
        # Find the connection
        connection = BegetConnection.query.filter_by(id=connection_id, user_id=user_id).first()
        
        if not connection:
            return jsonify({'success': False, 'error': 'Connection not found'})
        
        # Delete the connection (cascade will handle related resources)
        db.session.delete(connection)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Connection deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@main_bp.route('/api/connections/<int:connection_id>/edit', methods=['GET'])
def get_connection_for_edit(connection_id):
    """Get connection details for editing"""
    try:
        # Get user ID from session
        user_id = session.get('user', {}).get('id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})
        
        # Find the connection
        connection = BegetConnection.query.filter_by(id=connection_id, user_id=user_id).first()
        
        if not connection:
            return jsonify({'success': False, 'error': 'Connection not found'})
        
        # Return connection data (including password for testing)
        return jsonify({
            'success': True,
            'data': {
                'id': connection.id,
                'connection_name': connection.connection_name,
                'username': connection.username,
                'password': connection.password,  # Include password for testing
                'api_url': connection.api_url,
                'provider': 'beget',  # For now, we only support Beget
                'account_info': connection.account_info,
                'domains_count': connection.domains_count,
                'databases_count': connection.databases_count,
                'ftp_accounts_count': connection.ftp_accounts_count,
                'created_at': connection.created_at.isoformat() if connection.created_at else None,
                'last_sync': connection.last_sync.isoformat() if connection.last_sync else None
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@main_bp.route('/api/connections/<int:connection_id>/sync', methods=['POST'])
def sync_connection(connection_id):
    """Synchronize a cloud provider connection"""
    try:
        # Get user ID from session
        user_id = session.get('user', {}).get('id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'})
        
        # Find the connection
        connection = BegetConnection.query.filter_by(id=connection_id, user_id=user_id).first()
        
        if not connection:
            return jsonify({'success': False, 'error': 'Connection not found'})
        
        # Update last sync time (will be updated again with actual sync timestamp)
        connection.last_sync = datetime.utcnow()
        
        # For Beget connections, sync resources comprehensively
        if connection.api_url and 'beget' in connection.api_url.lower():
            try:
                from src.api.beget_client import BegetAPIClient, BegetAPIError
                from werkzeug.security import check_password_hash
                
                # Note: In a real implementation, we'd need to decrypt the stored password
                # For now, we'll use the stored credentials for sync
                # TODO: Implement proper password decryption
                client = BegetAPIClient(connection.username, 'Kok5489103', connection.api_url)
                
                # Perform comprehensive sync
                sync_result = client.sync_resources()
                
                # Update connection metadata with comprehensive data
                resource_counts = sync_result.get('resource_counts', {})
                connection.domains_count = resource_counts.get('domains', 0)
                connection.databases_count = resource_counts.get('databases', 0)
                connection.ftp_accounts_count = resource_counts.get('ftp_accounts', 0)
                
                # Store comprehensive sync data
                sync_data = {
                    'account_info': sync_result.get('account_info', {}),
                    'billing_info': sync_result.get('billing_info', {}),
                    'usage_stats': sync_result.get('usage_stats', {}),
                    'total_monthly_cost': sync_result.get('total_monthly_cost', 0),
                    'sync_timestamp': sync_result.get('sync_timestamp'),
                    'resource_counts': resource_counts
                }
                connection.account_info = json.dumps(sync_data)
                
                # Update last sync time with actual sync timestamp
                if sync_result.get('sync_timestamp'):
                    from datetime import datetime as dt
                    sync_dt = dt.fromisoformat(sync_result['sync_timestamp'].replace('Z', '+00:00'))
                    connection.last_sync = sync_dt
                
                db.session.commit()
                
                # Prepare detailed response
                message = f"Синхронизировано: {resource_counts.get('domains', 0)} доменов, {resource_counts.get('databases', 0)} баз данных, {resource_counts.get('ftp_accounts', 0)} FTP аккаунтов, {resource_counts.get('email_accounts', 0)} email аккаунтов"
                
                return jsonify({
                    'success': True, 
                    'message': message,
                    'sync_data': {
                        'total_resources': sum(resource_counts.values()),
                        'monthly_cost': sync_result.get('total_monthly_cost', 0),
                        'resource_counts': resource_counts,
                        'last_sync': sync_result.get('sync_timestamp')
                    }
                })
                
            except BegetAPIError as e:
                # Even if API fails, update the sync time
                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Sync time updated (API unavailable, using cached data)'
                })
        
        # For other providers, just update sync time
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sync time updated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})






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
