# 🚀 Local Development Environment - Setup & Run Guide

## 📋 Prerequisites

### System Requirements
```
✅ macOS 10.15+, Linux (Ubuntu 20.04+), or Windows 10+
✅ Git installed
✅ 8GB RAM minimum
✅ 2GB free disk space
✅ Internet connection
```

### Required Software
- ✅ Node.js >= 18.0.0
- ✅ Python >= 3.11
- ✅ PostgreSQL >= 16
- ✅ npm >= 9.0.0
- ✅ pip >= 23.0

---

## 🔧 Complete Setup Guide

### Step 1: Install Prerequisites

#### macOS (Using Homebrew)
```bash
# Install Node.js
brew install node

# Install Python
brew install python@3.11

# Install PostgreSQL
brew install postgresql@16
brew services start postgresql@16

# Verify installations
node --version     # Should be v18.0.0+
python3 --version  # Should be 3.11+
psql --version     # Should be PostgreSQL 16+
```

#### Linux (Ubuntu 20.04+)
```bash
# Update package manager
sudo apt update

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql

# Verify installations
node --version
python3.11 --version
psql --version
```

#### Windows
```powershell
# Download and install from official websites:
# - Node.js: https://nodejs.org/
# - Python 3.11: https://www.python.org/downloads/
# - PostgreSQL 16: https://www.postgresql.org/download/windows/

# Or use Chocolatey:
choco install nodejs python postgresql
```

### Step 2: Clone and Navigate

```bash
# Clone repository
git clone <repository-url>
cd bitsheet24

# Verify structure
ls -la
# Should see: backend/, frontend/, development/, etc.
```

### Step 3: Setup Database

```bash
# Create database
createdb bitsheet

# Connect and verify
psql bitsheet

# In psql, run:
\dt  # Should be empty initially

# Exit psql
\q
```

### Step 4: Run Migrations

```bash
# Apply migrations
psql bitsheet < backend/migrations/008_add_sheet_sync_tables.sql

# Verify tables created
psql bitsheet -c "\dt"
```

**Expected Output**:
```
                     List of relations
 Schema |              Name               | Type  | Owner
────────┼────────────────────────────────┼───────┼───────
 public | field_mappings                 | table | user
 public | reverse_sync_logs              | table | user
 public | sheet_sync_config              | table | user
 public | user_sheets_tokens             | table | user
 public | webhook_events                 | table | user
```

### Step 5: Configure Backend

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://localhost:5432/bitsheet
GOOGLE_SHEETS_API_KEY=your-api-key-here
BITRIX24_WEBHOOK_URL=https://your-bitrix.bitrix24.com/rest/...
FRONTEND_URL=http://localhost:3000
EOF

# Verify installation
python -m pytest --version
```

### Step 6: Configure Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env.local file
cat > .env.local << 'EOF'
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=+XaOututOTO9qm962t74N9h2f8X1hfIDRYMcnxePgpM=
GOOGLE_CLIENT_ID=1062427543251-s8hef8m2hvu1r0cdssda60787vb03g2n.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
NEXT_PUBLIC_API_URL=http://localhost:8001
EOF

# Verify installation
npm --version
npx eslint --version
```

---

## 🎯 Starting Local Development Environment

### Terminal 1: Backend Server

```bash
cd /home/captain/bitsheet24/backend

# Activate virtual environment
source venv/bin/activate  # macOS/Linux

# Start development server
python -m uvicorn app.main:app --reload --port 8001
```

**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8001
```

### Terminal 2: Frontend Server

```bash
cd /home/captain/bitsheet24/frontend

# Start development server
npm run dev
```

**Expected Output**:
```
▲ Next.js 16.0.1
  - Local:        http://localhost:3000
  - Environments: .env.local

✓ Ready in 2.8s
```

### Terminal 3: Database Monitor (Optional)

```bash
# Connect to database
psql bitsheet

# View tables
\dt

# View connections
SELECT * FROM pg_stat_activity;

