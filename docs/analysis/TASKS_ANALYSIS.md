# 📋 Tasks & Task Comments - Görev Yönetimi

## 📊 Genel Bakış

**Mevcut Durum:**
- ✅ **Tasks**: 43,431 görev
- ✅ **Incremental Sync**: Aktif
- ✅ **Alt Görevler**: Aynı tabloda (PARENT_ID ile)
- ✅ **Task Comments**: Destekleniyor

## 🎯 Tablo Yapısı

### 1. Tasks (Görevler)

**Tablo**: `bitrix.tasks`

**Önemli Alanlar:**
```json
{
  "ID": "12345",
  "TITLE": "Görev başlığı",
  "STATUS": "2",              // 1=Yeni, 2=Devam Ediyor, 3=Beklemede, 4=Tamamlandı, 5=Ertelendi
  "PARENT_ID": "0",           // Alt görev ise parent task ID'si
  "RESPONSIBLE_ID": "42",     // Sorumlu kişi
  "CREATED_BY": "1",          // Oluşturan kişi
  "CREATED_DATE": "2025-01-01T10:00:00+03:00",
  "CHANGED_DATE": "2025-01-05T15:30:00+03:00",
  "CLOSED_DATE": "2025-01-06T09:00:00+03:00",
  "DEADLINE": "2025-01-10T17:00:00+03:00",
  "GROUP_ID": "5"             // Proje/Grup ID
}
```

**İndeksler:**
- `idx_tasks_data` - GIN index on data (JSONB)
- `idx_tasks_responsible` - (data->>'RESPONSIBLE_ID')
- `idx_tasks_status` - (data->>'STATUS')
- `idx_tasks_parent` - (data->>'PARENT_ID')

---

### 2. Task Comments (Görev Yorumları)

**Tablo**: `bitrix.task_comments`

**Önemli Alanlar:**
```json
{
  "ID": "789",
  "TASK_ID": "12345",         // Hangi göreve ait
  "AUTHOR_ID": "42",          // Yorumu yazan
  "POST_DATE": "2025-01-02T14:30:00+03:00",
  "POST_MESSAGE": "Yorum metni...",
  "ATTACHED_OBJECTS": {}      // Ekler (varsa)
}
```

**İlişki:**
```sql
task_comments.task_id = tasks.ID
```

---

## 🔄 Senkronizasyon

### Full Sync (İlk Kurulum)

```bash
# Tüm görevleri çek
python sync_bitrix.py tasks

# Tüm yorumları çek (ağır işlem - 43k görev için ~2-3 saat)
python sync_bitrix.py task_comments
```

### Incremental Sync (Günlük Kullanım)

```bash
# Son sync'den bu yana değişen görevler
python sync_bitrix.py tasks --incremental

# Değişen görevlerin yorumları
python sync_bitrix.py task_comments --incremental

# Tümü birden (daemon otomatik yapar)
python sync_bitrix.py all --incremental
```

**Incremental Mantığı:**
- Tasks: `CREATED_DATE > last_sync` OR `CHANGED_DATE > last_sync`
- Comments: Sadece değişen görevlerin yorumları

---

## 📈 Analiz Örnekleri

### 1. Görev Tamamlama Performansı

```sql
-- Personel bazlı görev tamamlama oranı
SELECT 
    u.data->>'NAME' as personel,
    COUNT(*) as toplam_gorev,
    COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) as tamamlanan,
    ROUND(100.0 * COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) / 
          NULLIF(COUNT(*), 0), 2) as tamamlanma_orani,
    COUNT(CASE WHEN (t.data->>'DEADLINE')::timestamp < NOW() 
                AND t.data->>'STATUS' != '5' THEN 1 END) as geciken_gorev
FROM bitrix.tasks t
JOIN bitrix.users u ON u.data->>'ID' = t.data->>'RESPONSIBLE_ID'
WHERE (t.data->>'CREATED_DATE')::timestamp > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.data->>'NAME'
ORDER BY toplam_gorev DESC;
```

### 2. Görev Durumu Dağılımı

```sql
-- Statü bazlı görev sayıları
SELECT 
    CASE data->>'STATUS'
        WHEN '1' THEN '1 - Yeni'
        WHEN '2' THEN '2 - Devam Ediyor'
        WHEN '3' THEN '3 - Beklemede'
        WHEN '4' THEN '4 - Tamamlandı (Gözden Geç)'
        WHEN '5' THEN '5 - Tamamlandı'
        WHEN '6' THEN '6 - Ertelendi'
        WHEN '7' THEN '7 - Reddedildi'
        ELSE 'Diğer'
    END as durum,
    COUNT(*) as gorev_sayisi,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as yuzde
FROM bitrix.tasks
GROUP BY data->>'STATUS'
ORDER BY gorev_sayisi DESC;
```

