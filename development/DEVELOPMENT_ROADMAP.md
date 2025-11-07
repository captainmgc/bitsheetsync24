# 🎯 BitSheet24 - Geliştirme Planı & Roadmap

**Başlangıç**: 7 Kasım 2025  
**Hedef Şehir**: Production (End of November 2025)

---

## 📊 ROADMAP ÖZET

```
┌─────────────┬──────────────────────┬────────────────────┐
│  PHASE 1    │    PHASE 2           │    PHASE 3         │
│  MVP Ready  │  Security & Mgmt     │  Reporting & Scale │
│  (2-3w)     │  (2w)                │  (3w)              │
└─────────────┴──────────────────────┴────────────────────┘
     ↓              ↓                      ↓
 14 Kasım     21 Kasım              30 Kasım
 (Week 2)     (Week 3)              (Week 4-5)

PHASE 1 Hedefleri:
✓ Export Wizard UI
✓ Real-time Progress
✓ Reverse Sync (Sheets → Bitrix)
✓ Error Dashboard

PHASE 2 Hedefleri:
✓ Webhook Security
✓ RBAC System
✓ Audit Trail

PHASE 3 Hedefleri:
✓ Analytics Dashboard
✓ Export Formats (PDF, Excel)
✓ View Builder
```

---

## PHASE 1: MVP - Export & Monitoring (2-3 Hafta)

### 🎯 Hedefler
- [ ] Kullanıcılar tablo seçip export yapabilsin
- [ ] Export ilerlemesini real-time görebilsin
- [ ] Hatalar düzeltilip retry yapılabilsin
- [ ] Sheets'teki değişiklikler Bitrix24'e geri yazılabilsin

### 📋 SPRINT 1.1: Export Wizard UI (3-4 Gün)

#### Task 1.1.1: Export Form Components
**Files**: `frontend/app/export/`
```
└── export/
    ├── page.tsx (Main wizard entry point)
    ├── components/
    │   ├── WizardLayout.tsx (Multi-step layout)
    │   ├── StepSelector.tsx (Tablo seçimi)
    │   ├── FilterBuilder.tsx (Filtre seçenekleri)
    │   ├── FieldMapper.tsx (Alan eşleme)
    │   ├── PreviewTable.tsx (100 kayıt önizleme)
    │   ├── ConfirmDialog.tsx (Başlama onayı)
    │   └── SuccessNotification.tsx
    └── hooks/
        ├── useExportWizard.ts (State management)
        └── useExportPreview.ts (Preview data fetch)
```

**Component Detayları**:
- StepSelector: Checkbox list, "All tables" option
- FilterBuilder: Date range, status, custom filters
- FieldMapper: Turkish name mapping with toggles
- PreviewTable: React table library ile responsive table
- ConfirmDialog: Export settings summary

**Acceptance Criteria**:
- [ ] All 5 steps functional
- [ ] Form validation working
- [ ] API integration complete
- [ ] Error states handled
- [ ] Mobile responsive

---

#### Task 1.1.2: Export API Endpoints
**Files**: `backend/app/api/exports.py`

**New Endpoints**:
```python
POST /api/v1/exports
    - Create new export
    - Request body: {
        entity_name: string,
        export_type: "all" | "incremental" | "date_range",
        filters: {...},
        include_related: boolean,
        field_mappings: {...},
        batch_size: number,
        sheet_id: string,
        sheet_gid: string
      }
    - Returns: { id, status, created_at }

GET /api/v1/exports/{id}
    - Get export details
    - Returns: { id, status, progress, started_at, ... }

GET /api/v1/exports
    - List all exports (paginated)
    - Returns: { items: [...], total, page }

DELETE /api/v1/exports/{id}
    - Cancel running export
    - Returns: { status: "cancelled" }

POST /api/v1/exports/{id}/retry
    - Retry failed export
    - Returns: { status: "retrying" }
```

**Acceptance Criteria**:
- [ ] All endpoints return correct schemas
- [ ] Input validation working
- [ ] Database transactions atomic
- [ ] Error responses detailed

---

