#!/bin/bash
#
# Setup cron jobs for InfraZen price synchronization
# Usage: ./scripts/setup_cron.sh
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PYTHON="$PROJECT_ROOT/venv 2/bin/python"
SYNC_SCRIPT="$PROJECT_ROOT/scripts/sync_provider_prices.py"
LOG_DIR="$PROJECT_ROOT/logs"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "InfraZen Price Sync Cron Setup"
echo "=========================================="
echo ""

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Virtual environment not found at: $VENV_PYTHON${NC}"
    exit 1
fi

# Check if sync script exists
if [ ! -f "$SYNC_SCRIPT" ]; then
    echo -e "${RED}❌ Sync script not found at: $SYNC_SCRIPT${NC}"
    exit 1
fi

# Create logs directory
mkdir -p "$LOG_DIR"

echo -e "${GREEN}✅ Environment validated${NC}"
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Python:       $VENV_PYTHON"
echo "Sync script:  $SYNC_SCRIPT"
echo "Logs:         $LOG_DIR"
echo ""

# Display cron options
echo "=========================================="
echo "Available Cron Schedule Options:"
echo "=========================================="
echo ""
echo "1) Daily at 2:00 AM (recommended)"
echo "   0 2 * * * ..."
echo ""
echo "2) Every 6 hours"
echo "   0 */6 * * * ..."
echo ""
echo "3) Every 12 hours (noon and midnight)"
echo "   0 0,12 * * * ..."
echo ""
echo "4) Weekly (Sunday at 3:00 AM)"
echo "   0 3 * * 0 ..."
echo ""
echo "5) Custom schedule"
echo ""
echo "6) Manual (just show commands, don't set cron)"
echo ""

read -p "Choose option (1-6): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="Daily at 2:00 AM"
        ;;
    2)
        CRON_SCHEDULE="0 */6 * * *"
        DESCRIPTION="Every 6 hours"
        ;;
    3)
        CRON_SCHEDULE="0 0,12 * * *"
        DESCRIPTION="Every 12 hours"
        ;;
    4)
        CRON_SCHEDULE="0 3 * * 0"
        DESCRIPTION="Weekly on Sunday at 3:00 AM"
        ;;
    5)
        read -p "Enter custom cron schedule (e.g., '0 2 * * *'): " CRON_SCHEDULE
        DESCRIPTION="Custom: $CRON_SCHEDULE"
        ;;
    6)
        echo ""
        echo "=========================================="
        echo "Manual Setup Commands"
        echo "=========================================="
        echo ""
        echo "To add a cron job manually, run:"
        echo "  crontab -e"
        echo ""
        echo "Then add one of these lines:"
        echo ""
        echo "# Daily at 2 AM - sync all providers"
        echo "0 2 * * * cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT >> $LOG_DIR/cron_price_sync.log 2>&1"
        echo ""
        echo "# Every 6 hours - sync all providers"
        echo "0 */6 * * * cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT >> $LOG_DIR/cron_price_sync.log 2>&1"
        echo ""
        echo "# Daily at 3 AM - sync only Yandex (long-running)"
        echo "0 3 * * * cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT -p yandex >> $LOG_DIR/cron_yandex_sync.log 2>&1"
        echo ""
        echo "# Daily at 4 AM - sync Selectel and Beget"
        echo "0 4 * * * cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT -p selectel >> $LOG_DIR/cron_selectel_sync.log 2>&1"
        echo "0 4 * * * cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT -p beget >> $LOG_DIR/cron_beget_sync.log 2>&1"
        echo ""
        echo "To view current cron jobs:"
        echo "  crontab -l"
        echo ""
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

# Generate cron line
CRON_LINE="$CRON_SCHEDULE cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT >> $LOG_DIR/cron_price_sync.log 2>&1"

echo ""
echo "=========================================="
echo "Cron Job Configuration"
echo "=========================================="
echo ""
echo "Schedule:     $DESCRIPTION"
echo "Cron syntax:  $CRON_SCHEDULE"
echo ""
echo "Full cron line:"
echo "$CRON_LINE"
echo ""

read -p "Add this cron job? (y/n): " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo -e "${YELLOW}Cancelled${NC}"
    exit 0
fi

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SYNC_SCRIPT"; then
    echo -e "${YELLOW}⚠️  Warning: A cron job for this script already exists${NC}"
    echo ""
    crontab -l | grep "$SYNC_SCRIPT"
    echo ""
    read -p "Remove existing job and add new one? (y/n): " replace
    
    if [ "$replace" = "y" ] || [ "$replace" = "Y" ]; then
        # Remove existing job
        crontab -l 2>/dev/null | grep -v "$SYNC_SCRIPT" | crontab -
        echo -e "${GREEN}✅ Removed existing job${NC}"
    else
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Cron job added successfully!${NC}"
    echo ""
    echo "Current cron jobs:"
    crontab -l
    echo ""
    echo "Logs will be written to: $LOG_DIR/cron_price_sync.log"
    echo ""
    echo "To test manually:"
    echo "  cd $PROJECT_ROOT && \"$VENV_PYTHON\" $SYNC_SCRIPT"
    echo ""
    echo "To view cron jobs:"
    echo "  crontab -l"
    echo ""
    echo "To remove this cron job:"
    echo "  crontab -e"
    echo "  (then delete the line with sync_provider_prices.py)"
    echo ""
else
    echo -e "${RED}❌ Failed to add cron job${NC}"
    exit 1
fi

