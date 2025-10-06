# InfraZen User System Enhancement

## Overview

This document describes the enhanced user system for InfraZen that integrates Google OAuth data with database persistence and implements a comprehensive role-based access control system.

## Key Features

### 1. Google OAuth Integration
- **Automatic User Creation**: Users are automatically created in the database when they first log in with Google
- **Google Data Storage**: Stores Google profile information (picture, locale, verified email status)
- **Seamless Migration**: Existing users without Google IDs are updated when they log in with Google

### 2. Role-Based Access Control
- **Three Role Levels**:
  - `user`: Standard user with basic access
  - `admin`: Administrative user with user management capabilities
  - `super_admin`: Full system administrator with all permissions
- **Permission System**: Granular permissions for specific actions
- **Admin Interface**: Dedicated admin panel for user management

### 3. User Management Features
- **User CRUD Operations**: Create, read, update, delete users
- **Role Management**: Assign and modify user roles
- **Permission Control**: Set custom permissions for users
- **User Impersonation**: Admins can impersonate other users for support
- **Search and Filtering**: Find users by name, email, role, or status

## Database Schema Changes

### New User Model Fields

```python
# Google OAuth Integration
google_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
google_picture = db.Column(db.String(500))  # Profile picture URL
google_verified_email = db.Column(db.Boolean, default=False)
google_locale = db.Column(db.String(10))  # User's locale from Google

# Role and Permissions
role = db.Column(db.String(20), default='user', nullable=False, index=True)
permissions = db.Column(db.Text)  # JSON-encoded custom permissions

# Admin Functionality
created_by_admin = db.Column(db.Boolean, default=False)
admin_notes = db.Column(db.Text)

# Enhanced Tracking
login_count = db.Column(db.Integer, default=0)
```

### Permission System

The permission system uses JSON-encoded permissions with the following available permissions:

- `manage_users`: Can create, edit, and delete users
- `impersonate_users`: Can impersonate other users
- `view_all_data`: Can view data from all users
- `manage_providers`: Can manage cloud provider connections
- `manage_resources`: Can manage cloud resources

## API Endpoints

### Authentication (`/api/auth/`)
- `POST /google`: Handle Google OAuth authentication
- `GET /login`: Display login page
- `GET /logout`: Handle user logout

### Admin Management (`/api/admin/`)
- `GET /users`: List all users with pagination and filtering
- `GET /users/<id>`: Get specific user details
- `POST /users`: Create new user
- `PUT /users/<id>`: Update user
- `DELETE /users/<id>`: Delete user
- `GET /impersonate/<id>`: Impersonate user
- `GET /stop-impersonating`: Stop impersonation

## Usage Instructions

### 1. Initialize Database

Run the database initialization script to create tables and set up the super admin user:

```bash
python init_database.py
```

This will:
- Create all database tables
- Create a super admin user (admin@infrazen.com)
- Set up default permissions

### 2. User Authentication Flow

1. **First-time Google Login**:
   - User clicks "Sign in with Google"
   - Google OAuth token is verified
   - New user record is created in database with Google data
   - User is logged in and redirected to dashboard

2. **Returning Google Login**:
   - User clicks "Sign in with Google"
   - System finds existing user by Google ID
   - Login information is updated
   - User is logged in with their role and permissions

3. **Demo/Development Login**:
   - Demo users are handled in session only
   - No database persistence for demo users

### 3. Admin Functionality

#### Accessing Admin Panel
- Only users with `is_admin=True` can access admin features
- Admin section appears in sidebar navigation
- Admin users see "User Management" link

#### Managing Users
1. **View Users**: Paginated list with search and filtering
2. **Create User**: Add new users with email, name, role, and permissions
3. **Edit User**: Modify user details, role, and permissions
4. **Delete User**: Remove users (except super admins)
5. **Impersonate**: Login as another user for support

#### User Roles and Permissions

**Super Admin**:
- All permissions enabled by default
- Cannot be deleted
- Can manage all other users

**Admin**:
- Can manage users (if `manage_users` permission)
- Can impersonate users (if `impersonate_users` permission)
- Cannot delete super admins

**User**:
- Standard access to platform features
- Cannot access admin functions

### 4. Session Management

The system maintains both session-based authentication and database persistence:

```python
session['user'] = {
    'id': str(user.id),
    'db_id': user.id,
    'google_id': user.google_id,
    'email': user.email,
    'name': user.display_name,
    'picture': user.google_picture,
    'role': user.role,
    'is_admin': user.is_admin(),
    'permissions': user.get_permissions(),
    'impersonated': False,  # Set to True when impersonating
    'impersonated_by': None  # Email of admin doing impersonation
}
```

## Security Considerations

### 1. User Data Protection
- Google OAuth tokens are not stored (only profile data)
- Passwords are not required for Google OAuth users
- Sensitive data is excluded from user serialization

### 2. Admin Security
- Admin functions require authentication
- Role-based access control prevents unauthorized access
- Impersonation is logged and reversible

### 3. Data Integrity
- Foreign key constraints maintain data relationships
- User deletion cascades to related data
- Super admins cannot be deleted

## Migration from Existing System

The new system is backward compatible:

1. **Existing Users**: Will be updated with Google ID when they next log in
2. **Session Compatibility**: Existing sessions continue to work
3. **Demo Users**: Continue to work without database changes
4. **Gradual Migration**: Users are migrated as they log in

## Troubleshooting

### Common Issues

1. **Database Not Initialized**:
   - Run `python init_database.py`
   - Check database file permissions

2. **Google OAuth Not Working**:
   - Verify `GOOGLE_CLIENT_ID` environment variable
   - Check Google OAuth configuration

3. **Admin Access Denied**:
   - Ensure user has `is_admin=True`
   - Check user permissions in database

4. **User Not Found**:
   - Verify user exists in database
   - Check Google ID mapping

### Debugging

Enable debug logging to see authentication flow:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Advanced Permissions**: More granular permission system
2. **User Groups**: Group-based access control
3. **Audit Logging**: Track all admin actions
4. **Email Notifications**: Notify users of account changes
5. **SSO Integration**: Support for other identity providers
6. **API Authentication**: Token-based API access
7. **Two-Factor Authentication**: Enhanced security for admin users

## Support

For issues or questions about the user system:
1. Check the logs for error messages
2. Verify database schema is up to date
3. Ensure all environment variables are set
4. Test with demo user first before real Google OAuth