#### Task 1.1.3: Database Updates
**Files**: `backend/migrations/008_add_export_enhancements.sql`

```sql
-- Add new columns to export_logs
ALTER TABLE bitrix.export_logs ADD COLUMN IF NOT EXISTS (
    export_type VARCHAR(50) DEFAULT 'full',
    filter_config JSONB,
    field_mappings JSONB,
    sheet_id VARCHAR(100),
    sheet_gid VARCHAR(50),
    last_error_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3
);

-- Create export queue table
CREATE TABLE IF NOT EXISTS bitrix.export_queue (
    id BIGSERIAL PRIMARY KEY,
    export_id BIGINT REFERENCES bitrix.export_logs(id),
    entity_name VARCHAR(100),
    batch_number INT,
    status VARCHAR(20),
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create export metrics view
CREATE VIEW bitrix.v_export_metrics AS
SELECT 
    entity_name,
    COUNT(*) as total_exports,
    AVG(duration_seconds) as avg_duration,
    SUM(processed_records) as total_records,
    NOW() - MAX(completed_at) as time_since_last_export
FROM bitrix.export_logs
WHERE status = 'completed'
GROUP BY entity_name;
```

**Acceptance Criteria**:
- [ ] Migration applies without errors
- [ ] New columns usable
- [ ] Views query correctly

---

### 📋 SPRINT 1.2: Real-Time Progress Tracking (2-3 Gün)

#### Task 1.2.1: Progress Streaming (SSE)
**Files**: `backend/app/api/progress.py`

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

async def progress_stream(export_id: str):
    """Server-Sent Events stream for export progress"""
    while True:
        # Get current export status
        status = await get_export_status(export_id)
        
        # Yield progress update
        yield f"data: {json.dumps(status)}\n\n"
        
        # Stop if export finished
        if status['status'] in ['completed', 'failed', 'cancelled']:
            break
        
        await asyncio.sleep(1)  # Update every 1 second

@router.get("/api/v1/exports/{export_id}/progress")
async def export_progress(export_id: str):
    """Stream export progress"""
    return StreamingResponse(
        progress_stream(export_id),
        media_type="text/event-stream"
    )
```

**Response Format**:
```json
{
    "export_id": "12345",
    "status": "running",
    "current_batch": 5,
    "total_batches": 20,
    "processed_records": 2500,
    "total_records": 5000,
    "percentage": 50,
    "elapsed_seconds": 120,
    "estimated_remaining_seconds": 120,
    "current_entity": "leads",
    "bytes_transferred": 2500000,
    "error_count": 0,
    "warning_count": 2
}
```

**Acceptance Criteria**:
- [ ] SSE stream working
- [ ] Progress data accurate
- [ ] Updates smooth (1/sec)
- [ ] Handles disconnections
- [ ] No memory leaks

---

#### Task 1.2.2: Frontend Progress Component
**Files**: `frontend/app/export/components/ProgressTracker.tsx`

```tsx
'use client'

import { useEffect, useState } from 'react'
import { ProgressBar, EstimatedTime, ErrorAlert } from '@/components/ui'

