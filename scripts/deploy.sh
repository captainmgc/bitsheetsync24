#!/bin/bash

# ===========================================
# BitSheet24 - Production Deployment Script
# Domain: etablo.japonkonutlari.com
# ===========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🚀 BitSheet24 Production Deployment                 ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}❌ .env.production file not found!${NC}"
    echo -e "${YELLOW}   Please copy .env.production.template to .env.production${NC}"
    echo -e "${YELLOW}   and fill in the required values.${NC}"
    exit 1
fi

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs)

echo -e "${BLUE}📋 Deployment Configuration:${NC}"
echo -e "   Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "   Frontend URL: ${GREEN}${FRONTEND_URL}${NC}"
echo -e "   API URL: ${GREEN}${NEXT_PUBLIC_API_URL}${NC}"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is ready${NC}"
echo ""

# Create required directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p nginx/ssl
mkdir -p nginx/certbot
mkdir -p logs

# Check SSL certificates
if [ ! -f "nginx/ssl/fullchain.pem" ] || [ ! -f "nginx/ssl/privkey.pem" ]; then
    echo -e "${YELLOW}⚠️  SSL certificates not found in nginx/ssl/${NC}"
    echo -e "${YELLOW}   You need to obtain SSL certificates for HTTPS.${NC}"
    echo -e "${YELLOW}   Options:${NC}"
    echo -e "${YELLOW}   1. Use Let's Encrypt (certbot)${NC}"
    echo -e "${YELLOW}   2. Use your existing certificates${NC}"
    echo ""
    read -p "Continue without SSL? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build and deploy
echo ""
echo -e "${BLUE}🔨 Building Docker images...${NC}"
docker compose --env-file .env.production build

echo ""
echo -e "${BLUE}🚀 Starting services...${NC}"
docker compose --env-file .env.production up -d

echo ""
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Health check
echo ""
echo -e "${BLUE}🏥 Health Check:${NC}"

# Check backend
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "   Backend API: ${GREEN}✅ Healthy${NC}"
else
    echo -e "   Backend API: ${RED}❌ Not responding${NC}"
fi

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "   Frontend: ${GREEN}✅ Healthy${NC}"
else
    echo -e "   Frontend: ${RED}❌ Not responding${NC}"
fi

# Check database
if docker compose exec -T postgres pg_isready -U ${DB_USER} > /dev/null 2>&1; then
    echo -e "   Database: ${GREEN}✅ Healthy${NC}"
else
    echo -e "   Database: ${RED}❌ Not responding${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              🎉 Deployment Complete!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   🌐 Application: ${BLUE}${FRONTEND_URL}${NC}"
echo -e "   📚 API Docs: ${BLUE}${FRONTEND_URL}/docs${NC}"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "   View logs:     ${BLUE}docker compose logs -f${NC}"
echo -e "   Stop services: ${BLUE}docker compose down${NC}"
echo -e "   Restart:       ${BLUE}docker compose restart${NC}"
echo ""
