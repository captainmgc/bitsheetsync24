#!/bin/bash
# List and manage database backups

BACKUP_DIR="/home/captain/bitsheet24/backups"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📦 BitSheet24 Database Backups${NC}"
echo "================================"
echo ""

# Check if backup directory exists
if [ ! -d "${BACKUP_DIR}" ]; then
    echo -e "${YELLOW}⚠️  No backups directory found${NC}"
    exit 1
fi

# Count backups
TOTAL=$(ls -1 "${BACKUP_DIR}"/bitsheet_backup_*.sql.gz 2>/dev/null | wc -l)

if [ ${TOTAL} -eq 0 ]; then
    echo -e "${YELLOW}No backups found${NC}"
    echo ""
    echo "Run: ./scripts/backup_database.sh to create a backup"
    exit 0
fi

echo -e "Total backups: ${GREEN}${TOTAL}${NC}"
echo ""

# Calculate total size
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)
echo "Total size: ${TOTAL_SIZE}"
echo ""

# List backups with details
echo "Recent backups:"
echo "---------------"

ls -lht "${BACKUP_DIR}"/bitsheet_backup_*.sql.gz 2>/dev/null | while IFS= read -r line; do
    # Extract filename
    filename=$(echo "${line}" | awk '{print $NF}')
    
    # Extract date from filename
    base=$(basename "${filename}")
    date_part=$(echo "${base}" | sed 's/bitsheet_backup_//' | sed 's/.sql.gz//')
    
    # Format: YYYYMMDD_HHMMSS -> YYYY-MM-DD HH:MM:SS
    formatted_date=$(echo "${date_part}" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
    
    # Get file size
    size=$(echo "${line}" | awk '{print $5}')
    
    # Check if checksum exists
    checksum=""
    if [ -f "${filename}.md5" ]; then
        checksum=" ✓"
    fi
    
    echo -e "  ${GREEN}●${NC} ${formatted_date}  [${size}]${checksum}"
    echo "    ${filename}"
done

echo ""
echo "Commands:"
echo "  Backup:  ./scripts/backup_database.sh"
echo "  Restore: ./scripts/restore_database.sh <backup_file>"
echo "  Verify:  md5sum -c <backup_file>.md5"