export function ProgressTracker({ exportId }: { exportId: string }) {
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/exports/${exportId}/progress`)
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setProgress(data)
    }
    
    eventSource.onerror = () => {
      setError('Connection lost')
      eventSource.close()
    }
    
    return () => eventSource.close()
  }, [exportId])

  if (error) return <ErrorAlert message={error} />
  if (!progress) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <ProgressBar value={progress.percentage} max={100} />
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Processed" value={`${progress.processed_records}/${progress.total_records}`} />
        <Stat label="Batches" value={`${progress.current_batch}/${progress.total_batches}`} />
        <Stat label="Elapsed" value={formatSeconds(progress.elapsed_seconds)} />
        <Stat label="Remaining" value={formatSeconds(progress.estimated_remaining_seconds)} />
      </div>
      <CurrentEntity entity={progress.current_entity} />
      {progress.error_count > 0 && <ErrorSummary count={progress.error_count} />}
    </div>
  )
}
```

**Acceptance Criteria**:
- [ ] Real-time updates working
- [ ] Progress bar smooth
- [ ] Time estimates accurate
- [ ] Mobile responsive
- [ ] No UI freezing

---

### 📋 SPRINT 1.3: Reverse Sync (Sheets → Bitrix) (4-5 Gün)

#### Task 1.3.1: Sheets Data Reader
**Files**: `backend/app/services/sheets_reader.py`

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import structlog

logger = structlog.get_logger()

class SheetsReader:
    def __init__(self, credentials: Credentials):
        self.service = build('sheets', 'v4', credentials=credentials)
    
    async def read_sheet(self, sheet_id: str, sheet_gid: str) -> List[Dict]:
        """Read all data from sheet"""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{sheet_gid}'!A:Z"
        ).execute()
        
        values = result.get('values', [])
        headers = values[0] if values else []
        
        # Convert to list of dicts
        rows = [dict(zip(headers, row)) for row in values[1:]]
        
        logger.info("sheet_read", sheet_id=sheet_id, row_count=len(rows))
        return rows
    
    async def get_modified_rows(
        self,
        sheet_id: str,
        sheet_gid: str,
        since: datetime
    ) -> List[Dict]:
        """Get rows modified since timestamp"""
        all_rows = await self.read_sheet(sheet_id, sheet_gid)
        
        # Filter by modified timestamp column
        modified = [
            row for row in all_rows
            if row.get('_modified_at') and 
               datetime.fromisoformat(row['_modified_at']) > since
        ]
        
        return modified
```

**Acceptance Criteria**:
- [ ] Reads sheets correctly
- [ ] Handles large sheets (10k+)
- [ ] Detects modifications
- [ ] Error handling robust

---

#### Task 1.3.2: Change Detection Engine
**Files**: `backend/app/services/change_detector.py`

```python
class ChangeDetector:
    @staticmethod
    def detect_changes(
        original: Dict,
        modified: Dict,
        id_field: str = 'id'
    ) -> Dict:
        """Detect what changed between two records"""
        changes = {}
        
        for key in set(list(original.keys()) + list(modified.keys())):
            orig_val = original.get(key)
            mod_val = modified.get(key)
            
            if orig_val != mod_val:
                changes[key] = {
                    'old': orig_val,
                    'new': mod_val
                }
        
        return {
            'id': original.get(id_field),
            'changes': changes,
            'modified_count': len(changes)
        }
    
    @staticmethod
    def diff_sheets_and_db(
        sheet_rows: List[Dict],
        db_rows: List[Dict],
        id_field: str
    ) -> Dict:
        """Compare sheet vs database"""
        db_by_id = {row[id_field]: row for row in db_rows}
        
        changes = {
            'new': [],      # Only in sheets
            'modified': [], # In both, but different
            'deleted': []   # Only in DB
        }
        
        # Check new and modified
        for sheet_row in sheet_rows:
            row_id = sheet_row[id_field]
            db_row = db_by_id.get(row_id)
            
            if not db_row:
                changes['new'].append(sheet_row)
            elif sheet_row != db_row:
                diff = ChangeDetector.detect_changes(db_row, sheet_row)
                changes['modified'].append(diff)
        
        # Check deleted
        sheet_ids = {row[id_field] for row in sheet_rows}
        for row_id, db_row in db_by_id.items():
            if row_id not in sheet_ids:
                changes['deleted'].append(db_row)
        
        return changes
```

**Acceptance Criteria**:
- [ ] Diffs accurate
- [ ] Handles deleted records
- [ ] Detects type changes
- [ ] Performance OK (10k+ rows)

---

#### Task 1.3.3: Bitrix24 Sync Writer
**Files**: `backend/app/services/bitrix_sync_writer.py`

```python
from src.bitrix.client import BitrixClient
import structlog

logger = structlog.get_logger()