### 3. Alt Görev Analizi

```sql
-- Ana görev ve alt görevleri
SELECT 
    parent.data->>'ID' as ana_gorev_id,
    parent.data->>'TITLE' as ana_gorev,
    COUNT(child.id) as alt_gorev_sayisi,
    COUNT(CASE WHEN child.data->>'STATUS' = '5' THEN 1 END) as tamamlanan_alt,
    ROUND(100.0 * COUNT(CASE WHEN child.data->>'STATUS' = '5' THEN 1 END) / 
          NULLIF(COUNT(child.id), 0), 2) as alt_gorev_tamamlanma
FROM bitrix.tasks parent
LEFT JOIN bitrix.tasks child 
    ON child.data->>'PARENT_ID' = parent.data->>'ID'
    AND (child.data->>'PARENT_ID')::int > 0
WHERE (parent.data->>'PARENT_ID')::int = 0 
GROUP BY parent.id, parent.data->>'ID', parent.data->>'TITLE'
HAVING COUNT(child.id) > 0
ORDER BY alt_gorev_sayisi DESC
LIMIT 20;
```

### 4. Yorum Aktivitesi

```sql
-- En çok yorum alan görevler
SELECT 
    t.data->>'TITLE' as gorev,
    t.data->>'RESPONSIBLE_ID' as sorumlu_id,
    COUNT(tc.id) as yorum_sayisi,
    MIN((tc.data->>'POST_DATE')::timestamp) as ilk_yorum,
    MAX((tc.data->>'POST_DATE')::timestamp) as son_yorum
FROM bitrix.tasks t
LEFT JOIN bitrix.task_comments tc ON tc.data->>'TASK_ID' = t.data->>'ID'
GROUP BY t.id, t.data->>'TITLE', t.data->>'RESPONSIBLE_ID'
HAVING COUNT(tc.id) > 0
ORDER BY yorum_sayisi DESC
LIMIT 20;
```

### 5. Zamanında Teslim Oranı

```sql
-- Deadline karşılaştırması
SELECT 
    u.data->>'NAME' as personel,
    COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) as tamamlanan_gorev,
    
    -- Zamanında tamamlanan
    COUNT(CASE 
        WHEN t.data->>'STATUS' = '5' 
        AND (t.data->>'CLOSED_DATE')::timestamp <= (t.data->>'DEADLINE')::timestamp 
        THEN 1 
    END) as zamaninda_tamamlanan,
    
    -- Geciken
    COUNT(CASE 
        WHEN t.data->>'STATUS' = '5' 
        AND (t.data->>'CLOSED_DATE')::timestamp > (t.data->>'DEADLINE')::timestamp 
        THEN 1 
    END) as gecikmeli_tamamlanan,
    
    -- Oran
    ROUND(100.0 * COUNT(CASE 
        WHEN t.data->>'STATUS' = '5' 
        AND (t.data->>'CLOSED_DATE')::timestamp <= (t.data->>'DEADLINE')::timestamp 
        THEN 1 
    END) / NULLIF(COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END), 0), 2) 
    as zamaninda_teslim_orani
    
FROM bitrix.tasks t
JOIN bitrix.users u ON u.data->>'ID' = t.data->>'RESPONSIBLE_ID'
WHERE t.data->>'DEADLINE' IS NOT NULL
GROUP BY u.id, u.data->>'NAME'
ORDER BY tamamlanan_gorev DESC;
```

### 6. Ortalama Tamamlanma Süresi

```sql
-- Görev tipine göre ortalama süre
SELECT 
    t.data->>'GROUP_ID' as proje_id,
    COUNT(*) as gorev_sayisi,
    AVG(EXTRACT(EPOCH FROM (
        (t.data->>'CLOSED_DATE')::timestamp - (t.data->>'CREATED_DATE')::timestamp
    )) / 86400) as ortalama_gun,
    MIN(EXTRACT(EPOCH FROM (
        (t.data->>'CLOSED_DATE')::timestamp - (t.data->>'CREATED_DATE')::timestamp
    )) / 86400) as min_gun,
    MAX(EXTRACT(EPOCH FROM (
        (t.data->>'CLOSED_DATE')::timestamp - (t.data->>'CREATED_DATE')::timestamp
    )) / 86400) as max_gun
FROM bitrix.tasks t
WHERE t.data->>'STATUS' = '5'
  AND t.data->>'CLOSED_DATE' IS NOT NULL
GROUP BY t.data->>'GROUP_ID'
ORDER BY gorev_sayisi DESC;
```

