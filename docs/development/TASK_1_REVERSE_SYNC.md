# 📋 TASK 1: Sheets → Bitrix24 Reverse Sync

**Başlama**: 7 Kasım 2025  
**Hedef**: Google Sheets'teki değişiklikleri otomatik olarak Bitrix24'e yazma

---

## 🎯 **TEKNIK GEREKSINIMLER**

### 1. **Veri Akışı (User OAuth + Webhook)**

```
┌─────────────────────────────────────────────────────────┐
│  KULLANICI: "Leads tablosunu aktarmak istiyorum"       │
├─────────────────────────────────────────────────────────┤

1️⃣  USER SETUP (İlk kez):
   Kullanıcı UI'dan:
   - [Google Sheets ile Bağlan] butonuna tıklar
   - Google OAuth izni verir
   - Access token + Refresh token kaydedilir (DB'ye)
   
2️⃣  TABLO SEÇIMI:
   - Kendi Google Drive'ındaki Sheet'i seçer
   - GID'i (tablo numarası) seçer
   - Bitrix24 entity type seçer (Leads, Contacts, Deals, vb)
   - Sistem otomatik header'ları oku → Field mapping
   
3️⃣  WEBHOOK KAYDI (Otomatik):
   - Google Apps Script webhook URL'i oluştur
   - Kullanıcının Sheet'ine webhook kuralı ekle
   - (Artık Sheets'teki her değişiklik webhook'a gelecek)

4️⃣  SHEETS'TE DEĞIŞIKLIK:
   Kullanıcı: E-mail kolonu değiştirdi
   ↓
   Google Apps Script webhook tetiklenir
   ↓
   API'ye POST gönderilir
   ↓
   Backend: POST /api/v1/sync/webhook alır
   
5️⃣  BACKEND İŞLEMSİ:
   - Değişen satırı tespit et
   - Field mapping'i uygula
   - Bitrix24 API'ye güncelleme yap
   - Log'a kaydet
   
6️⃣  SONUÇ:
   - Bitrix24'teki kayıt otomatik güncellendi
   - Sheet'e "✅ Senkronize" status yazıldı
   - Log'ta işlem kaydedildi
```

### 2. **Yapılacak Dosyalar** (User OAuth + Webhook tabanlı)

```
backend/
├── app/
│   ├── services/
│   │   ├── google_sheets_auth.py (YENİ) ← OAuth token yönetimi
│   │   ├── sheets_webhook.py (YENİ) ← Webhook registration
│   │   ├── field_detector.py (YENİ) ← Otomatik field mapping
│   │   ├── change_processor.py (YENİ) ← Webhook events işleme
│   │   └── bitrix_updater.py (YENİ) ← Bitrix24'e yazma
│   ├── api/
│   │   └── sheet_sync.py (YENİ) ← API endpoints
│   ├── models/
│   │   └── sheet_sync.py (YENİ) ← Database models
│   └── migrations/
│       └── 012_add_sheet_sync_tables.sql (YENİ)
│
frontend/
├── app/
│   └── sheet-sync/
│       ├── page.tsx (YENİ) ← Ana sayfa
│       └── components/
│           ├── GoogleSheetConnect.tsx (YENİ) ← OAuth bağlantı
│           ├── SheetSelector.tsx (YENİ) ← Sheet & tablo seç
│           ├── FieldMapping.tsx (YENİ) ← Mapping göster
│           ├── ColorScheme.tsx (YENİ) ← Renk seçimi
│           └── SyncHistory.tsx (YENİ) ← Sync logs
│
└── hooks/
    └── useSheetSync.ts (YENİ) ← State management
```

### 3. **Veritabanı Şeması** (USER OAUTH + WEBHOOK + DYNAMIC TABLES)

