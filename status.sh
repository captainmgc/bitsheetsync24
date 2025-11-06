#!/bin/bash

# BitSheet24 - Durum Kontrolü
# Backend ve Frontend'in çalışma durumunu gösterir

# Renkli output için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              📊 BitSheet24 Durum Kontrolü                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Script'in çalıştığı dizini bul
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# PID dosyalarının konumu
PID_DIR="${SCRIPT_DIR}/.pids"
BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"

RUNNING_COUNT=0

# Backend kontrolü
echo -e "${BLUE}🔧 Backend (Port 8001):${NC}"
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${GREEN}   ✅ Çalışıyor (PID: $BACKEND_PID)${NC}"
        
        # HTTP kontrolü
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo -e "${GREEN}   ✅ HTTP yanıt veriyor${NC}"
        else
            echo -e "${YELLOW}   ⚠️  HTTP yanıt vermiyor${NC}"
        fi
        
        # Uptime göster
        UPTIME=$(ps -p $BACKEND_PID -o etime= | tr -d ' ')
        echo -e "${BLUE}   ⏱️  Uptime: $UPTIME${NC}"
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
    else
        echo -e "${RED}   ❌ Çalışmıyor (PID dosyası eski)${NC}"
    fi
else
    # Port kontrolü
    BACKEND_PORT_PID=$(lsof -ti:8001 2>/dev/null || true)
    if [ ! -z "$BACKEND_PORT_PID" ]; then
        echo -e "${YELLOW}   ⚠️  Port 8001'de bir process var (PID: $BACKEND_PORT_PID)${NC}"
        echo -e "${YELLOW}   ⚠️  Ancak start.sh tarafından başlatılmamış${NC}"
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
    else
        echo -e "${RED}   ❌ Çalışmıyor${NC}"
    fi
fi

echo ""

# Frontend kontrolü
echo -e "${BLUE}🎨 Frontend (Port 3000):${NC}"
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${GREEN}   ✅ Çalışıyor (PID: $FRONTEND_PID)${NC}"
        
        # HTTP kontrolü
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}   ✅ HTTP yanıt veriyor${NC}"
        else
            echo -e "${YELLOW}   ⚠️  HTTP yanıt vermiyor (başlatılıyor olabilir)${NC}"
        fi
        
        # Uptime göster
        UPTIME=$(ps -p $FRONTEND_PID -o etime= | tr -d ' ')
        echo -e "${BLUE}   ⏱️  Uptime: $UPTIME${NC}"
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
    else
        echo -e "${RED}   ❌ Çalışmıyor (PID dosyası eski)${NC}"
    fi
else
    # Port kontrolü
    FRONTEND_PORT_PID=$(lsof -ti:3000 2>/dev/null || true)
    if [ ! -z "$FRONTEND_PORT_PID" ]; then
        echo -e "${YELLOW}   ⚠️  Port 3000'de bir process var (PID: $FRONTEND_PORT_PID)${NC}"
        echo -e "${YELLOW}   ⚠️  Ancak start.sh tarafından başlatılmamış${NC}"
        RUNNING_COUNT=$((RUNNING_COUNT + 1))
    else
        echo -e "${RED}   ❌ Çalışmıyor${NC}"
    fi
fi

echo ""

# PostgreSQL kontrolü
echo -e "${BLUE}📊 PostgreSQL:${NC}"
if psql -h localhost -U bitsheet -d bitsheet_db -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Bağlantı başarılı${NC}"
    
    # Tablo kayıt sayıları
    RECORD_COUNTS=$(psql -h localhost -U bitsheet -d bitsheet_db -t -c "
        SELECT 
            'Contacts: ' || COUNT(*) FROM bitrix.contacts
        UNION ALL
        SELECT 'Companies: ' || COUNT(*) FROM bitrix.companies
        UNION ALL
        SELECT 'Deals: ' || COUNT(*) FROM bitrix.deals
        UNION ALL
        SELECT 'Tasks: ' || COUNT(*) FROM bitrix.tasks
    " 2>/dev/null | tr '\n' ', ')
    
    echo -e "${BLUE}   📈 Kayıtlar: $RECORD_COUNTS${NC}"
else
    echo -e "${RED}   ❌ Bağlantı başarısız${NC}"
fi

echo ""

# Özet
if [ $RUNNING_COUNT -eq 2 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ Tüm Servisler Çalışıyor!                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
elif [ $RUNNING_COUNT -eq 1 ]; then
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║          ⚠️  Bazı Servisler Çalışmıyor                     ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          ❌ Hiçbir Servis Çalışmıyor                       ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
fi

echo ""
echo -e "${BLUE}🌐 Erişim Linkleri:${NC}"
echo -e "   Frontend:  ${GREEN}http://localhost:3000${NC}"
echo -e "   Backend:   ${GREEN}http://localhost:8001${NC}"
echo -e "   API Docs:  ${GREEN}http://localhost:8001/docs${NC}"
echo ""
echo -e "${BLUE}🔧 Komutlar:${NC}"
echo -e "   Başlat:    ${YELLOW}./start.sh${NC}"
echo -e "   Durdur:    ${YELLOW}./stop.sh${NC}"
echo -e "   Restart:   ${YELLOW}./restart.sh${NC}"
echo ""