---

## 🎯 Performans Metrikleri

### KPI Örnekleri

| Metrik | Hesaplama | Hedef |
|--------|-----------|-------|
| **Görev Tamamlama Oranı** | Tamamlanan / Toplam | >80% |
| **Zamanında Teslimat** | Deadline'dan önce / Tamamlanan | >70% |
| **Ortalama Tamamlama Süresi** | Avg(CLOSED - CREATED) | <3 gün |
| **Geciken Görev Sayısı** | NOW() > DEADLINE & STATUS != 5 | <10 |
| **Aktif Görev Yükü** | STATUS IN (1,2,3) | <20/kişi |
| **Yorum Aktivitesi** | Yorum/Görev oranı | >2 |

---

## 🚨 Önemli Notlar

### Alt Görevler
- ✅ Alt görevler aynı `tasks` tablosunda
- ✅ `PARENT_ID > 0` ise alt görev
- ✅ `PARENT_ID = 0` veya `NULL` ise ana görev
- ✅ İç içe seviye: Teorik olarak sınırsız (pratik: 2-3 seviye)

### Task Comments
- ⚠️ **Ağır işlem**: 43k görev × ortalama 3 yorum = ~130k yorum
- ⚠️ **İlk sync süresi**: ~2-3 saat (API limit nedeniyle)
- ✅ **Incremental sync**: Sadece değişen görevlerin yorumları
- ✅ **Öneri**: Full sync'i hafta sonları çalıştır

### API Limitler
- Bitrix24 API: 2 istek/saniye (webhook)
- task.commentitem.getlist: Görev başına 1 istek
- 43,431 görev = minimum 6 saat (retry'lar dahil daha uzun)

---

## 🔧 Optimizasyon Önerileri

### 1. Task Comments İçin
```bash
# Sadece aktif görevlerin yorumlarını çek
python -c "
from src.storage import get_engine
from src.bitrix.client import BitrixClient
from src.bitrix.ingestors import task_comments as tc
from sqlalchemy.sql import text

engine = get_engine()
client = BitrixClient()

# Sadece son 90 gün içinde değişen görevler
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT data->>'ID' 
        FROM bitrix.tasks 
        WHERE updated_at > NOW() - INTERVAL '90 days'
    '''))
    
    for row in result:
        tc.sync_for_task(client, int(row[0]))
"
```

### 2. Indexleme
```sql
-- Performans için önerilen indexler
CREATE INDEX IF NOT EXISTS idx_tasks_responsible 
    ON bitrix.tasks ((data->>'RESPONSIBLE_ID'));

CREATE INDEX IF NOT EXISTS idx_tasks_status 
    ON bitrix.tasks ((data->>'STATUS'));

CREATE INDEX IF NOT EXISTS idx_tasks_deadline 
    ON bitrix.tasks (((data->>'DEADLINE')::timestamp));

CREATE INDEX IF NOT EXISTS idx_task_comments_task_id 
    ON bitrix.task_comments ((data->>'TASK_ID'));
```

### 3. Materialized Views
```sql
-- Hızlı raporlama için
CREATE MATERIALIZED VIEW bitrix.v_task_summary AS
SELECT 
    t.data->>'RESPONSIBLE_ID' as user_id,
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) as completed,
    AVG(EXTRACT(EPOCH FROM NOW() - (t.data->>'CREATED_DATE')::timestamp) / 86400) as avg_age_days
FROM bitrix.tasks t
GROUP BY t.data->>'RESPONSIBLE_ID';

-- Günlük refresh
REFRESH MATERIALIZED VIEW bitrix.v_task_summary;
```

---

## 📊 Dashboard Önerileri

### Görev Yönetimi Dashboard'u
1. **Özet Kartlar**
   - Toplam aktif görev
   - Geciken görev sayısı
   - Tamamlanma oranı (bu ay)
   - Ortalama tamamlanma süresi

2. **Grafikler**
   - Durum dağılımı (pie chart)
   - Aylık tamamlanan görevler (line chart)
   - Kişi bazlı yük (bar chart)
   - Deadline yaklaşan görevler (liste)

3. **Tablolar**
   - En aktif görevler (yorum sayısı)
   - Geciken görevler (sorumlu ile)
   - Alt görev durumu
   - Departman performansı

---

## 🎯 Sonraki Adımlar

1. ✅ **Tasks incremental sync** - Tamamlandı
2. ✅ **Task comments yapısı** - Tamamlandı
3. ⏳ **Task comments full sync** - Test edilecek
4. ⏳ **Dashboard geliştirme** - Planlanacak
5. ⏳ **Otomatik raporlama** - Planlanacak
