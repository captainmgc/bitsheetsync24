#!/bin/bash

# BitSheet24 - Yeniden Başlatma Scripti
# Backend ve Frontend'i durdurur ve tekrar başlatır

# Renkli output için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          🔄 BitSheet24 Yeniden Başlatılıyor...              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Script'in çalıştığı dizini bul
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Önce durdur
echo -e "${YELLOW}🛑 Mevcut servisler durduruluyor...${NC}"
./stop.sh

echo ""
echo -e "${YELLOW}⏳ 3 saniye bekleniyor...${NC}"
sleep 3
echo ""

# Sonra başlat
echo -e "${GREEN}🚀 Servisler yeniden başlatılıyor...${NC}"
echo ""
./start.sh
