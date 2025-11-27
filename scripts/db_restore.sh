#!/bin/bash

# ===========================================
# BitSheet24 - Veritabanı Restore Scripti
# Yedek dosyasından veritabanını geri yükler
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
BACKUP_DIR="${PROJECT_DIR}/backups"

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

# Kullanım bilgisi
usage() {
    echo "Kullanım: $0 [OPTIONS] [BACKUP_FILE]"
    echo ""
    echo "Yedek dosyasından veritabanını geri yükler."
    echo ""
    echo "OPTIONS:"
    echo "  -l, --list          Mevcut yedekleri listele"
    echo "  -f, --force         Onay sormadan restore et"
    echo "  --latest            En son yedeği kullan"
    echo "  --help              Bu yardım mesajını göster"
    echo ""
    echo "Örnekler:"
    echo "  $0 --list                      # Yedekleri listele"
    echo "  $0 --latest                    # En son yedeği restore et"
    echo "  $0 backup_20241127.sql.gz      # Belirli bir yedeği restore et"
    echo ""
    exit 1
}

# Yedekleri listele
list_backups() {
    echo -e "${BLUE}📋 Mevcut Yedekler:${NC}"
    echo ""
    if ls "$BACKUP_DIR"/*.sql.gz 1> /dev/null 2>&1; then
        ls -lh "$BACKUP_DIR"/*.sql.gz | awk '{print "   " $9 " (" $5 ")"}'
    else
        echo -e "   ${YELLOW}Yedek bulunamadı${NC}"
    fi
    echo ""
    exit 0
}

# Parametreleri parse et
FORCE=false
USE_LATEST=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--list)
            list_backups
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        --latest)
            USE_LATEST=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🔄 BitSheet24 Veritabanı Restore                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# En son yedeği bul
if [ "$USE_LATEST" = true ] || [ -z "$BACKUP_FILE" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${RED}❌ Yedek dosyası bulunamadı!${NC}"
        echo -e "${YELLOW}   Yedek oluşturun: ./scripts/db_backup.sh${NC}"
        exit 1
    fi
    echo -e "${BLUE}📦 En son yedek kullanılıyor${NC}"
else
    # Tam yol değilse backup dizininde ara
    if [ ! -f "$BACKUP_FILE" ]; then
        BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
    fi
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}❌ Yedek dosyası bulunamadı: $BACKUP_FILE${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}📋 Restore Bilgileri:${NC}"
echo -e "   Yedek:    ${GREEN}$(basename $BACKUP_FILE)${NC}"
echo -e "   Boyut:    ${GREEN}$(du -h "$BACKUP_FILE" | cut -f1)${NC}"
echo -e "   Hedef DB: ${GREEN}${DB_NAME}@${DB_HOST}:${DB_PORT}${NC}"
echo ""

# Onay iste
if [ "$FORCE" = false ]; then
    echo -e "${RED}⚠️  DİKKAT: Bu işlem mevcut veritabanını SİLECEK ve yedeği yükleyecek!${NC}"
    echo ""
    read -p "Devam etmek istiyor musunuz? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}İptal edildi.${NC}"
        exit 0
    fi
fi

echo ""

# PostgreSQL bağlantı testi
echo -e "${BLUE}🔗 Veritabanı bağlantısı test ediliyor...${NC}"
export PGPASSWORD="$DB_PASSWORD"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Veritabanına bağlanılamadı!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Bağlantı başarılı${NC}"
echo ""

# Restore işlemi
echo -e "${BLUE}🔄 Restore başlatılıyor...${NC}"
echo -e "   Bu işlem birkaç dakika sürebilir..."
echo ""

# Sıkıştırılmış dosyayı aç ve restore et
gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=0 2>&1 | grep -E "^(ERROR|NOTICE)" || true

echo ""
echo -e "${GREEN}✅ Restore tamamlandı!${NC}"
echo ""

# Tablo sayılarını göster
echo -e "${BLUE}📊 Restore Sonrası Tablo İstatistikleri:${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    schemaname || '.' || tablename as tablo,
    n_live_tup as kayit_sayisi
FROM pg_stat_user_tables 
WHERE n_live_tup > 0
ORDER BY n_live_tup DESC
LIMIT 10;
"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ Restore İşlemi Tamamlandı!                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
