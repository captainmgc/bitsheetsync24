#!/bin/bash
# Quick frontend rebuild script

cd /var/www/bitsheetsync24

echo "🚀 Starting quick frontend rebuild..."
start_time=$(date +%s)

# Only rebuild frontend, skip backend entirely
docker compose build --no-cache frontend 2>&1 | grep -v "backend"

# Restart only the frontend container
docker compose up -d --no-deps frontend

end_time=$(date +%s)
echo "✅ Frontend rebuilt in $((end_time - start_time)) seconds"
