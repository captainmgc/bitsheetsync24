# 🚀 ADIM B - Quick Reference

## Oluşturulan 4 Ana Bileşen

### 1️⃣ `sheets_webhook.py` - Google Sheets Connector
```python
SheetsWebhookManager
├── get_sheet_headers()              # Headers oku
├── auto_detect_and_save_mappings()  # Field'ları algıla
├── register_webhook()                # Webhook kaydı yap
├── get_field_mappings()             # Mapping'leri getir
├── update_field_mapping()           # Kullanıcı düzeltmesi
├── unregister_webhook()             # Webhook'u devre dışı bırak
└── validate_webhook_payload()       # Payload kontrol et
```

**Ana Görev**: Sheet headers → Database mappings

---

### 2️⃣ `change_processor.py` - Sheet Changes Processor
```python
ChangeProcessor
├── process_webhook_event()          # Event'i işle
├── generate_bitrix_update()         # Update oluştur
├── mark_sync_status()               # Status güncelle
├── mark_webhook_event_processed()   # Event'i işaretle
├── get_pending_syncs()              # Beklemede olanları getir
└── get_sync_history()               # Geçmişi getir

SyncStatus Enum
├── PENDING      # Kuyrukta bekliyor
├── SYNCING      # İşleniyor
├── COMPLETED    # Tamamlandı
├── FAILED       # Başarısız
└── RETRYING     # Yeniden deneniyor
```

**Ana Görev**: Sheet values → Bitrix24 format

---

### 3️⃣ `bitrix_updater.py` - Bitrix24 API Caller
```python
Bitrix24Updater
├── update_entity()                  # Tek update gönder
├── process_sync_log()               # Sync log'u işle
├── batch_process_syncs()            # Batch'i gönder
├── get_update_status()              # Durumu kontrol et
└── retry_failed_syncs()             # Başarısız'ları yeniden dene
```

**Ana Görev**: Bitrix24'e POST request'ler gönder

---

### 4️⃣ `sheet_sync.py` (API) - FastAPI Endpoints
```
/api/v1/sheet-sync/oauth/start              [POST]
/api/v1/sheet-sync/oauth/callback           [GET]
/api/v1/sheet-sync/config                   [POST]
/api/v1/sheet-sync/config/{id}              [GET]
/api/v1/sheet-sync/config/{id}              [DELETE]
/api/v1/sheet-sync/field-mapping/{id}       [POST]
/api/v1/sheet-sync/webhook/{config_id}      [POST]
/api/v1/sheet-sync/logs/{config_id}         [GET]
/api/v1/sheet-sync/status/{log_id}          [GET]
/api/v1/sheet-sync/retry/{config_id}        [POST]
```

---

## 🔄 İş Akışı (Workflow)

```
USER LOGS IN
    ↓
POST /oauth/start → Google OAuth URL
    ↓
GET /oauth/callback → Token'lar kaydedilir
    ↓
POST /config → Sheet seçilir + Mapping yapılır
    ├─ Header'lar okunur (get_sheet_headers)
    ├─ Field'lar algılanır (auto_detect_and_save_mappings)
    └─ Webhook kaydedilir (register_webhook)
    ↓
USER EDITS SHEET
    ↓
Google Apps Script webhook tetiklenir
    ↓
POST /webhook/{config_id}
    ├─ Payload validate edilir
    ├─ WebhookEvent kaydedilir
    ├─ Change'ler algılanır
    └─ Bitrix24 update oluşturulur
    ↓
(Async) Bitrix24'e gönder
    ├─ Status = SYNCING
    ├─ POST request gönder
    └─ Status = COMPLETED/FAILED
    ↓
GET /logs/{config_id} → Geçmiş görüntülenir
```

---

## 📊 Database Tables (ADIM A'dan Kalıtsal)

```sql
auth.user_sheets_tokens
├── id (PK)
├── user_id (UNIQUE)
├── user_email
├── access_token
├── refresh_token
├── token_expires_at
├── scopes (array)
├── is_active
└── last_used_at

bitrix.sheet_sync_config
├── id (PK)
├── user_id (FK → user_sheets_tokens)
├── sheet_id
├── sheet_gid
├── sheet_name
├── entity_type
├── webhook_url
├── webhook_registered
├── color_scheme (JSONB)
├── enabled
└── last_sync_at

bitrix.field_mappings
├── id (PK)
├── config_id (FK → sheet_sync_config)
├── sheet_column_index
├── sheet_column_name
├── bitrix_field
├── data_type
└── is_updatable

bitrix.reverse_sync_logs
├── id (PK)
├── config_id (FK)
├── user_id
├── entity_id
├── sheet_row_id
├── changed_fields (JSONB)
├── status (pending/syncing/completed/failed)
├── error_message
└── webhook_payload (JSONB)

bitrix.webhook_events
├── id (PK)
├── config_id (FK)
├── event_type
├── event_data (JSONB)
├── processed
└── processed_at
```