class BitrixSyncWriter:
    def __init__(self, client: BitrixClient):
        self.client = client
    
    async def update_records(
        self,
        entity: str,
        changes: Dict,
        batch_size: int = 50
    ) -> Dict:
        """Apply changes to Bitrix24"""
        results = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'errors': []
        }
        
        # Update modified records
        for change in changes['modified']:
            try:
                # Build update payload
                update_payload = {
                    'id': change['id'],
                    'fields': change['changes']
                }
                
                # Call Bitrix24 API
                method = f'crm.{entity.rstrip("s")}.update'
                self.client.call(method, update_payload)
                
                results['updated'] += 1
                logger.info("record_updated", entity=entity, id=change['id'])
                
            except Exception as e:
                results['errors'].append({
                    'id': change['id'],
                    'error': str(e)
                })
        
        # Create new records
        for new_record in changes['new']:
            try:
                create_payload = {'fields': new_record}
                method = f'crm.{entity.rstrip("s")}.add'
                response = self.client.call(method, create_payload)
                
                results['created'] += 1
                logger.info("record_created", entity=entity, response=response)
                
            except Exception as e:
                results['errors'].append({
                    'record': new_record,
                    'error': str(e)
                })
        
        return results
```

**Acceptance Criteria**:
- [ ] Updates work
- [ ] Creates work
- [ ] Error handling robust
- [ ] Batch optimization
- [ ] Logging detailed

---

#### Task 1.3.4: Reverse Sync API & Worker
**Files**: `backend/app/api/sync.py`

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/api/v1/sync/sheets-to-bitrix")
async def sync_sheets_to_bitrix(
    request: SyncRequest,  # sheet_id, sheet_gid, entity
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Sync changes from Sheets back to Bitrix24"""
    
    # Create sync log
    sync_log = SyncLog(
        entity_name=request.entity,
        direction='sheets_to_bitrix',
        status='running',
        started_at=datetime.now()
    )
    db.add(sync_log)
    await db.commit()
    
    # Queue background job
    background_tasks.add_task(
        perform_reverse_sync,
        sync_log_id=sync_log.id,
        sheet_id=request.sheet_id,
        sheet_gid=request.sheet_gid,
        entity=request.entity
    )
    
    return {
        "status": "queued",
        "sync_id": sync_log.id
    }

async def perform_reverse_sync(sync_log_id: int, sheet_id: str, sheet_gid: str, entity: str):
    """Background task for reverse sync"""
    try:
        # Read from Sheets
        sheets_reader = SheetsReader(get_user_credentials())
        sheet_data = await sheets_reader.read_sheet(sheet_id, sheet_gid)
        
        # Get DB data
        db_data = await get_entity_data(entity)
        
        # Detect changes
        detector = ChangeDetector()
        changes = detector.diff_sheets_and_db(sheet_data, db_data)
        
        # Apply to Bitrix24
        writer = BitrixSyncWriter(get_bitrix_client())
        results = await writer.update_records(entity, changes)
        
        # Update log
        sync_log = await get_sync_log(sync_log_id)
        sync_log.status = 'completed'
        sync_log.result = results
        sync_log.completed_at = datetime.now()
        await db.commit()
        
    except Exception as e:
        logger.error("reverse_sync_failed", error=str(e))
        sync_log.status = 'failed'
        sync_log.error = str(e)
        await db.commit()
```

**Acceptance Criteria**:
- [ ] Sync completes
- [ ] Changes applied to Bitrix24
- [ ] Log tracking accurate
- [ ] Error recovery works

---

### 📋 SPRINT 1.4: Error Dashboard (2-3 Gün)

#### Task 1.4.1: Error Tracking Database
**Files**: `backend/migrations/009_add_error_tracking.sql`

```sql
CREATE TABLE IF NOT EXISTS bitrix.error_events (
    id BIGSERIAL PRIMARY KEY,
    export_id BIGINT REFERENCES bitrix.export_logs(id),
    error_code VARCHAR(50),
    error_message TEXT,
    error_details JSONB,
    stack_trace TEXT,
    severity VARCHAR(20),  -- info, warning, error, critical
    source VARCHAR(100),   -- sheets_api, bitrix24_api, database, etc
    retryable BOOLEAN DEFAULT true,
    retry_count INT DEFAULT 0,
    occurred_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX idx_error_events_export ON bitrix.error_events(export_id);
CREATE INDEX idx_error_events_occurred ON bitrix.error_events(occurred_at DESC);
```

