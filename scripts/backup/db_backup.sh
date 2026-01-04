#!/bin/bash

# ===========================================
# BitSheet24 - Veritabanı Yedekleme Scripti
# Lokal PostgreSQL veritabanını yedekler
# ===========================================

set -e

# Renkli output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script dizini
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# .env dosyasından veritabanı bilgilerini yükle
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | grep -E '^DB_' | xargs)
fi

# Varsayılan değerler
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-bitsheet_db}
DB_USER=${DB_USER:-bitsheet}
DB_PASSWORD=${DB_PASSWORD:-bitsheet123}

# Yedekleme dizini
BACKUP_DIR="${PROJECT_DIR}/backups"
mkdir -p "$BACKUP_DIR"

# Dosya adı (tarih damgalı)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/bitsheet_backup_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         📦 BitSheet24 Veritabanı Yedekleme                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}📊 Veritabanı Bilgileri:${NC}"
echo -e "   Host: ${GREEN}${DB_HOST}${NC}"
echo -e "   Port: ${GREEN}${DB_PORT}${NC}"
echo -e "   Database: ${GREEN}${DB_NAME}${NC}"
echo -e "   User: ${GREEN}${DB_USER}${NC}"
echo ""

# PostgreSQL bağlantı testi
echo -e "${BLUE}🔗 Bağlantı test ediliyor...${NC}"
export PGPASSWORD="$DB_PASSWORD"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Veritabanına bağlanılamadı!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Bağlantı başarılı${NC}"
echo ""

# Veritabanı boyutunu göster
DB_SIZE=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));")
echo -e "${BLUE}📏 Veritabanı Boyutu: ${GREEN}${DB_SIZE}${NC}"
echo ""

# Tablo sayılarını göster (gerçek COUNT ile)
echo -e "${BLUE}📋 Tablo İstatistikleri:${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 'bitrix.activities' as tablo, COUNT(*) as kayit_sayisi FROM bitrix.activities
UNION ALL SELECT 'bitrix.tasks', COUNT(*) FROM bitrix.tasks
UNION ALL SELECT 'bitrix.task_comments', COUNT(*) FROM bitrix.task_comments
UNION ALL SELECT 'bitrix.contacts', COUNT(*) FROM bitrix.contacts
UNION ALL SELECT 'bitrix.deals', COUNT(*) FROM bitrix.deals
UNION ALL SELECT 'bitrix.leads', COUNT(*) FROM bitrix.leads
UNION ALL SELECT 'bitrix.companies', COUNT(*) FROM bitrix.companies
UNION ALL SELECT 'bitrix.users', COUNT(*) FROM bitrix.users
ORDER BY kayit_sayisi DESC;
"
echo ""

# Yedekleme başlat
echo -e "${BLUE}💾 Yedekleme başlatılıyor...${NC}"
echo -e "   Hedef: ${YELLOW}${COMPRESSED_FILE}${NC}"
echo ""

# pg_dump ile yedekle
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    --verbose \
    2>&1 | tee "${BACKUP_FILE}.log" | grep -E "^pg_dump:" || true

# SQL dosyasını oluştur
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    > "$BACKUP_FILE"

# Sıkıştır
echo -e "${BLUE}🗜️  Sıkıştırılıyor...${NC}"
gzip -f "$BACKUP_FILE"

# MD5 checksum oluştur
md5sum "$COMPRESSED_FILE" > "${COMPRESSED_FILE}.md5"

# Sonuç
FINAL_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ Yedekleme Tamamlandı!                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   📁 Dosya: ${BLUE}${COMPRESSED_FILE}${NC}"
echo -e "   📏 Boyut: ${GREEN}${FINAL_SIZE}${NC}"
echo -e "   🔒 MD5:   ${YELLOW}$(cat ${COMPRESSED_FILE}.md5 | cut -d' ' -f1)${NC}"
echo ""

# Eski yedekleri temizle (30 günden eski)
echo -e "${BLUE}🧹 Eski yedekler temizleniyor (30+ gün)...${NC}"
find "$BACKUP_DIR" -name "bitsheet_backup_*.sql.gz" -mtime +30 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "bitsheet_backup_*.sql.gz.md5" -mtime +30 -delete 2>/dev/null || true

# Mevcut yedekleri listele
echo ""
echo -e "${BLUE}📋 Mevcut Yedekler:${NC}"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -10 || echo "   Yedek bulunamadı"
echo ""

# Çıktı: dosya yolu (script'ler arası kullanım için)
echo "$COMPRESSED_FILE"