---

## 🎯 Önemli Bağlantılar

### Services → API
```
sheets_webhook.py
    ↓
sheet_sync.py endpoints
    - POST /config → register_webhook()
    - GET /config/{id} → get_field_mappings()
    - POST /field-mapping/{id} → update_field_mapping()

change_processor.py
    ↓
sheet_sync.py endpoints
    - POST /webhook/{config_id} → process_webhook_event()
    - GET /logs/{config_id} → get_sync_history()
    - GET /status/{log_id} → get_update_status()

bitrix_updater.py
    ↓
sheet_sync.py endpoints
    - POST /retry/{config_id} → retry_failed_syncs()
    - (internally used in change_processor)
```

### Config → Services
```
config.py
├── google_client_id
├── google_client_secret
├── google_redirect_uri
├── frontend_url
├── bitrix24_webhook_url
└── redis_url (future: for async tasks)
        ↓
app/main.py
    ↓
sheet_sync router included
```

---

## 🔌 API Response Örnekleri

### POST /oauth/start
```json
{
  "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "550e8400-e29b-41d4-a716-446655440000"
}
```

### POST /config
```json
{
  "id": 1,
  "sheet_id": "1BxiMVs0XRA5nFMKejzYhbFS4fbb5DQKgvE2h2Xw3WmQ",
  "sheet_name": "Leads",
  "entity_type": "contacts",
  "webhook_url": "http://localhost:8000/api/v1/sheet-sync/webhook/1",
  "status": "registered",
  "mapping_result": {
    "total_fields": 5,
    "mapped_fields": 4,
    "unmapped_fields": 1,
    "confidence": 0.8
  }
}
```

### POST /webhook/{config_id}
```json
{
  "status": "queued",
  "event_id": 42,
  "log_id": 17
}
```

### GET /logs/{config_id}
```json
{
  "config_id": 1,
  "total": 3,
  "logs": [
    {
      "id": 17,
      "entity_id": "123",
      "row_id": 5,
      "status": "completed",
      "changes": {"TITLE": "John Smith", "PHONE": "+1234567890"},
      "error": null,
      "created_at": "2025-11-07T12:34:56Z"
    }
  ]
}
```

### GET /status/{log_id}
```json
{
  "id": 17,
  "entity_id": "123",
  "row_id": 5,
  "status": "completed",
  "changes": {"TITLE": "John Smith"},
  "error": null,
  "created_at": "2025-11-07T12:34:56Z",
  "updated_at": "2025-11-07T12:35:01Z"
}
```

---

## ⚙️ Configuration

### .env
```env
# Google OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=http://localhost:3000/sheet-sync/oauth/callback

# URLs
FRONTEND_URL=http://localhost:3000
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Bitrix24
BITRIX24_WEBHOOK_URL=https://sistem.japonkonutlari.com/rest/...
```

---

## 📝 Integration Checklist

- [x] OAuth Service (google_sheets_auth.py)
- [x] Webhook Service (sheets_webhook.py)
- [x] Change Processor (change_processor.py)
- [x] Bitrix24 Updater (bitrix_updater.py)
- [x] API Endpoints (sheet_sync.py)
- [x] Config Updates
- [x] Main App Router Integration
- [x] Syntax Validation
- [ ] **NEXT: Frontend Implementation (ADIM C)**

---

## 🚀 Çalıştırma

```bash
# Backend server başlat
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# API Docs
http://localhost:8000/docs (Swagger)
http://localhost:8000/redoc (ReDoc)
```

---

## 🔗 Kaynaklar

- `sheets_webhook.py` - Lines 1-380
- `change_processor.py` - Lines 1-400
- `bitrix_updater.py` - Lines 1-350
- `sheet_sync.py` (API) - Lines 1-550
- `ADIM_B_BACKEND_OZETIM.md` - Full detailed docs

---

**Status**: ✅ ADIM B TAMAMLANDI

**Next**: ADIM C - Frontend Implementation
