# 🔌 Bitrix24 REST API Referansı

## 📋 Genel Bilgiler

**Webhook URL**: `https://sistem.japonkonutlari.com/rest/1/g2gj8wxjs6izkzhy/`

**Rate Limit**: 2 istek/saniye (webhook için)

**Response Format**: JSON

---

## 🎯 Kullanılan API Metodları

### 1. CRM - Leads (Potansiyel Müşteriler)

#### crm.lead.list
```http
POST /crm.lead.list
```

**Parametreler:**
```json
{
    "select": ["*", "UF_*"],
    "filter": {
        ">DATE_CREATE": "2025-01-01T00:00:00",
        ">DATE_MODIFY": "2025-01-01T00:00:00",
        "LOGIC": "OR"
    },
    "order": {"ID": "ASC"},
    "start": 0
}
```

**Response:**
```json
{
    "result": [
        {
            "ID": "123",
            "TITLE": "Lead başlığı",
            "NAME": "Müşteri adı",
            "STATUS_ID": "NEW",
            "DATE_CREATE": "2025-01-01T10:00:00+03:00",
            "DATE_MODIFY": "2025-01-05T15:30:00+03:00",
            "ASSIGNED_BY_ID": "1"
        }
    ],
    "total": 7685
}
```

---

### 2. CRM - Contacts (Kişiler)

#### crm.contact.list
```http
POST /crm.contact.list
```

**Parametreler:**
```json
{
    "select": ["*", "UF_*"],
    "filter": {
        ">DATE_CREATE": "2025-01-01T00:00:00",
        ">DATE_MODIFY": "2025-01-01T00:00:00",
        "LOGIC": "OR"
    },
    "order": {"ID": "ASC"},
    "start": 0
}
```

---

### 3. CRM - Companies (Firmalar)

#### crm.company.list
```http
POST /crm.company.list
```

**Parametreler:**
```json
{
    "select": ["*", "UF_*"],
    "filter": {
        ">DATE_CREATE": "2025-01-01T00:00:00",
        ">DATE_MODIFY": "2025-01-01T00:00:00",
        "LOGIC": "OR"
    },
    "order": {"ID": "ASC"},
    "start": 0
}
```

---

### 4. CRM - Deals (Fırsatlar)

#### crm.deal.list
```http
POST /crm.deal.list
```

**Parametreler:**
```json
{
    "select": ["*", "UF_*"],
    "filter": {
        ">DATE_CREATE": "2025-01-01T00:00:00",
        ">DATE_MODIFY": "2025-01-01T00:00:00",
        "LOGIC": "OR"
    },
    "order": {"ID": "ASC"},
    "start": 0
}
```

---

### 5. CRM - Activities (Aktiviteler)

#### crm.activity.list
```http
POST /crm.activity.list
```

**Parametreler:**
```json
{
    "select": ["*"],
    "filter": {
        ">DATE_CREATE": "2025-01-01T00:00:00",
        ">LAST_UPDATED": "2025-01-01T00:00:00",
        "LOGIC": "OR"
    },
    "order": {"ID": "ASC"},
    "start": 0
}
```

**Not**: Activities için `DATE_MODIFY` yerine `LAST_UPDATED` kullanılır.

---

### 6. Tasks (Görevler)

#### tasks.task.list
```http
POST /tasks.task.list
```

**Parametreler:**
```json
{
    "select": ["*"],
    "filter": {
        ">CREATED_DATE": "2025-01-01T00:00:00",
        ">CHANGED_DATE": "2025-01-01T00:00:00",
        "LOGIC": "OR"
    },
    "order": {"ID": "ASC"},
    "start": 0
}
```

**Response Format** (özel):
```json
{
    "result": {
        "tasks": [
            {
                "id": "12345",
                "title": "Görev başlığı",
                "status": "2",
                "responsibleId": "42",
                "createdDate": "2025-01-01T10:00:00+03:00",
                "changedDate": "2025-01-05T15:30:00+03:00"
            }
        ]
    },
    "total": 43431
}
```

**Not**: 
- Tasks API nested response döner: `result.tasks` (diğerleri `result` direkt)
- Field names camelCase (diğerleri UPPERCASE)
- `DATE_CREATE` yerine `CREATED_DATE`
- `DATE_MODIFY` yerine `CHANGED_DATE`

---

### 7. Task Comments (Görev Yorumları)

#### task.commentitem.getlist
```http
POST /task.commentitem.getlist
```

**Parametreler:**
```json
{
    "TASKID": 12345,
    "PARAMS": {
        "select": ["*"]
    }
}
```

**Response:**
```json
{
    "result": [
        {
            "ID": "789",
            "AUTHOR_ID": "42",
            "POST_DATE": "2025-01-02T14:30:00+03:00",
            "POST_MESSAGE": "Yorum metni...",
            "ATTACHED_OBJECTS": {}
        }
    ]
}
```

**Not**: 
- Görev başına ayrı istek gerekir
- TASKID zorunlu parametre
- Pagination yok (tüm yorumlar tek seferde)

---

### 8. Users (Kullanıcılar)

#### user.get
```http
POST /user.get
```

**Parametreler:**
```json
{
    "FILTER": {
        "ACTIVE": true
    }
}
```

