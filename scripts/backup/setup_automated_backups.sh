#!/bin/bash
# Setup automated database backups with cron

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 BitSheet24 Automated Backup Setup${NC}"
echo "======================================"
echo ""

# Check if running as the correct user
CURRENT_USER=$(whoami)
echo "Current user: ${CURRENT_USER}"
echo ""

# Backup script path
BACKUP_SCRIPT="/home/captain/bitsheet24/scripts/backup_database.sh"

# Check if backup script exists
if [ ! -f "${BACKUP_SCRIPT}" ]; then
    echo -e "${YELLOW}❌ Backup script not found: ${BACKUP_SCRIPT}${NC}"
    exit 1
fi

# Create cron entries
CRON_DAILY="0 2 * * * ${BACKUP_SCRIPT} >> /tmp/backup_cron.log 2>&1"
CRON_WEEKLY="0 3 * * 0 ${BACKUP_SCRIPT} >> /tmp/backup_cron.log 2>&1"
CRON_MONTHLY="0 4 1 * * ${BACKUP_SCRIPT} >> /tmp/backup_cron.log 2>&1"

echo "Proposed cron schedule:"
echo "----------------------"
echo -e "${GREEN}Daily backup:${NC}   Every day at 02:00 AM"
echo "  $CRON_DAILY"
echo ""
echo -e "${GREEN}Weekly backup:${NC}  Every Sunday at 03:00 AM"
echo "  $CRON_WEEKLY"
echo ""
echo -e "${GREEN}Monthly backup:${NC} 1st of each month at 04:00 AM"
echo "  $CRON_MONTHLY"
echo ""

# Ask for confirmation
read -p "Add these cron jobs? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Get existing crontab (or empty if none)
TEMP_CRON=$(mktemp)
crontab -l > "${TEMP_CRON}" 2>/dev/null || true

# Check if cron jobs already exist
if grep -q "${BACKUP_SCRIPT}" "${TEMP_CRON}"; then
    echo -e "${YELLOW}⚠️  Backup cron jobs already exist!${NC}"
    echo "Remove existing jobs first? (yes/no): "
    read -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        sed -i "\|${BACKUP_SCRIPT}|d" "${TEMP_CRON}"
        echo "Existing jobs removed."
    else
        echo "Keeping existing jobs."
        rm "${TEMP_CRON}"
        exit 0
    fi
fi

# Add new cron jobs
echo "# BitSheet24 Database Backups" >> "${TEMP_CRON}"
echo "${CRON_DAILY}" >> "${TEMP_CRON}"
echo "${CRON_WEEKLY}" >> "${TEMP_CRON}"
echo "${CRON_MONTHLY}" >> "${TEMP_CRON}"

# Install new crontab
crontab "${TEMP_CRON}"
rm "${TEMP_CRON}"

echo ""
echo -e "${GREEN}✅ Automated backups configured!${NC}"
echo ""
echo "Verify with: crontab -l"
echo "View logs: tail -f /tmp/backup_cron.log"
echo ""
echo "Next scheduled backups:"
echo "  Daily:   Tomorrow at 02:00 AM"
echo "  Weekly:  Next Sunday at 03:00 AM"  
echo "  Monthly: 1st of next month at 04:00 AM"
