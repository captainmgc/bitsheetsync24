#!/bin/bash

# BitSheet24 - Sürekli Monitoring
# Kullanım: ./monitor.sh veya ./monitor.sh --once

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Python virtual environment aktifleştir
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if [ "$1" == "--once" ] || [ "$1" == "-1" ]; then
    # Tek seferlik göster
    python monitor.py
else
    # Sürekli izle (5 saniyede bir)
    python monitor.py --watch --interval 5
fi
