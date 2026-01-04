#!/bin/bash
# Test backup integrity without actually restoring

BACKUP_DIR="/home/captain/bitsheet24/backups"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 BitSheet24 Backup Integrity Check${NC}"
echo "====================================="
echo ""

# Find latest backup
LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/bitsheet_backup_*.sql.gz 2>/dev/null | head -1)

if [ -z "${LATEST_BACKUP}" ]; then
    echo -e "${RED}❌ No backups found${NC}"
    exit 1
fi

echo "Testing backup: $(basename ${LATEST_BACKUP})"
echo ""

# Test 1: File exists and readable
echo -n "1. File accessibility... "
if [ -r "${LATEST_BACKUP}" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Cannot read file${NC}"
    exit 1
fi

# Test 2: File size
echo -n "2. File size check... "
SIZE=$(stat -f%z "${LATEST_BACKUP}" 2>/dev/null || stat -c%s "${LATEST_BACKUP}" 2>/dev/null)
if [ ${SIZE} -gt 1000 ]; then
    echo -e "${GREEN}✓${NC} ($(numfmt --to=iec-i --suffix=B ${SIZE} 2>/dev/null || echo "${SIZE} bytes"))"
else
    echo -e "${RED}✗ File too small (${SIZE} bytes)${NC}"
    exit 1
fi

# Test 3: MD5 checksum
echo -n "3. Checksum verification... "
if [ -f "${LATEST_BACKUP}.md5" ]; then
    if md5sum -c "${LATEST_BACKUP}.md5" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Checksum mismatch${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ No checksum file${NC}"
fi

# Test 4: GZIP integrity
echo -n "4. Compression integrity... "
if gunzip -t "${LATEST_BACKUP}" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Corrupted gzip file${NC}"
    exit 1
fi

# Test 5: SQL content check
echo -n "5. SQL content validation... "
TEMP_SQL=$(mktemp)
gunzip < "${LATEST_BACKUP}" > "${TEMP_SQL}" 2>/dev/null

if grep -q "PostgreSQL database dump" "${TEMP_SQL}"; then
    echo -e "${GREEN}✓${NC}"
    
    # Check for key tables
    echo ""
    echo "   Tables found in backup:"
    for table in contacts companies deals tasks leads activities; do
        if grep -q "CREATE TABLE.*${table}" "${TEMP_SQL}"; then
            echo -e "     ${GREEN}●${NC} bitrix.${table}"
        else
            echo -e "     ${YELLOW}○${NC} bitrix.${table} (not found)"
        fi
    done
else
    echo -e "${RED}✗ Invalid SQL format${NC}"
    rm "${TEMP_SQL}"
    exit 1
fi

rm "${TEMP_SQL}"

# Test 6: Estimate record count
echo ""
echo -n "6. Record count estimation... "
INSERTS=$(gunzip < "${LATEST_BACKUP}" | grep -c "^INSERT INTO" || echo "0")
echo -e "${GREEN}✓${NC} (~${INSERTS} INSERT statements)"

echo ""
echo -e "${GREEN}═══════════════════════════════════${NC}"
echo -e "${GREEN}✅ Backup integrity check PASSED${NC}"
echo -e "${GREEN}═══════════════════════════════════${NC}"
echo ""
echo "Backup details:"
echo "  File: ${LATEST_BACKUP}"
echo "  Size: $(du -h ${LATEST_BACKUP} | cut -f1)"
echo "  Date: $(stat -f%Sm "${LATEST_BACKUP}" 2>/dev/null || stat -c%y "${LATEST_BACKUP}" 2>/dev/null | cut -d' ' -f1,2)"
echo ""
echo "This backup can be safely used for restore."
