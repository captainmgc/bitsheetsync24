#!/bin/bash

# BitSheet24 Complete Restart Script
# Restarts both Backend (FastAPI) and Frontend (Next.js)

set -e

PROJECT_ROOT="/home/captain/bitsheet24"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "================================"
echo "🔄 BitSheet24 Full Restart"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Kill existing processes
echo -e "${YELLOW}⏹️  Stopping existing services...${NC}"
pkill -f "uvicorn app.main:app" || echo "  No backend process found"
pkill -f "next dev" || echo "  No frontend process found"
sleep 2

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Starting Backend (FastAPI)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$BACKEND_DIR"

# Activate venv and start backend
source venv/bin/activate
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo -e "  📍 http://localhost:8000"
echo -e "  📚 Docs: http://localhost:8000/docs"

# Wait for backend to be ready
echo "  Waiting for backend to start..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Backend ready!${NC}"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🎨 Starting Frontend (Next.js)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$FRONTEND_DIR"

# Start frontend
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "  📍 http://localhost:3000"

# Wait for frontend to be ready
echo "  Waiting for frontend to start..."
for i in {1..30}; do
  if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Frontend ready!${NC}"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All Services Started Successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📊 Service URLs:${NC}"
echo -e "  🌐 Frontend:     ${GREEN}http://localhost:3000${NC}"
echo -e "  ⚙️  Backend:      ${GREEN}http://localhost:8000${NC}"
echo -e "  📚 API Docs:     ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}📋 Logs:${NC}"
echo -e "  Backend:  tail -f /tmp/backend.log"
echo -e "  Frontend: tail -f /tmp/frontend.log"
echo ""
echo -e "${YELLOW}🛑 To stop services:${NC}"
echo -e "  pkill -f 'uvicorn app.main:app'  # Backend"
echo -e "  pkill -f 'next dev'              # Frontend"
echo ""
