from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from wtforms.widgets import PasswordInput
import re

class BegetConnectionForm(FlaskForm):
    """Form for adding Beget hosting connection"""
    
    # Basic connection details
    connection_name = StringField(
        'Название подключения',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={
            'placeholder': 'Мой Beget аккаунт',
            'class': 'form-control'
        }
    )
    
    username = StringField(
        'Имя пользователя',
        validators=[DataRequired(), Length(min=3, max=100)],
        render_kw={
            'placeholder': 'your_beget_username',
            'class': 'form-control'
        }
    )
    
    password = PasswordField(
        'Пароль',
        validators=[DataRequired(), Length(min=6, max=255)],
        render_kw={
            'placeholder': '••••••••',
            'class': 'form-control'
        }
    )
    
    # API configuration
    api_url = StringField(
        'API URL',
        default='https://api.beget.com',
        validators=[DataRequired()],
        render_kw={
            'placeholder': 'https://api.beget.com',
            'class': 'form-control'
        }
    )
    
    # Connection options
    auto_sync = BooleanField(
        'Автоматическая синхронизация',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    sync_interval = SelectField(
        'Интервал синхронизации',
        choices=[
            ('hourly', 'Каждый час'),
            ('daily', 'Ежедневно'),
            ('weekly', 'Еженедельно'),
            ('manual', 'Только вручную')
        ],
        default='daily',
        render_kw={'class': 'form-select'}
    )
    
    # Notification settings
    enable_notifications = BooleanField(
        'Уведомления о изменениях',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    notification_email = StringField(
        'Email для уведомлений',
        validators=[Email()],
        render_kw={
            'placeholder': 'notifications@example.com',
            'class': 'form-control'
        }
    )
    
    # Advanced settings
    connection_timeout = SelectField(
        'Таймаут подключения',
        choices=[
            ('30', '30 секунд'),
            ('60', '1 минута'),
            ('120', '2 минуты'),
            ('300', '5 минут')
        ],
        default='60',
        render_kw={'class': 'form-select'}
    )
    
    retry_attempts = SelectField(
        'Количество попыток',
        choices=[
            ('1', '1 попытка'),
            ('2', '2 попытки'),
            ('3', '3 попытки'),
            ('5', '5 попыток')
        ],
        default='3',
        render_kw={'class': 'form-select'}
    )
    
    # Resource filters (what to sync)
    sync_domains = BooleanField(
        'Синхронизировать домены',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    sync_databases = BooleanField(
        'Синхронизировать базы данных',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    sync_ftp_accounts = BooleanField(
        'Синхронизировать FTP аккаунты',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    sync_dns_records = BooleanField(
        'Синхронизировать DNS записи',
        default=False,
        render_kw={'class': 'form-check-input'}
    )
    
    sync_billing_info = BooleanField(
        'Синхронизировать биллинг',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    # Description
    description = TextAreaField(
        'Описание',
        render_kw={
            'placeholder': 'Дополнительная информация о подключении...',
            'class': 'form-control',
            'rows': 3
        }
    )
    
    # Submit button
    submit = SubmitField(
        'Подключить Beget',
        render_kw={'class': 'btn btn-primary btn-lg'}
    )
    
    test_connection = SubmitField(
        'Тест подключения',
        render_kw={'class': 'btn btn-outline-secondary'}
    )
    
    def validate_username(self, field):
        """Validate username format"""
        username = field.data.strip()
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValidationError('Имя пользователя может содержать только буквы, цифры, дефисы и подчеркивания')
    
    def validate_api_url(self, field):
        """Validate API URL format"""
        url = field.data.strip()
        if not url.startswith(('http://', 'https://')):
            raise ValidationError('URL должен начинаться с http:// или https://')
    
    def validate_connection_name(self, field):
        """Validate connection name uniqueness"""
        # This will be checked in the route handler against the database
        name = field.data.strip()
        if len(name) < 2:
            raise ValidationError('Название подключения должно содержать минимум 2 символа')

class BegetSyncForm(FlaskForm):
    """Form for manual synchronization of Beget resources"""
    
    sync_type = SelectField(
        'Тип синхронизации',
        choices=[
            ('full', 'Полная синхронизация'),
            ('domains', 'Только домены'),
            ('databases', 'Только базы данных'),
            ('ftp', 'Только FTP аккаунты'),
            ('billing', 'Только биллинг')
        ],
        default='full',
        render_kw={'class': 'form-select'}
    )
    
    force_refresh = BooleanField(
        'Принудительное обновление',
        render_kw={'class': 'form-check-input'}
    )
    
    submit = SubmitField(
        'Запустить синхронизацию',
        render_kw={'class': 'btn btn-warning'}
    )

class BegetSettingsForm(FlaskForm):
    """Form for updating Beget connection settings"""
    
    connection_name = StringField(
        'Название подключения',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={'class': 'form-control'}
    )
    
    auto_sync = BooleanField(
        'Автоматическая синхронизация',
        render_kw={'class': 'form-check-input'}
    )
    
    sync_interval = SelectField(
        'Интервал синхронизации',
        choices=[
            ('hourly', 'Каждый час'),
            ('daily', 'Ежедневно'),
            ('weekly', 'Еженедельно'),
            ('manual', 'Только вручную')
        ],
        render_kw={'class': 'form-select'}
    )
    
    enable_notifications = BooleanField(
        'Уведомления о изменениях',
        render_kw={'class': 'form-check-input'}
    )
    
    notification_email = StringField(
        'Email для уведомлений',
        validators=[Email()],
        render_kw={'class': 'form-control'}
    )
    
    is_active = BooleanField(
        'Активное подключение',
        render_kw={'class': 'form-check-input'}
    )
    
    description = TextAreaField(
        'Описание',
        render_kw={
            'class': 'form-control',
            'rows': 3
        }
    )
    
    submit = SubmitField(
        'Сохранить настройки',
        render_kw={'class': 'btn btn-primary'}
    )
    
    test_connection = SubmitField(
        'Тест подключения',
        render_kw={'class': 'btn btn-outline-secondary'}
    )
