#!/bin/bash
# PostgreSQL Database Restore Script for BitSheet24

# Configuration
DB_NAME="bitsheet_db"
DB_USER="bitsheet"
BACKUP_DIR="/home/captain/bitsheet24/backups"
LOG_FILE="${BACKUP_DIR}/restore.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <backup_file>${NC}"
    echo ""
    echo "Available backups:"
    ls -lht "${BACKUP_DIR}"/bitsheet_backup_*.sql.gz 2>/dev/null | head -10
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}❌ Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

# Verify checksum if exists
if [ -f "${BACKUP_FILE}.md5" ]; then
    log "🔍 Verifying backup integrity..."
    if md5sum -c "${BACKUP_FILE}.md5" > /dev/null 2>&1; then
        log "${GREEN}✅ Checksum verification passed${NC}"
    else
        log "${RED}❌ Checksum verification failed!${NC}"
        read -p "Continue anyway? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
            exit 1
        fi
    fi
fi

# Confirm restore
echo -e "${YELLOW}⚠️  WARNING: This will REPLACE the current database!${NC}"
echo "Database: ${DB_NAME}"
echo "Backup: ${BACKUP_FILE}"
echo ""
read -p "Are you sure you want to continue? (type 'YES' to confirm): " -r
if [[ ! $REPLY == "YES" ]]; then
    echo "Restore cancelled."
    exit 0
fi

log "Starting database restore from: ${BACKUP_FILE}"

# Create a safety backup before restore
SAFETY_BACKUP="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
log "📦 Creating safety backup: ${SAFETY_BACKUP}"
pg_dump -U ${DB_USER} -h localhost ${DB_NAME} | gzip > "${SAFETY_BACKUP}"

if [ $? -eq 0 ]; then
    log "✅ Safety backup created"
else
    log "${RED}❌ Failed to create safety backup${NC}"
    exit 1
fi

# Terminate existing connections
log "🔌 Terminating existing database connections..."
psql -U ${DB_USER} -h localhost -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" > /dev/null 2>&1

# Drop and recreate database
log "🗑️  Dropping database..."
dropdb -U ${DB_USER} -h localhost ${DB_NAME}

log "📦 Creating fresh database..."
createdb -U ${DB_USER} -h localhost ${DB_NAME}

# Restore from backup
log "🔄 Restoring from backup..."
gunzip < "${BACKUP_FILE}" | psql -U ${DB_USER} -h localhost ${DB_NAME} > /dev/null 2>&1

if [ $? -eq 0 ]; then
    log "${GREEN}✅ Database restored successfully!${NC}"
    
    # Verify restore
    RECORD_COUNT=$(psql -U ${DB_USER} -h localhost ${DB_NAME} -t -c "SELECT COUNT(*) FROM bitrix.contacts;" 2>/dev/null | xargs)
    log "📊 Verification: ${RECORD_COUNT} records in contacts table"
    
    log "🎉 Restore completed successfully"
else
    log "${RED}❌ Restore failed!${NC}"
    log "💾 Safety backup available at: ${SAFETY_BACKUP}"
    exit 1
fi