```sql
-- User Sheets Authentication (User OAuth)
CREATE TABLE auth.user_sheets_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100),                          -- Google OAuth user ID
    user_email VARCHAR(255),
    access_token TEXT,                             -- Google API token
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Dinamik Tablo Senkronizasyon Konfigürasyonu
CREATE TABLE bitrix.sheet_sync_config (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100),                          -- Hangi user?
    sheet_id VARCHAR(200),                         -- Google Sheet ID
    sheet_gid VARCHAR(50),                         -- Tablo gid
    sheet_name VARCHAR(255),                       -- Kullanıcının verdiği ad
    entity_type VARCHAR(100),                      -- "deals", "contacts", vb
    is_custom_view BOOLEAN DEFAULT false,          -- Custom view mi?
    color_scheme JSONB,                            -- {bgColor, textColor, font}
    webhook_url VARCHAR(500),                      -- Google Apps Script webhook
    webhook_registered BOOLEAN DEFAULT false,      -- Webhook kurulu mu?
    last_sync_at TIMESTAMP,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Otomatik Alan Eşlemeleri (Header'dan otomatik tespit)
CREATE TABLE bitrix.field_mappings (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT REFERENCES bitrix.sheet_sync_config(id),
    sheet_column_index INT,                        -- Kolon numarası (0, 1, 2...)
    sheet_column_name VARCHAR(100),                -- "Name", "Email", "Phone"
    bitrix_field VARCHAR(100),                     -- "TITLE", "EMAIL", "PHONE"
    data_type VARCHAR(50),                         -- "string", "number", "date", vb
    is_updatable BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reverse Sync Log (Değişiklik Kaydı)
CREATE TABLE bitrix.reverse_sync_logs (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT REFERENCES bitrix.sheet_sync_config(id),
    user_id VARCHAR(100),
    entity_id BIGINT,                              -- Bitrix24 entity ID
    sheet_row_id INT,                              -- Google Sheet satır numarası
    changed_fields JSONB,                          -- {field: {old: x, new: y}}
    status VARCHAR(20),                            -- pending, syncing, completed, failed
    error_message TEXT,
    webhook_payload JSONB,                         -- Google Apps Script'ten gelen data
    synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Webhook Events (Hangi event'ler gerildi)
CREATE TABLE bitrix.webhook_events (
    id BIGSERIAL PRIMARY KEY,
    config_id BIGINT REFERENCES bitrix.sheet_sync_config(id),
    event_type VARCHAR(50),                        -- "row_edited", "row_deleted", vb
    event_data JSONB,
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP,
    received_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_sheets_tokens_user ON auth.user_sheets_tokens(user_id);
CREATE INDEX idx_sheet_sync_config_user ON bitrix.sheet_sync_config(user_id);
CREATE INDEX idx_field_mappings_config ON bitrix.field_mappings(config_id);
CREATE INDEX idx_reverse_sync_logs_config ON bitrix.reverse_sync_logs(config_id);
CREATE INDEX idx_reverse_sync_logs_user ON bitrix.reverse_sync_logs(user_id);
CREATE INDEX idx_webhook_events_config ON bitrix.webhook_events(config_id);
```

---

## 🔄 **IŞLEM ADIMLARI** (User OAuth + Webhook tabanlı)

### **ADIM 1: Google OAuth Token Yönetimi** (3-4 gün)

**Dosya**: `backend/app/services/google_sheets_auth.py`

```python
class GoogleSheetsAuth:
    async def get_google_oauth_url():
        # "Google ile Bağlan" butonunun linki
        # scope: ["spreadsheets", "drive"]
        
    async def handle_oauth_callback(code, user_id):
        # OAuth code'u tokens'a dönüştür
        # access_token + refresh_token DB'ye kaydet
        
    async def get_valid_token(user_id):
        # Token'ı refresh et (süresi dolmuşsa)
        
    async def revoke_token(user_id):
        # User: "Bu bağlantıyı kes"
```

**Veritabanı**: `auth.user_sheets_tokens` tablosuna kaydedilecek

---

### **ADIM 2: Webhook Kurulumu & Field Detection** (4-5 gün)

**Dosya**: `backend/app/services/sheets_webhook.py`

```python
class SheetsWebhookManager:
    async def register_webhook(user_id, sheet_id, gid):
        # 1) Google Sheet'i oku → Header'ları al
        # 2) Field auto-detection: Header → Bitrix24 alanları
        # 3) Google Apps Script webhook kuralı ekle
        # 4) Webhook URL'i DB'ye kaydet
        
    async def auto_detect_fields(headers: List[str]):
        # Headers: ["Name", "Email", "Phone", "Status"]
        # ↓
        # Mapping: {
        #     "Name": "TITLE",
        #     "Email": "EMAIL",
        #     "Phone": "PHONE",
        #     "Status": "STATUS_ID"
        # }
```

---

### **ADIM 3: Webhook Listener API** (3-4 gün)

**Dosya**: `backend/app/api/sheet_sync.py`

```python
@router.post("/api/v1/sheet-sync/webhook")
async def handle_sheet_webhook(payload: dict, db: AsyncSession):
    """
    Google Apps Script'ten webhook POST gelir
    Payload örneği:
    {
        "sheet_id": "1234567890",
        "gid": "0",
        "event": "row_edited",
        "row_id": 5,
        "changes": {
            "Email": {"old": "old@mail.com", "new": "new@mail.com"},
            "Phone": {"old": "5551234567", "new": "5559876543"}
        }
    }
    """
    # 1) Config bul
    # 2) Field mapping uygula
    # 3) Bitrix24'e update yap
    # 4) Log'a kaydet
```

---

### **ADIM 4: Change Processing & Bitrix24 Update** (5-7 gün)

**Dosya**: `backend/app/services/change_processor.py`

```python
class ChangeProcessor:
    async def process_webhook_changes(config_id, webhook_payload):
        # 1) Field mapping'i al
        # 2) Sadece değişen alanları tut
        # 3) Data type'ları dönüştür (string → number, vb)
        # 4) Bitrix24'e gönder
```

