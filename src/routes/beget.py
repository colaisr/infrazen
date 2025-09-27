from flask import Blueprint, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
import json
import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.user import db
from src.models.beget import BegetConnection, BegetResource, BegetDomain, BegetDatabase, BegetFTPAccount
from api.beget_client import BegetAPIClient, BegetAPIError

beget_bp = Blueprint('beget', __name__, url_prefix='/connections/beget')

@beget_bp.route('/')
def test_route():
    """Test route to verify blueprint registration"""
    return jsonify({'message': 'Beget blueprint is working!', 'status': 'success'})

@beget_bp.route('/add', methods=['POST'])
def add_connection():
    """Add a new Beget connection"""
    print("DEBUG: add_connection route called")
    try:
        # Get form data
        connection_name = request.form.get('connection_name')
        username = request.form.get('username')
        password = request.form.get('password')
        api_url = request.form.get('api_url', 'https://api.beget.com')
        
        # Optional fields
        auto_sync = request.form.get('auto_sync') == 'on'
        sync_interval = request.form.get('sync_interval', 'daily')
        enable_notifications = request.form.get('enable_notifications') == 'on'
        description = request.form.get('description', '')
        
        # Validate required fields
        if not all([connection_name, username, password]):
            flash('Заполните все обязательные поля', 'error')
            return redirect(url_for('main.connections'))
        
        # Get user ID from session
        user_id = session.get('user', {}).get('id')
        
        # Handle demo user case - they can't create real connections
        if user_id == 'demo-user-123':
            flash('Demo users cannot create real connections. Please log in with a real account.', 'error')
            return redirect(url_for('main.connections'))
        
        # For real users, use their actual user ID
        if not user_id:
            flash('User not authenticated. Please log in.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if connection name already exists
        existing = BegetConnection.query.filter_by(
            connection_name=connection_name,
            user_id=user_id
        ).first()
        
        if existing:
            flash('Подключение с таким названием уже существует', 'error')
            return redirect(url_for('main.connections'))
        
        # Test connection before saving
        try:
            client = BegetAPIClient(username, password, api_url)
            account_info = client.test_connection()
        except BegetAPIError as e:
            flash(f'Ошибка подключения к Beget API: {str(e)}', 'error')
            return redirect(url_for('main.connections'))
        
        # Create new connection
        connection = BegetConnection(
            user_id=user_id,
            connection_name=connection_name,
            username=username,
            password=generate_password_hash(password),  # Encrypt password
            api_url=api_url,
            account_info=json.dumps(account_info),
            domains_count=account_info.get('domains_count', 0),
            databases_count=account_info.get('databases_count', 0),
            ftp_accounts_count=account_info.get('ftp_accounts_count', 0)
        )
        
        db.session.add(connection)
        db.session.commit()
        
        # Initial sync
        try:
            sync_beget_resources(connection.id)
            flash('Подключение к Beget успешно добавлено и синхронизировано!', 'success')
        except Exception as e:
            flash('Подключение добавлено, но произошла ошибка при синхронизации данных', 'warning')
        
        return redirect(url_for('main.connections'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении подключения: {str(e)}', 'error')
        return redirect(url_for('main.connections'))

@beget_bp.route('/test', methods=['POST'])
def test_connection():
    """Test Beget API connection"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        api_url = data.get('api_url', 'https://api.beget.com')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Заполните имя пользователя и пароль'})
        
        # Test connection
        client = BegetAPIClient(username, password, api_url)
        account_info = client.test_connection()
        
        return jsonify({
            'success': True,
            'message': 'Подключение успешно установлено',
            'account_info': account_info
        })
        
    except BegetAPIError as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Неожиданная ошибка: {str(e)}'})

@beget_bp.route('/sync/<int:connection_id>', methods=['POST'])
def sync_connection(connection_id):
    """Manually sync Beget resources"""
    try:
        connection = BegetConnection.query.get_or_404(connection_id)
        
        # Verify user ownership
        if connection.user_id != session.get('user_id', 1):
            flash('У вас нет прав для синхронизации этого подключения', 'error')
            return redirect(url_for('main.connections'))
        
        sync_beget_resources(connection_id)
        flash('Синхронизация завершена успешно', 'success')
        
        return redirect(url_for('main.connections'))
        
    except Exception as e:
        flash(f'Ошибка синхронизации: {str(e)}', 'error')
        return redirect(url_for('main.connections'))

@beget_bp.route('/delete/<int:connection_id>', methods=['POST'])
def delete_connection(connection_id):
    """Delete Beget connection"""
    try:
        connection = BegetConnection.query.get_or_404(connection_id)
        
        # Verify user ownership
        if connection.user_id != session.get('user_id', 1):
            flash('У вас нет прав для удаления этого подключения', 'error')
            return redirect(url_for('main.connections'))
        
        # Delete connection (cascade will delete resources)
        db.session.delete(connection)
        db.session.commit()
        
        flash('Подключение успешно удалено', 'success')
        return redirect(url_for('main.connections'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении подключения: {str(e)}', 'error')
        return redirect(url_for('main.connections'))

def sync_beget_resources(connection_id):
    """Sync resources for a Beget connection"""
    connection = BegetConnection.query.get(connection_id)
    if not connection:
        raise Exception("Connection not found")
    
    # Create API client (we'll need to store password securely in production)
    # For now, we'll use mock data since we can't decrypt the password
    try:
        # In production, you'd decrypt the password here
        # For demo purposes, we'll use mock data
        from data.mock_data import get_beget_mock_resources
        
        mock_resources = get_beget_mock_resources()
        
        # Clear existing resources
        BegetResource.query.filter_by(connection_id=connection_id).delete()
        
        # Add domains
        for domain_data in mock_resources['domains']:
            resource = BegetResource(
                connection_id=connection_id,
                resource_id=domain_data['id'],
                resource_type='domain',
                name=domain_data['name'],
                status=domain_data['status'],
                config=json.dumps(domain_data),
                monthly_cost=domain_data['monthly_cost']
            )
            db.session.add(resource)
            db.session.flush()  # Get the resource ID
            
            # Add domain details
            domain_detail = BegetDomain(
                resource_id=resource.id,
                domain_name=domain_data['name'],
                registrar=domain_data.get('registrar'),
                registration_date=domain_data.get('registration_date'),
                expiration_date=domain_data.get('expiration_date'),
                nameservers=json.dumps(domain_data.get('nameservers', [])),
                hosting_plan=domain_data.get('hosting_plan'),
                monthly_cost=domain_data['monthly_cost']
            )
            db.session.add(domain_detail)
        
        # Add databases
        for db_data in mock_resources['databases']:
            resource = BegetResource(
                connection_id=connection_id,
                resource_id=db_data['id'],
                resource_type='database',
                name=db_data['name'],
                status='active',
                config=json.dumps(db_data),
                monthly_cost=db_data['monthly_cost']
            )
            db.session.add(resource)
            db.session.flush()
            
            # Add database details
            database_detail = BegetDatabase(
                resource_id=resource.id,
                database_name=db_data['name'],
                database_type=db_data['type'],
                size_mb=db_data['size_mb'],
                username=db_data.get('username'),
                host=db_data.get('host'),
                port=db_data.get('port', 3306),
                monthly_cost=db_data['monthly_cost']
            )
            db.session.add(database_detail)
        
        # Add FTP accounts
        for ftp_data in mock_resources['ftp_accounts']:
            resource = BegetResource(
                connection_id=connection_id,
                resource_id=ftp_data['id'],
                resource_type='ftp',
                name=ftp_data['username'],
                status='active' if ftp_data.get('is_active') else 'inactive',
                config=json.dumps(ftp_data),
                monthly_cost=ftp_data['monthly_cost']
            )
            db.session.add(resource)
            db.session.flush()
            
            # Add FTP details
            ftp_detail = BegetFTPAccount(
                resource_id=resource.id,
                username=ftp_data['username'],
                home_directory=ftp_data.get('home_directory'),
                disk_quota_mb=ftp_data.get('disk_quota_mb', 0),
                disk_used_mb=ftp_data.get('disk_used_mb', 0),
                server_host=ftp_data.get('server_host'),
                port=ftp_data.get('port', 21),
                is_active=ftp_data.get('is_active', True),
                monthly_cost=ftp_data['monthly_cost']
            )
            db.session.add(ftp_detail)
        
        # Update connection stats
        connection.domains_count = len(mock_resources['domains'])
        connection.databases_count = len(mock_resources['databases'])
        connection.ftp_accounts_count = len(mock_resources['ftp_accounts'])
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Sync failed: {str(e)}")

@beget_bp.route('/api/resources/<int:connection_id>')
def get_resources_api(connection_id):
    """Get Beget resources as JSON API"""
    try:
        connection = BegetConnection.query.get_or_404(connection_id)
        
        # Verify user ownership
        if connection.user_id != session.get('user_id', 1):
            return jsonify({'error': 'Unauthorized'}), 403
        
        resources = BegetResource.query.filter_by(connection_id=connection_id).all()
        
        return jsonify({
            'connection': connection.to_dict(),
            'resources': [resource.to_dict() for resource in resources]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
