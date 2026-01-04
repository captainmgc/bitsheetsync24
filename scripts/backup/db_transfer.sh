#!/bin/bash

# ===========================================
# BitSheet24 - Veritabanı Sunucuya Aktarım Scripti
# Lokal yedeği uzak sunucuya aktarır
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

# Varsayılan sunucu bilgileri (override edilebilir)
REMOTE_HOST=${REMOTE_HOST:-"etablo.japonkonutlari.com"}
REMOTE_USER=${REMOTE_USER:-"root"}
REMOTE_PORT=${REMOTE_PORT:-22}
REMOTE_PATH=${REMOTE_PATH:-"/opt/bitsheet24/backups"}

# Kullanım bilgisi
usage() {
    echo "Kullanım: $0 [OPTIONS] [BACKUP_FILE]"
    echo ""
    echo "Lokal veritabanı yedeğini uzak sunucuya aktarır."
    echo ""
    echo "OPTIONS:"
    echo "  -h, --host HOST     Uzak sunucu adresi (varsayılan: $REMOTE_HOST)"
    echo "  -u, --user USER     SSH kullanıcı adı (varsayılan: $REMOTE_USER)"
    echo "  -p, --port PORT     SSH portu (varsayılan: $REMOTE_PORT)"
    echo "  -d, --dest PATH     Hedef dizin (varsayılan: $REMOTE_PATH)"
    echo "  -r, --restore       Aktarımdan sonra restore et"
    echo "  -l, --latest        En son yedeği kullan"
    echo "  --help              Bu yardım mesajını göster"
    echo ""
    echo "Örnekler:"
    echo "  $0 --latest                    # En son yedeği aktar"
    echo "  $0 --latest --restore          # En son yedeği aktar ve restore et"
    echo "  $0 backup_20241127.sql.gz      # Belirli bir yedeği aktar"
    echo ""
    exit 1
}

# Parametreleri parse et
RESTORE=false
USE_LATEST=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        -u|--user)
            REMOTE_USER="$2"
            shift 2
            ;;
        -p|--port)
            REMOTE_PORT="$2"
            shift 2
            ;;
        -d|--dest)
            REMOTE_PATH="$2"
            shift 2
            ;;
        -r|--restore)
            RESTORE=true
            shift
            ;;
        -l|--latest)
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
echo -e "${BLUE}║       🚀 BitSheet24 Veritabanı Sunucuya Aktarım            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# En son yedeği bul
if [ "$USE_LATEST" = true ] || [ -z "$BACKUP_FILE" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${RED}❌ Yedek dosyası bulunamadı!${NC}"
        echo -e "${YELLOW}   Önce yedek oluşturun: ./scripts/db_backup.sh${NC}"
        exit 1
    fi
    echo -e "${BLUE}📦 En son yedek kullanılıyor: ${GREEN}$(basename $BACKUP_FILE)${NC}"
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

# Dosya bilgilerini göster
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo -e "${BLUE}📋 Aktarım Bilgileri:${NC}"
echo -e "   Kaynak: ${GREEN}${BACKUP_FILE}${NC}"
echo -e "   Boyut:  ${GREEN}${FILE_SIZE}${NC}"
echo -e "   Hedef:  ${GREEN}${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}${NC}"
echo -e "   Port:   ${GREEN}${REMOTE_PORT}${NC}"
echo ""

# SSH bağlantı testi
echo -e "${BLUE}🔗 SSH bağlantısı test ediliyor...${NC}"
if ! ssh -p "$REMOTE_PORT" -o ConnectTimeout=10 -o BatchMode=yes "$REMOTE_USER@$REMOTE_HOST" "echo 'OK'" > /dev/null 2>&1; then
    echo -e "${RED}❌ SSH bağlantısı başarısız!${NC}"
    echo -e "${YELLOW}   Lütfen SSH anahtarınızın kurulu olduğundan emin olun.${NC}"
    echo -e "${YELLOW}   ssh-copy-id -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST${NC}"
    exit 1
fi
echo -e "${GREEN}✅ SSH bağlantısı başarılı${NC}"
echo ""

# Hedef dizini oluştur
echo -e "${BLUE}📁 Hedef dizin oluşturuluyor...${NC}"
ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH"

# Dosyayı aktar
echo -e "${BLUE}📤 Dosya aktarılıyor...${NC}"
REMOTE_FILE="${REMOTE_PATH}/$(basename $BACKUP_FILE)"

rsync -avz --progress \
    -e "ssh -p $REMOTE_PORT" \
    "$BACKUP_FILE" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_FILE"

# MD5 dosyasını da aktar
if [ -f "${BACKUP_FILE}.md5" ]; then
    rsync -avz -e "ssh -p $REMOTE_PORT" \
        "${BACKUP_FILE}.md5" \
        "$REMOTE_USER@$REMOTE_HOST:${REMOTE_FILE}.md5"
fi

echo ""
echo -e "${GREEN}✅ Aktarım tamamlandı!${NC}"
echo ""

# Restore seçeneği
if [ "$RESTORE" = true ]; then
    echo -e "${BLUE}🔄 Veritabanı restore ediliyor...${NC}"
    
    # Uzak sunucuda restore komutu çalıştır
    ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" << EOF
        cd /opt/bitsheet24
        
        # .env dosyasından değişkenleri yükle
        if [ -f ".env" ]; then
            export \$(cat .env | grep -v '^#' | grep -E '^DB_' | xargs)
        fi
        
        DB_HOST=\${DB_HOST:-postgres}
        DB_PORT=\${DB_PORT:-5432}
        DB_NAME=\${DB_NAME:-bitsheet_db}
        DB_USER=\${DB_USER:-bitsheet}
        DB_PASSWORD=\${DB_PASSWORD:-bitsheet123}
        
        export PGPASSWORD="\$DB_PASSWORD"
        
        echo "Veritabanı restore ediliyor..."
        gunzip -c "$REMOTE_FILE" | psql -h "\$DB_HOST" -p "\$DB_PORT" -U "\$DB_USER" -d "\$DB_NAME"
        
        echo "Restore tamamlandı!"
EOF
    
    echo -e "${GREEN}✅ Restore tamamlandı!${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ İşlem Başarıyla Tamamlandı!                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   Uzak dosya: ${BLUE}${REMOTE_FILE}${NC}"
echo ""

if [ "$RESTORE" = false ]; then
    echo -e "${YELLOW}💡 İpucu: Restore etmek için --restore parametresi ekleyin${NC}"
    echo -e "${YELLOW}   Örnek: $0 --latest --restore${NC}"
fi
echo ""