**Acceptance Criteria**:
- [ ] Table created
- [ ] Indexes working
- [ ] Data inserts fast

---

#### Task 1.4.2: Error API Endpoints
**Files**: `backend/app/api/errors.py`

```python
@router.get("/api/v1/errors")
async def list_errors(
    export_id: str = None,
    severity: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List recent errors with filtering"""
    query = select(ErrorEvent)
    
    if export_id:
        query = query.where(ErrorEvent.export_id == export_id)
    if severity:
        query = query.where(ErrorEvent.severity == severity)
    
    errors = await db.execute(
        query.order_by(ErrorEvent.occurred_at.desc())
            .limit(limit)
            .offset(offset)
    )
    
    return errors.scalars().all()

@router.get("/api/v1/errors/{error_id}")
async def get_error_details(error_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed error information"""
    error = await db.get(ErrorEvent, error_id)
    return error

@router.post("/api/v1/errors/{error_id}/resolve")
async def resolve_error(error_id: int, db: AsyncSession = Depends(get_db)):
    """Mark error as resolved"""
    error = await db.get(ErrorEvent, error_id)
    error.resolved_at = datetime.now()
    await db.commit()
    return {"status": "resolved"}

@router.post("/api/v1/errors/{error_id}/retry")
async def retry_failed_operation(
    error_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Retry the operation that failed"""
    error = await db.get(ErrorEvent, error_id)
    
    if error.retry_count >= 3:
        return {"status": "max_retries_exceeded"}
    
    error.retry_count += 1
    await db.commit()
    
    background_tasks.add_task(retry_export, error.export_id)
    return {"status": "retrying", "attempt": error.retry_count}
```

**Acceptance Criteria**:
- [ ] All endpoints working
- [ ] Filtering accurate
- [ ] Retry logic safe
- [ ] Performance good

---

#### Task 1.4.3: Error Dashboard Frontend
**Files**: `frontend/app/errors/page.tsx`

```tsx
'use client'

import { useEffect, useState } from 'react'
import { Table, Badge, Button } from '@/components/ui'

export default function ErrorsDashboard() {
  const [errors, setErrors] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchErrors()
    const interval = setInterval(fetchErrors, 5000) // Poll every 5s
    return () => clearInterval(interval)
  }, [filter])

  const fetchErrors = async () => {
    const res = await fetch(`/api/v1/errors?severity=${filter}`)
    const data = await res.json()
    setErrors(data)
    setLoading(false)
  }

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">Error Dashboard</h1>
      
      {/* Filter buttons */}
      <div className="flex gap-2">
        {['all', 'warning', 'error', 'critical'].map(severity => (
          <Button
            key={severity}
            variant={filter === severity ? 'primary' : 'outline'}
            onClick={() => setFilter(severity)}
          >
            {severity}
          </Button>
        ))}
      </div>

      {/* Error table */}
      <Table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Severity</th>
            <th>Error Code</th>
            <th>Message</th>
            <th>Source</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {errors.map(error => (
            <tr key={error.id}>
              <td>{new Date(error.occurred_at).toLocaleString('tr-TR')}</td>
              <td><Badge severity={error.severity}>{error.severity}</Badge></td>
              <td className="font-mono">{error.error_code}</td>
              <td className="max-w-md truncate">{error.error_message}</td>
              <td>{error.source}</td>
              <td>
                {error.retryable && (
                  <Button size="sm" onClick={() => retryError(error.id)}>
                    Retry
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  )
}
```

**Acceptance Criteria**:
- [ ] Errors displayed
- [ ] Filtering works
- [ ] Retry button functional
- [ ] Real-time updates
- [ ] Responsive design

---

## PHASE 2: Security & Management (2 Hafta)

### 📋 SPRINT 2.1: Webhook Security (2-3 Gün)

#### Task 2.1.1: HMAC Signature Verification
**Files**: `backend/app/middleware/webhook_security.py`

