from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class BegetConnection(db.Model):
    """Model for storing Beget provider connections"""
    __tablename__ = 'beget_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    
    # Connection details
    connection_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Encrypted
    api_url = db.Column(db.String(255), default='https://api.beget.com')
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Connection metadata
    account_info = db.Column(db.Text)  # JSON string of account details
    domains_count = db.Column(db.Integer, default=0)
    databases_count = db.Column(db.Integer, default=0)
    ftp_accounts_count = db.Column(db.Integer, default=0)
    
    # Relationships
    resources = db.relationship('BegetResource', backref='connection', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'connection_name': self.connection_name,
            'username': self.username,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'domains_count': self.domains_count,
            'databases_count': self.databases_count,
            'ftp_accounts_count': self.ftp_accounts_count,
            'account_info': json.loads(self.account_info) if self.account_info else None
        }

class BegetResource(db.Model):
    """Model for storing Beget hosting resources"""
    __tablename__ = 'beget_resources'
    
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('beget_connections.id'), nullable=False)
    
    # Resource identification
    resource_id = db.Column(db.String(100), nullable=False)  # Beget's internal ID
    resource_type = db.Column(db.String(50), nullable=False)  # domain, database, ftp, email
    name = db.Column(db.String(255), nullable=False)
    
    # Resource details
    status = db.Column(db.String(50), default='active')
    config = db.Column(db.Text)  # JSON string of resource configuration
    monthly_cost = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('connection_id', 'resource_id', 'resource_type'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'name': self.name,
            'status': self.status,
            'config': json.loads(self.config) if self.config else None,
            'monthly_cost': self.monthly_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BegetDomain(db.Model):
    """Model for storing Beget domain details"""
    __tablename__ = 'beget_domains'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('beget_resources.id'), nullable=False)
    
    # Domain details
    domain_name = db.Column(db.String(255), nullable=False)
    registrar = db.Column(db.String(100))
    registration_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)
    
    # DNS and hosting
    nameservers = db.Column(db.Text)  # JSON array
    dns_records = db.Column(db.Text)  # JSON array
    hosting_plan = db.Column(db.String(100))
    
    # Costs
    registration_cost = db.Column(db.Float, default=0.0)
    renewal_cost = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'domain_name': self.domain_name,
            'registrar': self.registrar,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'nameservers': json.loads(self.nameservers) if self.nameservers else [],
            'dns_records': json.loads(self.dns_records) if self.dns_records else [],
            'hosting_plan': self.hosting_plan,
            'registration_cost': self.registration_cost,
            'renewal_cost': self.renewal_cost
        }

class BegetDatabase(db.Model):
    """Model for storing Beget database details"""
    __tablename__ = 'beget_databases'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('beget_resources.id'), nullable=False)
    
    # Database details
    database_name = db.Column(db.String(100), nullable=False)
    database_type = db.Column(db.String(50), default='mysql')  # mysql, postgresql
    size_mb = db.Column(db.Integer, default=0)
    
    # Access details
    username = db.Column(db.String(100))
    host = db.Column(db.String(255))
    port = db.Column(db.Integer, default=3306)
    
    # Costs
    monthly_cost = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'database_name': self.database_name,
            'database_type': self.database_type,
            'size_mb': self.size_mb,
            'username': self.username,
            'host': self.host,
            'port': self.port,
            'monthly_cost': self.monthly_cost
        }

class BegetFTPAccount(db.Model):
    """Model for storing Beget FTP account details"""
    __tablename__ = 'beget_ftp_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('beget_resources.id'), nullable=False)
    
    # FTP account details
    username = db.Column(db.String(100), nullable=False)
    home_directory = db.Column(db.String(255))
    disk_quota_mb = db.Column(db.Integer, default=0)
    disk_used_mb = db.Column(db.Integer, default=0)
    
    # Access details
    server_host = db.Column(db.String(255))
    port = db.Column(db.Integer, default=21)
    is_active = db.Column(db.Boolean, default=True)
    
    # Costs
    monthly_cost = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'home_directory': self.home_directory,
            'disk_quota_mb': self.disk_quota_mb,
            'disk_used_mb': self.disk_used_mb,
            'server_host': self.server_host,
            'port': self.port,
            'is_active': self.is_active,
            'monthly_cost': self.monthly_cost
        }
