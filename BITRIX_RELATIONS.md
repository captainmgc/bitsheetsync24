# 🔗 BITRIX24 VERİTABANI İLİŞKİ HARİTASI

## ✅ ÇÖZÜLEN SORUNLAR

### 1. ❌ ~~TASK tablosu: RESPONSIBLE_ID, CREATED_BY gibi alanlar JSONB'de yok~~
**ÇÖZÜM**: Tasks API camelCase döndürüyor. Alan isimleri farklı:

| Dökümantasyon | Gerçek API | Açıklama |
|---------------|------------|----------|
| RESPONSIBLE_ID | responsibleId | Sorumlu kişi |
| CREATED_BY | createdBy | Oluşturan |
| GROUP_ID | groupId | Proje/Grup |
| CHANGED_BY | changedBy | Değiştiren |
| CLOSED_BY | closedBy | Kapatan |
| PARENT_ID | parentId | Ana görev |
| STATUS_CHANGED_BY | statusChangedBy | Durum değiştiren |
| UF_CRM_TASK | ❓ Kontrol edilecek | CRM bağlantısı |

---

## 📊 VERİTABANI İLİŞKİ ŞEMASI

```
┌─────────────────┐
│     USERS       │
│  (users table)  │
└────────┬────────┘
         │
         │ assignedById / responsibleId / createdBy
         │
    ┌────┴────────────────────────────────────┐
    │                                         │
    ▼                                         ▼
┌─────────┐                            ┌──────────┐
│  LEADS  │                            │ CONTACTS │
└────┬────┘                            └─────┬────┘
     │                                       │
     │ ASSIGNED_BY_ID                        │ ASSIGNED_BY_ID
     │                                       │ COMPANY_ID
     │                                       │
     │            ┌──────────┐               │
     └────────────┤  DEALS   ├───────────────┘
                  └─────┬────┘
                        │
                        │ CONTACT_ID
                        │ COMPANY_ID
                        │ ASSIGNED_BY_ID
                        │
                  ┌─────┴──────┐
                  │ COMPANIES  │ ← HENÜZ ÇEKİLMEDİ
                  └────────────┘

┌──────────────┐
│  ACTIVITIES  │
└──────┬───────┘
       │
       │ OWNER_ID + OWNER_TYPE_ID
       │
       ├─ OWNER_TYPE_ID=1 → LEAD
       ├─ OWNER_TYPE_ID=2 → DEAL
       ├─ OWNER_TYPE_ID=3 → CONTACT
       └─ OWNER_TYPE_ID=4 → COMPANY

┌─────────┐
│  TASKS  │
└────┬────┘
     │
     │ responsibleId → USER
     │ createdBy → USER
     │ groupId → PROJECT/GROUP
     │ parentId → TASK (alt görevler)
     └─ UF_CRM_TASK → CRM entities (kontrol edilecek)

┌────────────────┐
│ TASK_COMMENTS  │
└───────┬────────┘
        │
        │ TASK_ID
        │ AUTHOR_ID → USER
        └─ Görev yorumları
```

---

## 🔢 OWNER_TYPE_ID KODLARI (Activities)

| Kod | Entity | Açıklama |
|-----|--------|----------|
| 1 | LEAD | Potansiyel müşteri |
| 2 | DEAL | Fırsat/Satış |
| 3 | CONTACT | Kişi |
| 4 | COMPANY | Firma |
| 14 | ❓ | Bizim veride var - araştırılacak |

---

## 📋 GOOGLE SHEETS İÇİN VIEW ÖNERİLERİ

### 1. CRM Ana View (crm_overview)
```sql
CREATE VIEW bitrix.v_crm_overview AS
SELECT 
    d.data->>'ID' as deal_id,
    d.data->>'TITLE' as deal_title,
    c.data->>'NAME' as contact_name,
    u.data->>'NAME' as responsible_name,
    d.data->>'STAGE_ID' as stage,
    d.data->>'OPPORTUNITY' as amount
FROM bitrix.deals d
LEFT JOIN bitrix.contacts c ON c.data->>'ID' = d.data->>'CONTACT_ID'
LEFT JOIN bitrix.users u ON u.data->>'ID' = d.data->>'ASSIGNED_BY_ID';
```

### 2. Tasks View (tasks_flat)
```sql
CREATE VIEW bitrix.v_tasks_flat AS
SELECT 
    (data->>'id')::int as task_id,
    data->>'title' as title,
    (data->>'responsibleId')::int as responsible_id,
    (data->>'createdBy')::int as created_by,
    (data->>'groupId')::int as group_id,
    (data->>'status')::int as status,
    data->>'deadline' as deadline
FROM bitrix.tasks;
```

### 3. Activity View (activities_decoded)
```sql
CREATE VIEW bitrix.v_activities_decoded AS
SELECT 
    (data->>'ID')::int as activity_id,
    data->>'SUBJECT' as subject,
    (data->>'OWNER_ID')::int as owner_id,
    (data->>'OWNER_TYPE_ID')::int as owner_type_id,
    CASE (data->>'OWNER_TYPE_ID')::int
        WHEN 1 THEN 'LEAD'
        WHEN 2 THEN 'DEAL'
        WHEN 3 THEN 'CONTACT'
        WHEN 4 THEN 'COMPANY'
        ELSE 'UNKNOWN'
    END as owner_type,
    (data->>'RESPONSIBLE_ID')::int as responsible_id
FROM bitrix.activities;
```

---

## ⏭️ SONRAKİ ADIMLAR

### 1. ✅ YAPILACAK:
- [ ] Companies tablosunu çek
- [ ] UF_CRM_TASK alanını kontrol et
- [ ] OWNER_TYPE_ID=14 ne olduğunu araştır
- [ ] SQL VIEW'ları oluştur
- [ ] Google Sheets test export (Leads 100 kayıt)

### 2. 📊 GOOGLE SHEETS EXPORT STRATEJİSİ:
1. **Test Phase**: Leads (100 kayıt) → Düz format
2. **Tarih Alanları**: Tarih ve Saat ayrı kolonlara
3. **İlişkiler**: Foreign key ID'ler + İsimler birlikte
4. **Batch Size**: 1000 satır/request (webhook limit testi)
5. **Filter**: Tarih filtreleme desteği

---

## 📅 TARİH FORMATLAMA

**PostgreSQL → Google Sheets:**
```sql
-- Tarih ve saat ayrı
TO_CHAR((data->>'DATE_CREATE')::timestamp, 'DD/MM/YYYY') as tarih,
TO_CHAR((data->>'DATE_CREATE')::timestamp, 'HH24:MI') as saat
```

**Türkçe Format:**
- Tarih: 05/11/2025
- Saat: 19:30
- Tam: 05/11/2025 19:30
