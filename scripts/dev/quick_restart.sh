#!/bin/bash
# One-liner to restart both services
pkill -f "uvicorn app.main:app" || true; pkill -f "next dev" || true; sleep 2; cd /home/captain/bitsheet24/backend && source venv/bin/activate && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &  cd /home/captain/bitsheet24/frontend && npm run dev > /tmp/frontend.log 2>&1 &
