#!/bin/bash
# Setup local MySQL database for InfraZen development

echo "=========================================="
echo "InfraZen Local MySQL Setup"
echo "=========================================="
echo ""

# Database configuration
DB_NAME="infrazen_dev"
DB_USER="infrazen_user"
DB_PASS="infrazen_password"

echo "This script will create a MySQL database for InfraZen development."
echo ""
echo "Database Name: $DB_NAME"
echo "Database User: $DB_USER"
echo "Database Password: $DB_PASS"
echo ""
echo "Make sure MySQL is running on your system."
echo ""

read -p "Enter MySQL root password: " -s MYSQL_ROOT_PASS
echo ""

# Create database and user
echo ""
echo "Creating database and user..."

mysql -u root -p"$MYSQL_ROOT_PASS" <<EOF
-- Create database
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user (if not exists)
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';

-- Grant privileges
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Show databases
SHOW DATABASES LIKE '$DB_NAME';
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ MySQL database setup completed successfully!"
    echo ""
    echo "Database connection details:"
    echo "  Host: localhost"
    echo "  Port: 3306"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASS"
    echo ""
    echo "Connection URL:"
    echo "  mysql+pymysql://$DB_USER:$DB_PASS@localhost:3306/$DB_NAME?charset=utf8mb4"
    echo ""
    echo "Next steps:"
    echo "  1. Update config.env with the DATABASE_URL above"
    echo "  2. Run: python init_database.py"
    echo "  3. Run: python scripts/export_sqlite_data.py (to backup existing data)"
    echo "  4. Run: python scripts/import_data_to_mysql.py (to import data)"
    echo ""
else
    echo ""
    echo "❌ Error setting up MySQL database"
    echo "Please check your MySQL root password and try again"
    exit 1
fi