# Exit
\q
```

---

## 🌐 Access the Application

### Frontend
- **URL**: http://localhost:3000
- **Path**: `/sheet-sync`
- **Status**: Should load the configuration page

### Backend API
- **URL**: http://localhost:8001
- **Docs**: http://localhost:8001/docs (Interactive Swagger UI)
- **ReDoc**: http://localhost:8001/redoc

### Database
- **Connection**: `psql bitsheet`
- **GUI Option**: Use pgAdmin (brew install pgadmin4)

---

## 🧪 Testing the System

### Test 1: Backend Health Check

```bash
curl -X GET http://localhost:8001/docs
```

**Expected**: Opens Swagger UI

### Test 2: OAuth Start Endpoint

```bash
curl -X POST http://localhost:8001/api/v1/sheet-sync/oauth/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user-123"}'
```

**Expected**:
```json
{
  "oauth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

### Test 3: Frontend OAuth Page

1. Open http://localhost:3000
2. You should be redirected to login
3. Log in with your credentials
4. Navigate to `/sheet-sync`
5. Click "Connect with Google"
6. Authorize the application
7. Should redirect back to `/sheet-sync` with token

### Test 4: Create Configuration

```bash
# First get a valid token from OAuth flow above, then:
curl -X POST http://localhost:8001/api/v1/sheet-sync/config \
  -H "Content-Type: application/json" \
  -d '{
    "sheet_id": "1BxiMVs0XRA5nFMoon9dsLkW1an7cosuQ3DN5-J6Z8c",
    "sheet_name": "Test Sheet",
    "gid": "0",
    "entity_type": "contacts",
    "user_id": "test-user-123"
  }'
```

### Test 5: Verify Database

```bash
psql bitsheet

# Check if config was saved
SELECT * FROM sheet_sync_config;

# Check field mappings
SELECT * FROM field_mappings;

# Exit
\q
```

---

## 🔧 Common Development Tasks

### Add New API Endpoint

```bash
# 1. Edit backend/app/api/sheet_sync.py
# 2. Add new endpoint function

@router.get("/new-endpoint/{id}")
async def new_endpoint(id: int, user_id: str = Depends(get_current_user_id)):
    # Your logic here
    return {"result": "success"}

# 3. Server auto-reloads
# 4. Access at http://localhost:8001/api/v1/sheet-sync/new-endpoint/1
```

### Add New Frontend Component

```bash
# 1. Create component file
touch frontend/app/sheet-sync/components/NewComponent.tsx

# 2. Create basic component
cat > frontend/app/sheet-sync/components/NewComponent.tsx << 'EOF'
export default function NewComponent({ config }) {
  return <div>New Component</div>
}
EOF

# 3. Import in page.tsx
# 4. Add to component list
# 5. HMR auto-updates
```

### Run Backend Tests

```bash
cd backend

# Run all tests
python -m pytest

# Run specific test
python -m pytest tests/test_sheet_sync.py -v

# Run with coverage
python -m pytest --cov=app tests/
```

### Run Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Run e2e tests (if configured)
npm run e2e
```

### Format Code

```bash
# Backend - Python
cd backend
black .
isort .

# Frontend - JavaScript/TypeScript
cd frontend
npm run lint -- --fix
```

### Build for Production

```bash
# Backend
cd backend
# No special build needed, runs directly

# Frontend
cd frontend
npm run build
npm run start  # Test production build locally
```

---

## 🐛 Debugging

### Frontend Debugging

1. Open http://localhost:3000
2. Press `F12` to open DevTools
3. Check Console tab for errors
4. Check Network tab for API calls
5. Check Application tab for stored data

**Useful Tips**:
```javascript
// In DevTools console:
localStorage  // Check stored data
sessionStorage  // Check session data
document.cookie  // Check cookies
```

### Backend Debugging

```bash
# Check logs
tail -f logs/app.log

# Use Python debugger
# Add to code: import pdb; pdb.set_trace()

# Monitor requests
curl -v http://localhost:8001/api/v1/sheet-sync/config
```

### Database Debugging

```bash
psql bitsheet

# Check table structure
\d sheet_sync_config

# Check data
SELECT * FROM sheet_sync_config LIMIT 5;

# Check relationships
SELECT * FROM field_mappings WHERE config_id = 1;

# Run explain on slow query
EXPLAIN SELECT * FROM reverse_sync_logs WHERE config_id = 1;
```

---

## 🔄 Development Workflow

### 1. Start Services

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Editor/IDE
# Use your favorite editor (VS Code, PyCharm, etc.)
```

### 2. Make Changes

```bash
# Backend changes
# Edit files in backend/app/
# Server auto-reloads (Ctrl+C to stop, then run again if needed)

# Frontend changes
# Edit files in frontend/app/sheet-sync/
# HMR (Hot Module Replacement) auto-updates
```

### 3. Test Changes

```bash
# Frontend
# Refresh browser (F5) if HMR doesn't catch it

# Backend
# Check http://localhost:8001/docs for API changes
# Test endpoint with curl or Postman
```

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit
git commit -m "feat: description of changes"

# Push
git push origin main
```

---

## 📊 Monitoring Development

### Performance Monitoring

```bash
# Frontend bundle size
cd frontend
npm run build
du -sh .next/

# Backend performance
# Check response times in logs
tail -f logs/app.log | grep "completed"

# Database queries
psql bitsheet
SELECT * FROM pg_stat_statements;
```

### Error Monitoring

```bash
# Check frontend errors
# DevTools Console tab

# Check backend errors
# Terminal output or logs/app.log

# Check database errors
# psql error messages or PostgreSQL logs
```

---

## 🛑 Stopping Services

### Clean Shutdown

```bash
# Terminal 1 (Backend): Press Ctrl+C
# Terminal 2 (Frontend): Press Ctrl+C
# Terminal 3 (Database): psql → \q

# Stop PostgreSQL (if running as service)
brew services stop postgresql@16  # macOS
sudo systemctl stop postgresql     # Linux
```

### Force Stop (if needed)

```bash
# Kill processes using ports
lsof -i :3000    # Frontend
lsof -i :8001    # Backend
lsof -i :5432    # Database

# Kill specific process
kill -9 <PID>
```

---

## 📋 Useful Commands Reference

### Database
```bash
psql bitsheet                    # Connect
\dt                              # List tables
\d table_name                    # Show table structure
SELECT * FROM table_name;        # Query data
\q                               # Exit
```

### Backend
```bash
python -m venv venv              # Create environment
source venv/bin/activate         # Activate environment
pip install -r requirements.txt  # Install deps
python -m pytest                 # Run tests
python -m uvicorn app.main:app --reload  # Start server
```

### Frontend
```bash
npm install                      # Install deps
npm run dev                      # Start dev server
npm run build                    # Build for prod
npm test                         # Run tests
npm run lint                     # Check code style
npm run lint -- --fix            # Fix style issues
```

### Git
```bash
git status                       # Check status
git add .                        # Stage changes
git commit -m "msg"              # Commit
git push origin main             # Push
git pull                         # Pull latest
```

---

## 🆘 Troubleshooting

### Issue: Port Already in Use
```bash
# Find what's using the port
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or use different port
python -m uvicorn app.main:app --port 8002
```

### Issue: Database Connection Failed
```bash
# Check PostgreSQL is running
psql --version

# Start PostgreSQL
brew services start postgresql@16

# Check connection
psql postgres -c "SELECT 1"
```

### Issue: Module Not Found Error
```bash
# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: Next.js Port Conflict
```bash
# Use different port
npm run dev -- -p 3001
```

### Issue: CORS Error
```bash
# Check CORS configured in FastAPI
# In backend/app/main.py:
# app.add_middleware(CORSMiddleware, ...)

# Make sure NEXT_PUBLIC_API_URL matches backend URL
```

---

## 🎯 Next Steps

1. ✅ All services running locally
2. ✅ Test OAuth flow manually
3. ✅ Create test configuration
4. ⏳ Run test suite
5. ⏳ Deploy to staging
6. ⏳ Production deployment

---

## 📞 Need Help?

### Check Documentation
- `/development/QUICK_START.md` - Quick setup
- `/development/INDEX.md` - Documentation index
- `/development/COMPLETE_ADIM_ABC_OVERVIEW.md` - Full system overview

### Check Logs
```bash
# Backend errors
tail -f /home/captain/bitsheet24/backend/logs/app.log

# Frontend errors
# Browser DevTools Console

# Database errors
psql bitsheet -c "SELECT * FROM pg_stat_statements;"
```

### Debugging Tips
1. Read error messages carefully
2. Check recent commits
3. Look at git diff for changes
4. Ask colleague for code review
5. Google the error message

---

## ✅ Verification Checklist

- [ ] All prerequisites installed
- [ ] Database created and migrated
- [ ] Backend environment configured
- [ ] Frontend environment configured
- [ ] Backend server running on 8001
- [ ] Frontend server running on 3000
- [ ] Can access http://localhost:3000
- [ ] Can access http://localhost:8001/docs
- [ ] Can connect to database with psql
- [ ] Tables visible in database
- [ ] No errors in console
- [ ] OAuth flow works end-to-end
- [ ] Can create configuration
- [ ] Can view sync history

---

**Ready to develop! 🎉**

All systems operational. Start making changes and enjoy development! 🚀

---

*Local Development Environment Guide - December 2024*
