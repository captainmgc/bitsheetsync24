#!/bin/bash

# BitSheet24 - Durdurma Scripti
# Backend ve Frontend'i güvenli bir şekilde durdurur

set -e

# Renkli output için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🛑 BitSheet24 Durduruluyor...                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Script'in çalıştığı dizini bul
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# PID dosyalarının konumu
PID_DIR="${SCRIPT_DIR}/.pids"
BACKEND_PID_FILE="${PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"

STOPPED=0

# Backend'i durdur
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${YELLOW}🔧 Backend durduruluyor (PID: $BACKEND_PID)...${NC}"
        kill "$BACKEND_PID" 2>/dev/null || true
        sleep 2
        
        # Hala çalışıyorsa zorla durdur
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo -e "${YELLOW}   Zorla durduruluyor...${NC}"
            kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ Backend durduruldu${NC}"
        STOPPED=1
    else
        echo -e "${YELLOW}⚠️  Backend zaten çalışmıyor${NC}"
    fi
    rm -f "$BACKEND_PID_FILE"
else
    echo -e "${YELLOW}⚠️  Backend PID dosyası bulunamadı${NC}"
fi

echo ""

# Frontend'i durdur
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${YELLOW}🎨 Frontend durduruluyor (PID: $FRONTEND_PID)...${NC}"
        kill "$FRONTEND_PID" 2>/dev/null || true
        sleep 2
        
        # Hala çalışıyorsa zorla durdur
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            echo -e "${YELLOW}   Zorla durduruluyor...${NC}"
            kill -9 "$FRONTEND_PID" 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ Frontend durduruldu${NC}"
        STOPPED=1
    else
        echo -e "${YELLOW}⚠️  Frontend zaten çalışmıyor${NC}"
    fi
    rm -f "$FRONTEND_PID_FILE"
else
    echo -e "${YELLOW}⚠️  Frontend PID dosyası bulunamadı${NC}"
fi

echo ""

# Ek temizlik - port'larda kalmış olabilecek process'leri kontrol et
echo -e "${BLUE}🧹 Port kontrolü yapılıyor...${NC}"

# Port 8001 (Backend)
BACKEND_PORT_PID=$(lsof -ti:8001 2>/dev/null || true)
if [ ! -z "$BACKEND_PORT_PID" ]; then
    echo -e "${YELLOW}   Port 8001'de process bulundu (PID: $BACKEND_PORT_PID), durduruluyor...${NC}"
    kill -9 "$BACKEND_PORT_PID" 2>/dev/null || true
    STOPPED=1
fi

# Port 1600 (Frontend)
FRONTEND_PORT_PID=$(lsof -ti:1600 2>/dev/null || true)
if [ ! -z "$FRONTEND_PORT_PID" ]; then
    echo -e "${YELLOW}   Port 1600'de process bulundu (PID: $FRONTEND_PORT_PID), durduruluyor...${NC}"
    kill -9 "$FRONTEND_PORT_PID" 2>/dev/null || true
    STOPPED=1
fi

echo ""

if [ $STOPPED -eq 1 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ BitSheet24 Başarıyla Durduruldu!               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║          ⚠️  BitSheet24 Zaten Çalışmıyordu                 ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
fi

echo ""
echo -e "${BLUE}💡 Tekrar başlatmak için: ./start.sh${NC}"
echo ""