**Dosya**: `backend/app/services/bitrix_updater.py`

```python
class BitrixUpdater:
    async def update_entity(entity_type, entity_id, changes):
        # Bitrix24 API'ye update POST yap
        # Örnek:
        # POST /crm.contact.update
        # {id: 123, fields: {EMAIL: "new@mail.com", PHONE: "123456"}}
```

---

### **ADIM 5: Frontend - Kurulum UI** (5-7 gün)

**Dosya**: `frontend/app/sheet-sync/page.tsx`

```
SAYFA 1: Google ile Bağlan
├─ [🔗 Google Sheets ile Bağlan] butonu
└─ OAuth flow başlar

SAYFA 2: Sheet ve Tablo Seçimi
├─ Kullanıcının Drive'ındaki Sheets listesi
├─ Sheet seçer → Tab'ları (gid) listele
├─ Bitrix24 entity type seçer
└─ Sistem otomatik field mapping yapar

SAYFA 3: Field Mapping Kontrolü
├─ Otomatik tespit edilen mapping göster
├─ "Name" → "TITLE" [✓ Doğru]
├─ "Email" → "EMAIL" [✓ Doğru]
├─ Eğer yanlışsa dropdown'dan düzelt
└─ [✅ Kaydet] butonu

SAYFA 4: Tablo Renkleri & Ayarları
├─ Poppins font (sabit)
├─ [🎨 Arka Plan Rengi Seç]
├─ [🎨 Yazı Rengi Seç]
├─ [✅ Kaydet & Webhook'u Aktifleştir]
└─ Başarı mesajı: "✅ Webhook kuruldu!"

SAYFA 5: Senkronizasyon Geçmişi
├─ Tüm sync işlemleri listesi
├─ Timestamp, satır numarası, değişen alanlar
├─ Status (✅ Başarılı / ❌ Hata)
└─ Hata detayları göster
```

---

### **ADIM 6: Şema Başında Poppins Font & Renkler** (2-3 gün)

**Dosya**: `frontend/app/sheet-sync/components/` ve tablo gösterim

```
Her tablo custom renk/font ile gösterilir:
- Poppins font (global CSS)
- User seçtiği arka plan rengi
- User seçtiği yazı rengi
```

---

## 📅 **ZAMAN TAHMINI** (User OAuth + Webhook tabanlı)

| Adım | İş | Gün |
|------|-----|-----|
| 1 | Google OAuth Token Yönetimi | 3-4 |
| 2 | Webhook Setup & Field Detection | 4-5 |
| 3 | Webhook Listener API | 3-4 |
| 4 | Change Processing & Bitrix Update | 5-7 |
| 5 | Frontend Setup UI (OAuth → Field Mapping) | 5-7 |
| 6 | Sync History & Status Gösterim | 2-3 |
| 7 | Testing, Debugging & Google Apps Script | 5-7 |
| --- | **TOPLAM** | **~27-37 gün** |

---

## 🎯 **HEMEN BAŞLAMAK İÇİN:**

### **1. İLK ADIM: Database Migrasyonu**

```bash
# migration dosyası oluştur
cat > backend/migrations/012_add_sheet_sync_tables.sql << 'EOF'
-- Buraya migration kodu yapıştır
EOF
```

### **2. İKİNCİ ADIM: Google OAuth Config**

`.env` dosyasına ekle:
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:3000/sheet-sync/oauth/callback
```

### **3. ÜÇÜNCÜ ADIM: Backend Services Oluştur**

İlk yapılacak:
- `backend/app/services/google_sheets_auth.py`
- `backend/app/services/sheets_webhook.py`
- `backend/app/api/sheet_sync.py`

### **4. DÖRDÜNCÜ ADIM: Frontend Pages**

- `frontend/app/sheet-sync/page.tsx`
- `frontend/app/sheet-sync/components/GoogleSheetConnect.tsx`
- `frontend/app/sheet-sync/components/SheetSelector.tsx`

---

## ✅ **CEVAPLAR ALINDI!**

| Soru | Cevap | Anlam |
|------|-------|-------|
| **Q1** | **B** | Her kullanıcının kendi Google OAuth credentials'ı |
| **Q2** | **B** | Google Apps Script webhook (real-time) |
| **Q3** | **Dynamic** | Kullanıcı istediği tabloyu aktarabilir + Custom View'ler |
| **Q4** | **A** | Sistem otomatik header'dan field mapping yapar |

---

## 🚀 **HEMEN KODLAMAYA BAŞLIYORUZ!**

Yapılacak adımlar sırası ile:

1. ✅ Google OAuth Token Management
2. ✅ Sheet Webhook Kurulumu
3. ✅ Field Auto-Detection (Header'dan)
4. ✅ Webhook Listener API
5. ✅ Change Detection & Bitrix24 Update
6. ✅ Frontend Setup UI
7. ✅ Testing