```python
import hmac
import hashlib
from fastapi import HTTPException, status

class WebhookSecurity:
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify HMAC-SHA256 signature"""
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    @staticmethod
    async def webhook_security_middleware(request: Request):
        """Middleware to verify webhook signatures"""
        signature = request.headers.get('X-Webhook-Signature')
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature"
            )
        
        body = await request.body()
        
        if not WebhookSecurity.verify_signature(
            body,
            signature,
            settings.webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
```

**Acceptance Criteria**:
- [ ] Signature verification working
- [ ] Rejects unsigned requests
- [ ] Handles timing attacks safely
- [ ] Performance acceptable

---

### 📋 SPRINT 2.2: RBAC System (3-4 Gün)

#### Task 2.2.1: Database Schema
**Files**: `backend/migrations/010_add_rbac.sql`

```sql
-- Roles table
CREATE TABLE IF NOT EXISTS auth.roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Permissions table
CREATE TABLE IF NOT EXISTS auth.permissions (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE,
    description TEXT,
    resource VARCHAR(50),
    action VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Role-Permission mapping
CREATE TABLE IF NOT EXISTS auth.role_permissions (
    role_id BIGINT REFERENCES auth.roles(id),
    permission_id BIGINT REFERENCES auth.permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role mapping
CREATE TABLE IF NOT EXISTS auth.user_roles (
    user_id VARCHAR(100),  -- From Google OAuth
    role_id BIGINT REFERENCES auth.roles(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- Default roles
INSERT INTO auth.roles (name, description) VALUES
    ('admin', 'Full system access'),
    ('editor', 'Can export and manage data'),
    ('viewer', 'Read-only access'),
    ('operator', 'Manual sync and monitoring only');

-- Default permissions
INSERT INTO auth.permissions (code, resource, action, description) VALUES
    ('export.create', 'export', 'create', 'Create new exports'),
    ('export.read', 'export', 'read', 'View exports'),
    ('export.delete', 'export', 'delete', 'Cancel exports'),
    ('data.read', 'data', 'read', 'View raw data'),
    ('settings.write', 'settings', 'write', 'Modify settings'),
    ('admin.write', 'admin', 'write', 'System administration');

-- Admin role permissions (all)
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM auth.roles r, auth.permissions p WHERE r.name = 'admin';

-- Editor role permissions
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM auth.roles r, auth.permissions p 
WHERE r.name = 'editor' AND p.code IN ('export.create', 'export.read', 'data.read');
```

**Acceptance Criteria**:
- [ ] Schema created
- [ ] Default roles/perms inserted
- [ ] Queries indexed
- [ ] No conflicts

---

#### Task 2.2.2: RBAC Middleware & Decorators
**Files**: `backend/app/middleware/rbac.py`

```python
from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy import select

async def check_permission(
    required_permission: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to check user permissions"""
    
    # Get user roles
    stmt = select(UserRole).where(UserRole.user_id == current_user['id'])
    user_roles = await db.execute(stmt)
    role_ids = [ur.role_id for ur in user_roles.scalars()]
    
    if not role_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No roles assigned"
        )
    
    # Check if user has required permission
    stmt = select(Permission).join(RolePermission).where(
        (RolePermission.role_id.in_(role_ids)) &
        (Permission.code == required_permission)
    )
    
    permission = await db.execute(stmt)
    if not permission.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required_permission}"
        )
    
    return current_user

def require_permission(permission: str):
    """Decorator for route protection"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user = Depends(lambda: check_permission(permission, ...)), **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Usage**:
```python
@router.post("/api/v1/exports")
async def create_export(
    request: ExportRequest,
    current_user = Depends(lambda: check_permission('export.create'))
):
    # Only users with 'export.create' permission can access
    pass
```

**Acceptance Criteria**:
- [ ] Decorator works
- [ ] Routes protected
- [ ] Permission checks fast
- [ ] Error messages clear

---

### 📋 SPRINT 2.3: Audit Trail (2-3 Gün)

#### Task 2.3.1: Audit Log Schema
**Files**: `backend/migrations/011_add_audit_trail.sql`

```sql
CREATE TABLE IF NOT EXISTS bitrix.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    user_email VARCHAR(255),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id BIGINT,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(20),
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON bitrix.audit_logs(user_id);
CREATE INDEX idx_audit_timestamp ON bitrix.audit_logs(timestamp DESC);
CREATE INDEX idx_audit_resource ON bitrix.audit_logs(resource_type, resource_id);
```

**Acceptance Criteria**:
- [ ] Table created
- [ ] Indexes working
- [ ] Fast writes

---

#### Task 2.3.2: Audit Middleware
**Files**: `backend/app/middleware/audit_logger.py`

```python
from app.models.audit_log import AuditLog
import structlog

