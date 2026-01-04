#!/bin/bash
# PostgreSQL Backup Script for BitSheet24
# Automated database backup with rotation

# Configuration
DB_NAME="bitsheet_db"
DB_USER="bitsheet"
BACKUP_DIR="/home/captain/bitsheet24/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/bitsheet_backup_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Retention policy
KEEP_DAYS=7        # Keep daily backups for 7 days
KEEP_WEEKS=4       # Keep weekly backups for 4 weeks
KEEP_MONTHS=6      # Keep monthly backups for 6 months

# Create backup directory if not exists
mkdir -p "${BACKUP_DIR}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "Starting database backup..."

# Perform backup
pg_dump -U ${DB_USER} -h localhost ${DB_NAME} | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log "✅ Backup completed successfully: ${BACKUP_FILE} (${BACKUP_SIZE})"
    
    # Create checksums for integrity verification
    md5sum "${BACKUP_FILE}" > "${BACKUP_FILE}.md5"
    log "📝 Checksum created: ${BACKUP_FILE}.md5"
else
    log "❌ Backup failed!"
    exit 1
fi

# Cleanup old backups
log "🧹 Cleaning up old backups..."

# Keep daily backups for KEEP_DAYS
find "${BACKUP_DIR}" -name "bitsheet_backup_*.sql.gz" -type f -mtime +${KEEP_DAYS} -delete
log "   Removed backups older than ${KEEP_DAYS} days"

# Keep weekly backups (every Sunday) for KEEP_WEEKS
WEEKS_AGO=$((KEEP_WEEKS * 7))
find "${BACKUP_DIR}" -name "bitsheet_backup_*.sql.gz" -type f -mtime +${WEEKS_AGO} ! -exec sh -c 'date -r "$1" +%u | grep -q "^7$"' _ {} \; -delete 2>/dev/null
log "   Kept weekly backups for ${KEEP_WEEKS} weeks"

# Keep monthly backups (1st of month) for KEEP_MONTHS
MONTHS_AGO=$((KEEP_MONTHS * 30))
find "${BACKUP_DIR}" -name "bitsheet_backup_*.sql.gz" -type f -mtime +${MONTHS_AGO} ! -exec sh -c 'date -r "$1" +%d | grep -q "^01$"' _ {} \; -delete 2>/dev/null
log "   Kept monthly backups for ${KEEP_MONTHS} months"

# Display backup statistics
TOTAL_BACKUPS=$(ls -1 "${BACKUP_DIR}"/bitsheet_backup_*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
log "📊 Total backups: ${TOTAL_BACKUPS}, Total size: ${TOTAL_SIZE}"

# List recent backups
log "📋 Recent backups:"
ls -lht "${BACKUP_DIR}"/bitsheet_backup_*.sql.gz 2>/dev/null | head -5 | while read line; do
    log "   ${line}"
done

log "Backup process completed."