**Response:**
```json
{
    "result": [
        {
            "ID": "42",
            "NAME": "Ahmet",
            "LAST_NAME": "Yılmaz",
            "EMAIL": "ahmet@example.com",
            "WORK_POSITION": "Satış Müdürü",
            "PERSONAL_DEPARTMENT": ["5", "12"]
        }
    ]
}
```

---

### 9. Departments (Departmanlar)

#### department.get
```http
POST /department.get
```

**Parametreler:**
```json
{
    "order": {"ID": "ASC"}
}
```

**Response:**
```json
{
    "result": [
        {
            "ID": "5",
            "NAME": "Satış",
            "PARENT": "1",
            "SORT": 100
        }
    ]
}
```

---

## 🔧 Pagination (Sayfalama)

Tüm list metodları pagination destekler:

```json
{
    "start": 0,
    "limit": 50
}
```

**Default limit**: 50
**Maximum limit**: 50
**Next page**: `start = start + 50`

**Response ile birlikte gelen bilgi:**
```json
{
    "result": [...],
    "total": 1000,
    "next": 50
}
```

---

## 🎯 Filter Operatörleri

### Karşılaştırma
- `>` - Büyük
- `>=` - Büyük eşit
- `<` - Küçük
- `<=` - Küçük eşit
- `=` - Eşit (default)
- `!=` - Eşit değil

### Mantıksal
```json
{
    "LOGIC": "OR",
    ">DATE_CREATE": "2025-01-01",
    ">DATE_MODIFY": "2025-01-01"
}
```

- `LOGIC: OR` - Herhangi biri
- `LOGIC: AND` - Hepsi (default)

### Örnekler

**Son 7 günde oluşturulmuş veya güncellenmiş:**
```json
{
    "filter": {
        "LOGIC": "OR",
        ">DATE_CREATE": "2025-01-01T00:00:00",
        ">DATE_MODIFY": "2025-01-01T00:00:00"
    }
}
```

**Belirli kullanıcıya ait:**
```json
{
    "filter": {
        "ASSIGNED_BY_ID": "42"
    }
}
```

**Durum filtresi:**
```json
{
    "filter": {
        "STATUS_ID": "NEW"
    }
}
```

---

## 📊 Select (Alan Seçimi)

### Tüm alanlar:
```json
{
    "select": ["*"]
}
```

### Özel alanlar dahil:
```json
{
    "select": ["*", "UF_*"]
}
```

### Belirli alanlar:
```json
{
    "select": ["ID", "TITLE", "DATE_CREATE", "ASSIGNED_BY_ID"]
}
```

---

## ⚠️ Önemli Farklılıklar

| Entity | Date Create | Date Modify | Response Format | Notes |
|--------|-------------|-------------|-----------------|-------|
| **Leads** | DATE_CREATE | DATE_MODIFY | `result: []` | Standard |
| **Contacts** | DATE_CREATE | DATE_MODIFY | `result: []` | Standard |
| **Companies** | DATE_CREATE | DATE_MODIFY | `result: []` | Standard |
| **Deals** | DATE_CREATE | DATE_MODIFY | `result: []` | Standard |
| **Activities** | DATE_CREATE | LAST_UPDATED | `result: []` | LAST_UPDATED! |
| **Tasks** | CREATED_DATE | CHANGED_DATE | `result: {tasks:[]}` | Nested + camelCase |
| **Task Comments** | - | - | Per task | No incremental |
| **Users** | - | - | `result: []` | No date filter |
| **Departments** | - | - | `result: []` | No date filter |

---

## 🚀 Kullanım Örnekleri

### Python ile örnek istek:

```python
import httpx

webhook_url = "https://sistem.japonkonutlari.com/rest/1/g2gj8wxjs6izkzhy/"

# Lead listele
response = httpx.post(
    f"{webhook_url}crm.lead.list",
    json={
        "select": ["*", "UF_*"],
        "filter": {
            ">DATE_MODIFY": "2025-01-01T00:00:00"
        },
        "order": {"ID": "ASC"},
        "start": 0
    },
    timeout=30.0
)

data = response.json()
leads = data["result"]
total = data.get("total", 0)
```

### Görev yorumlarını çek:

```python
# Görev ID'si bilinen
task_id = 12345

response = httpx.post(
    f"{webhook_url}task.commentitem.getlist",
    json={
        "TASKID": task_id,
        "PARAMS": {"select": ["*"]}
    },
    timeout=30.0
)

comments = response.json()["result"]
```

---

## 🔍 Hata Kodları

| Kod | Açıklama | Çözüm |
|-----|----------|--------|
| **401** | Unauthorized | Webhook URL kontrol et |
| **403** | Forbidden | Yetki eksik |
| **404** | Not Found | Method adı yanlış |
| **429** | Too Many Requests | Rate limit (2/sn) |
| **500** | Internal Server Error | Bitrix24 hatası, tekrar dene |

---

## 📚 Kaynaklar

- [Bitrix24 REST API Docs](https://training.bitrix24.com/rest_help/)
- [CRM Methods](https://training.bitrix24.com/rest_help/crm/index.php)
- [Tasks Methods](https://training.bitrix24.com/rest_help/tasks/index.php)
- [User Methods](https://training.bitrix24.com/rest_help/users/index.php)

---

## 🎯 Sonraki Adımlar

1. ✅ Temel metodlar dokümante edildi
2. ⏳ Companies, Products, Invoices metodları eklenecek
3. ⏳ Batch işlemler (multi-request)
4. ⏳ Webhook event binding