logger = structlog.get_logger()

class AuditLogger:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: int = None,
        changes: dict = None,
        request: Request = None
    ):
        """Log user action for audit trail"""
        
        audit_log = AuditLog(
            user_id=user_id,
            user_email=get_user_email(user_id),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get('user-agent') if request else None,
            timestamp=datetime.now()
        )
        
        db.add(audit_log)
        await db.commit()
        
        logger.info("audit_action",
                   user_id=user_id,
                   action=action,
                   resource=f"{resource_type}:{resource_id}")

# Usage in routes
@router.post("/api/v1/exports")
async def create_export(
    request: Request,
    export_request: ExportRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    export = await ExportService.create(export_request, db)
    
    await AuditLogger.log_action(
        db=db,
        user_id=current_user['id'],
        action='create',
        resource_type='export',
        resource_id=export.id,
        request=request
    )
    
    return export
```

**Acceptance Criteria**:
- [ ] Actions logged
- [ ] Changes tracked
- [ ] Performance OK
- [ ] IP/User-Agent captured

---

## PHASE 3: Reporting & Advanced Features (3 Hafta)

### 📋 SPRINT 3.1: Analytics Dashboard (3-4 Gün)

Dashboard components ve widgets...

### 📋 SPRINT 3.2: Export Formats (2-3 Gün)

PDF, Excel, CSV export desteği...

### 📋 SPRINT 3.3: View Builder (4-5 Gün)

Custom relationship view builder...

---

## 📅 DETAYLI ZAMAN ÇIZELGESI

```
HAFTA 1 (7-11 Kasım):
  Monday 7:    Feature analysis & planning ✓
  Tue 8-Wed 9: Export Wizard UI (Task 1.1.1)
  Thu 10-Fri 11: Export API (Task 1.1.2-3)

HAFTA 2 (14-18 Kasım):
  Mon 14-Tue 15: Progress Tracking (Task 1.2)
  Wed 16-Thu 17: Reverse Sync Implementation (Task 1.3)
  Fri 18:       Integration testing

HAFTA 3 (21-25 Kasım):
  Mon 21-Tue 22: Error Dashboard (Task 1.4)
  Wed 23-Thu 24: Webhook Security (Task 2.1)
  Fri 25:       RBAC Implementation (Task 2.2)

HAFTA 4-5 (28 Kasım-5 Aralık):
  Audit Trail, Analytics Dashboard, Export Formats
```

---

## ✅ BAŞARIYA ÖLÇÜTLERİ

### PHASE 1 Completion Criteria
- [ ] Export wizard tamamlanmış ve test edilmiş
- [ ] Progress tracking real-time çalışıyor
- [ ] Reverse sync (Sheets → Bitrix) çalışıyor
- [ ] Error dashboard operasyonel
- [ ] E2E tests written ve passing

### PHASE 2 Completion Criteria
- [ ] Webhook signature verification aktif
- [ ] RBAC system fully implemented
- [ ] Audit trail logging all actions
- [ ] Security audit completed

### PHASE 3 Completion Criteria
- [ ] Analytics dashboard live
- [ ] PDF/Excel export working
- [ ] View builder UI complete
- [ ] Performance benchmarks met

---

## 🔧 GELIŞTIRME ORTAMı

```
Frontend:     http://localhost:3000
Backend API:  http://localhost:8000/docs
Database:     psql postgresql://bitsheet:***@localhost:5432/bitsheet_db
Redis:        redis://localhost:6379/0
```

---

**Hazırlandı**: 7 Kasım 2025
**Durum**: READY FOR DEVELOPMENT
**Next Review**: 14 Kasım 2025 (End of Week 1)
