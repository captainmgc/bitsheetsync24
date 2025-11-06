#!/bin/bash

# BitSheet24 - Başlatma Scripti
# Hem Backend hem de Frontend'i aynı anda başlatır

set -e

# Renkli output için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🚀 BitSheet24 Başlatılıyor...                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Script'in çalıştığı dizini bul
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# PID dosyalarının konumu
PID_DIR="${SCRIPT_DIR}/.pids"
mkdir -p "$PID_DIR"
BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"

# Log dosyalarının konumu
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

# Cleanup fonksiyonu
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Kapatılıyor...${NC}"
    
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo -e "${YELLOW}   Backend durduruluyor (PID: $BACKEND_PID)${NC}"
            kill "$BACKEND_PID" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            echo -e "${YELLOW}   Frontend durduruluyor (PID: $FRONTEND_PID)${NC}"
            kill "$FRONTEND_PID" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    echo -e "${GREEN}✅ Temizlik tamamlandı${NC}"
    exit 0
}

# CTRL+C yakalandığında cleanup çalıştır
trap cleanup SIGINT SIGTERM

# PostgreSQL kontrolü
echo -e "${BLUE}📊 PostgreSQL kontrol ediliyor...${NC}"
if ! psql -h localhost -U bitsheet -d bitsheet_db -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL'e bağlanılamadı!${NC}"
    echo -e "${YELLOW}   Lütfen PostgreSQL'in çalıştığından emin olun.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL bağlantısı başarılı${NC}"
echo ""

# Backend başlatma
echo -e "${BLUE}🔧 Backend başlatılıyor...${NC}"
cd "${SCRIPT_DIR}/backend"

# Virtual environment aktifleştir
if [ ! -d "../venv" ]; then
    echo -e "${RED}❌ Virtual environment bulunamadı!${NC}"
    echo -e "${YELLOW}   Lütfen önce: python -m venv venv${NC}"
    exit 1
fi

source ../venv/bin/activate

# Gerekli paketler yüklü mü kontrol et (sadece kritik paketler)
if ! python -c "import fastapi, uvicorn, sqlalchemy, asyncpg" 2>/dev/null; then
    echo -e "${YELLOW}⚙️  Kritik paketler eksik, yükleniyor...${NC}"
    pip install -q fastapi uvicorn sqlalchemy asyncpg
fi

# Backend'i başlat
echo -e "${GREEN}   Backend başlatılıyor: http://localhost:8001${NC}"
nohup uvicorn main:app --host 0.0.0.0 --port 8001 --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$BACKEND_PID_FILE"

# Backend'in başlamasını bekle
sleep 3
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Backend başlatılamadı!${NC}"
    echo -e "${YELLOW}   Log: $BACKEND_LOG${NC}"
    tail -20 "$BACKEND_LOG"
    exit 1
fi

echo -e "${GREEN}✅ Backend başladı (PID: $BACKEND_PID)${NC}"
echo ""

# Frontend başlatma
echo -e "${BLUE}🎨 Frontend başlatılıyor...${NC}"
cd "${SCRIPT_DIR}/frontend"

# Node modules yüklü mü kontrol et
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚙️  Node paketleri yükleniyor...${NC}"
    npm install
fi

# Frontend'i başlat
echo -e "${GREEN}   Frontend başlatılıyor: http://localhost:3000${NC}"
nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$FRONTEND_PID_FILE"

# Frontend'in başlamasını bekle
sleep 5
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Frontend başlatılamadı!${NC}"
    echo -e "${YELLOW}   Log: $FRONTEND_LOG${NC}"
    tail -20 "$FRONTEND_LOG"
    exit 1
fi

echo -e "${GREEN}✅ Frontend başladı (PID: $FRONTEND_PID)${NC}"
echo ""

# Başarı mesajı
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✅ BitSheet24 Başarıyla Başlatıldı!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🌐 Erişim Bilgileri:${NC}"
echo -e "   ${GREEN}Frontend:${NC}  http://localhost:3000"
echo -e "   ${GREEN}Backend:${NC}   http://localhost:8001"
echo -e "   ${GREEN}API Docs:${NC}  http://localhost:8001/docs"
echo ""
echo -e "${BLUE}📋 Log Dosyaları:${NC}"
echo -e "   ${YELLOW}Backend:${NC}   tail -f $BACKEND_LOG"
echo -e "   ${YELLOW}Frontend:${NC}  tail -f $FRONTEND_LOG"
echo ""
echo -e "${BLUE}🔧 Process ID'ler:${NC}"
echo -e "   ${YELLOW}Backend:${NC}   $BACKEND_PID"
echo -e "   ${YELLOW}Frontend:${NC}  $FRONTEND_PID"
echo ""
echo -e "${YELLOW}⚠️  Durdurmak için: CTRL+C veya ./stop.sh${NC}"
echo ""

# Log takibi (opsiyonel)
echo -e "${BLUE}📊 Log izleniyor... (CTRL+C ile çık)${NC}"
echo ""

# Her iki log'u da takip et
tail -f "$BACKEND_LOG" "$FRONTEND_LOG" &
TAIL_PID=$!

# Script sonsuza kadar çalışsın (CTRL+C ile durur)
wait $TAIL_PID
