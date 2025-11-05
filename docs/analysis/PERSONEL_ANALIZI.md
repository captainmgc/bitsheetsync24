# 👥 Personel Performans Analizi Ölçütleri

**Mevcut Durum:** 50 aktif personel

## 📊 1. SATIŞ PERFORMANSI ANALİZİ

### A. Bireysel Satış Metrikleri
**Veri Kaynakları:** `deals`, `contacts`, `leads`, `users`

```sql
-- Satış temsilcisi performans raporu
SELECT 
    u.data->>'NAME' as personel,
    u.data->>'WORK_POSITION' as pozisyon,
    u.data->>'UF_DEPARTMENT' as departman,
    
    -- Lead metrikleri
    COUNT(DISTINCT l.id) as toplam_lead,
    COUNT(DISTINCT CASE WHEN d.id IS NOT NULL THEN l.id END) as donusen_lead,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN d.id IS NOT NULL THEN l.id END) / 
          NULLIF(COUNT(DISTINCT l.id), 0), 2) as lead_donusum_orani,
    
    -- Deal metrikleri
    COUNT(DISTINCT d.id) as toplam_deal,
    COUNT(DISTINCT CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' THEN d.id END) as kazanilan_deal,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' THEN d.id END) / 
          NULLIF(COUNT(DISTINCT d.id), 0), 2) as deal_kazanma_orani,
    
    -- Gelir metrikleri
    SUM(CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' 
             THEN (d.data->>'OPPORTUNITY')::numeric 
             ELSE 0 END) as toplam_gelir,
    AVG(CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' 
             THEN (d.data->>'OPPORTUNITY')::numeric 
             ELSE NULL END) as ortalama_deal_degeri,
    
    -- Süre metrikleri
    AVG(EXTRACT(DAY FROM 
        (d.data->>'CLOSEDATE')::timestamp - (d.data->>'BEGINDATE')::timestamp
    )) as ortalama_kapanma_suresi_gun

FROM bitrix.users u
LEFT JOIN bitrix.leads l ON l.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
LEFT JOIN bitrix.deals d ON d.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
WHERE u.data->>'ACTIVE' = 'true'
GROUP BY u.id, u.data->>'NAME', u.data->>'WORK_POSITION', u.data->>'UF_DEPARTMENT'
ORDER BY toplam_gelir DESC NULLS LAST;
```

**Ölçütler:**
- ✅ Lead dönüşüm oranı (hedef: >%20)
- ✅ Deal kazanma oranı (hedef: >%30)
- ✅ Ortalama deal değeri (TL)
- ✅ Toplam gelir (aylık/yıllık)
- ✅ Ortalama kapanma süresi (gün)

---

## 📋 2. GÖREV YÖNETİMİ & VERİMLİLİK

### B. Task Performansı
**Veri Kaynakları:** `tasks`, `users`

```sql
-- Görev tamamlama performansı
SELECT 
    u.data->>'NAME' as personel,
    u.data->>'WORK_POSITION' as pozisyon,
    
    -- Görev sayıları
    COUNT(*) as toplam_gorev,
    COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) as tamamlanan,
    COUNT(CASE WHEN t.data->>'STATUS' IN ('1','2','3') THEN 1 END) as devam_eden,
    COUNT(CASE WHEN (t.data->>'DEADLINE')::timestamp < NOW() 
                AND t.data->>'STATUS' != '5' THEN 1 END) as geciken,
    
    -- Tamamlanma oranı
    ROUND(100.0 * COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) / 
          NULLIF(COUNT(*), 0), 2) as tamamlanma_orani,
    
    -- Zamanında tamamlama
    ROUND(100.0 * COUNT(CASE 
        WHEN t.data->>'STATUS' = '5' 
        AND (t.data->>'CLOSED_DATE')::timestamp <= (t.data->>'DEADLINE')::timestamp 
        THEN 1 END) / NULLIF(COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END), 0), 2) 
        as zamaninda_tamamlama_orani,
    
    -- Ortalama tamamlanma süresi
    AVG(CASE WHEN t.data->>'STATUS' = '5' THEN
        EXTRACT(DAY FROM 
            (t.data->>'CLOSED_DATE')::timestamp - (t.data->>'CREATED_DATE')::timestamp
        )
    END) as ort_tamamlanma_suresi_gun

FROM bitrix.users u
LEFT JOIN bitrix.tasks t ON t.data->>'RESPONSIBLE_ID' = u.data->>'ID'
WHERE u.data->>'ACTIVE' = 'true'
GROUP BY u.id, u.data->>'NAME', u.data->>'WORK_POSITION'
ORDER BY tamamlanma_orani DESC;
```

**Ölçütler:**
- ✅ Görev tamamlama oranı (hedef: >%80)
- ✅ Zamanında tamamlama oranı (hedef: >%70)
- ✅ Geciken görev sayısı (hedef: <5)
- ✅ Ortalama tamamlanma süresi
- ✅ Aktif görev yükü

---

## 📞 3. MÜŞTERİ ETKİLEŞİM ANALİZİ

### C. Aktivite Performansı
**Veri Kaynakları:** `activities`, `users`

```sql
-- Müşteri etkileşim aktivitesi
SELECT 
    u.data->>'NAME' as personel,
    
    -- Aktivite türleri
    COUNT(*) as toplam_aktivite,
    COUNT(CASE WHEN a.data->>'TYPE_ID' = '1' THEN 1 END) as aramalar,
    COUNT(CASE WHEN a.data->>'TYPE_ID' = '2' THEN 1 END) as toplanti,
    COUNT(CASE WHEN a.data->>'TYPE_ID' = '4' THEN 1 END) as email,
    
    -- Günlük ortalama
    ROUND(COUNT(*)::numeric / 
          NULLIF(EXTRACT(DAY FROM NOW() - MIN((a.data->>'CREATED')::timestamp)), 0), 1) 
          as gunluk_ortalama_aktivite,
    
    -- Son aktivite tarihi
    MAX((a.data->>'CREATED')::timestamp) as son_aktivite_tarihi,
    
    -- Aktif gün sayısı
    COUNT(DISTINCT DATE((a.data->>'CREATED')::timestamp)) as aktif_gun_sayisi

FROM bitrix.users u
LEFT JOIN bitrix.activities a ON a.data->>'RESPONSIBLE_ID' = u.data->>'ID'
WHERE u.data->>'ACTIVE' = 'true'
  AND (a.data->>'CREATED')::timestamp > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.data->>'NAME'
ORDER BY gunluk_ortalama_aktivite DESC NULLS LAST;
```

**Ölçütler:**
- ✅ Günlük ortalama aktivite sayısı (hedef: >8)
- ✅ Arama sayısı (telefon görüşmeleri)
- ✅ Toplantı sayısı
- ✅ Email aktivitesi
- ✅ Müşteri etkileşim sıklığı

---

## 🏢 4. DEPARTMAN BAZLI ANALİZ

### D. Departman Performans Karşılaştırması
**Veri Kaynakları:** `users`, `departments`, `deals`, `tasks`

```sql
-- Departman karşılaştırması
WITH dept_stats AS (
    SELECT 
        d.data->>'NAME' as departman,
        u.data->>'ID' as user_id,
        COUNT(DISTINCT dl.id) as deal_count,
        SUM(CASE WHEN dl.data->>'STAGE_ID' LIKE '%WON%' 
                 THEN (dl.data->>'OPPORTUNITY')::numeric 
                 ELSE 0 END) as revenue,
        COUNT(DISTINCT t.id) as task_count,
        COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) as completed_tasks
    FROM bitrix.departments d
    JOIN bitrix.users u ON u.data->>'UF_DEPARTMENT' @> d.data->>'ID'::jsonb
    LEFT JOIN bitrix.deals dl ON dl.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
    LEFT JOIN bitrix.tasks t ON t.data->>'RESPONSIBLE_ID' = u.data->>'ID'
    GROUP BY d.id, d.data->>'NAME', u.data->>'ID'
)
SELECT 
    departman,
    COUNT(user_id) as personel_sayisi,
    SUM(deal_count) as toplam_deal,
    SUM(revenue) as toplam_gelir,
    ROUND(SUM(revenue) / NULLIF(COUNT(user_id), 0), 2) as kisi_basina_gelir,
    ROUND(100.0 * SUM(completed_tasks) / NULLIF(SUM(task_count), 0), 2) as gorev_tamamlanma_orani
FROM dept_stats
GROUP BY departman
ORDER BY toplam_gelir DESC NULLS LAST;
```

**Ölçütler:**
- ✅ Departman bazlı toplam gelir
- ✅ Kişi başına ortalama gelir
- ✅ Departman görev tamamlanma oranı
- ✅ Deal dönüşüm oranı
- ✅ Departman verimliliği

---

## ⏱️ 5. ZAMAN YÖNETİMİ ANALİZİ

### E. Çalışma Süresi ve Verimlilik
**Veri Kaynakları:** `users`, `activities`, `tasks`

```sql
-- Zaman dağılımı analizi
SELECT 
    u.data->>'NAME' as personel,
    
    -- Aktivite dağılımı (son 30 gün)
    COUNT(DISTINCT DATE((a.data->>'CREATED')::timestamp)) as aktif_gun_sayisi,
    COUNT(a.id) as toplam_aktivite,
    
    -- Saat bazlı dağılım
    COUNT(CASE WHEN EXTRACT(HOUR FROM (a.data->>'CREATED')::timestamp) BETWEEN 9 AND 12 
               THEN 1 END) as sabah_aktivite,
    COUNT(CASE WHEN EXTRACT(HOUR FROM (a.data->>'CREATED')::timestamp) BETWEEN 13 AND 17 
               THEN 1 END) as ogleden_sonra_aktivite,
    COUNT(CASE WHEN EXTRACT(HOUR FROM (a.data->>'CREATED')::timestamp) >= 18 
               THEN 1 END) as mesai_disi_aktivite,
    
    -- Verimlilik skoru (aktivite / aktif gün)
    ROUND(COUNT(a.id)::numeric / 
          NULLIF(COUNT(DISTINCT DATE((a.data->>'CREATED')::timestamp)), 0), 1) 
          as gunluk_verimlilik_skoru,
    
    -- Son aktivite
    MAX((a.data->>'CREATED')::timestamp) as son_aktivite,
    EXTRACT(DAY FROM NOW() - MAX((a.data->>'CREATED')::timestamp)) as son_aktivite_once_gun

FROM bitrix.users u
LEFT JOIN bitrix.activities a 
    ON a.data->>'RESPONSIBLE_ID' = u.data->>'ID'
    AND (a.data->>'CREATED')::timestamp > NOW() - INTERVAL '30 days'
WHERE u.data->>'ACTIVE' = 'true'
GROUP BY u.id, u.data->>'NAME'
ORDER BY gunluk_verimlilik_skoru DESC NULLS LAST;
```

**Ölçütler:**
- ✅ Aktif çalışma günü sayısı
- ✅ Günlük verimlilik skoru
- ✅ Mesai saatleri dağılımı
- ✅ Mesai dışı çalışma oranı
- ✅ İş-yaşam dengesi göstergesi

---

## 🎯 6. HEDEF BAZLI PERFORMANS

### F. Hedef Takibi (KPI)
**Veri Kaynakları:** `deals`, `users`

```sql
-- Aylık hedef performansı (örnek hedef: 100,000 TL/ay)
WITH monthly_targets AS (
    SELECT 
        u.data->>'ID' as user_id,
        u.data->>'NAME' as personel,
        100000 as aylik_hedef, -- Hedef tutar
        
        SUM(CASE 
            WHEN d.data->>'STAGE_ID' LIKE '%WON%' 
            AND DATE_TRUNC('month', (d.data->>'CLOSEDATE')::timestamp) = DATE_TRUNC('month', NOW())
            THEN (d.data->>'OPPORTUNITY')::numeric 
            ELSE 0 
        END) as bu_ay_gelir,
        
        SUM(CASE 
            WHEN d.data->>'STAGE_ID' LIKE '%WON%' 
            AND DATE_TRUNC('month', (d.data->>'CLOSEDATE')::timestamp) = DATE_TRUNC('month', NOW()) - INTERVAL '1 month'
            THEN (d.data->>'OPPORTUNITY')::numeric 
            ELSE 0 
        END) as gecen_ay_gelir
        
    FROM bitrix.users u
    LEFT JOIN bitrix.deals d ON d.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
    WHERE u.data->>'ACTIVE' = 'true'
    GROUP BY u.data->>'ID', u.data->>'NAME'
)
SELECT 
    personel,
    aylik_hedef,
    bu_ay_gelir,
    ROUND(100.0 * bu_ay_gelir / NULLIF(aylik_hedef, 0), 1) as hedef_gerceklesme_yuzdesi,
    bu_ay_gelir - aylik_hedef as hedeften_fark,
    gecen_ay_gelir,
    ROUND(100.0 * (bu_ay_gelir - gecen_ay_gelir) / NULLIF(gecen_ay_gelir, 0), 1) as buyume_yuzdesi,
    
    CASE 
        WHEN bu_ay_gelir >= aylik_hedef THEN '✅ Hedef aşıldı'
        WHEN bu_ay_gelir >= aylik_hedef * 0.8 THEN '⚠️ Hedefe yakın'
        ELSE '❌ Hedefin altında'
    END as durum
    
FROM monthly_targets
ORDER BY hedef_gerceklesme_yuzdesi DESC NULLS LAST;
```

**Ölçütler:**
- ✅ Aylık satış hedefi gerçekleşme oranı
- ✅ Önceki ay karşılaştırması
- ✅ Yıllık büyüme oranı
- ✅ Hedeften sapma (pozitif/negatif)
- ✅ Performans trendi

---

## 📊 7. MÜŞTERİ İLİŞKİLERİ KALİTESİ

### G. Müşteri Memnuniyeti Göstergeleri
**Veri Kaynakları:** `contacts`, `deals`, `activities`, `users`

```sql
-- Müşteri ilişkileri kalitesi
SELECT 
    u.data->>'NAME' as personel,
    
    -- Müşteri sayıları
    COUNT(DISTINCT c.id) as toplam_musteri,
    COUNT(DISTINCT CASE 
        WHEN a.updated_at > NOW() - INTERVAL '30 days' 
        THEN c.id 
    END) as aktif_musteri_30gun,
    
    -- İletişim sıklığı
    COUNT(a.id) / NULLIF(COUNT(DISTINCT c.id), 0) as musteri_basina_aktivite,
    
    -- Tekrar eden müşteri oranı
    ROUND(100.0 * COUNT(DISTINCT CASE 
        WHEN deal_count.count > 1 THEN c.id 
    END) / NULLIF(COUNT(DISTINCT c.id), 0), 2) as tekrar_musteri_orani,
    
    -- Ortalama müşteri değeri
    AVG(customer_value.total_value) as ortalama_musteri_degeri,
    
    -- Müşteri kaybı (90 gün iletişimsiz)
    COUNT(DISTINCT CASE 
        WHEN a.updated_at < NOW() - INTERVAL '90 days' 
        OR a.id IS NULL 
        THEN c.id 
    END) as kayip_risk_musteri

FROM bitrix.users u
LEFT JOIN bitrix.contacts c ON c.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
LEFT JOIN bitrix.activities a 
    ON a.data->>'OWNER_ID' = c.data->>'ID' 
    AND a.data->>'OWNER_TYPE_ID' = '3'
LEFT JOIN LATERAL (
    SELECT COUNT(*) as count
    FROM bitrix.deals d
    WHERE d.data->>'CONTACT_ID' = c.data->>'ID'
) deal_count ON true
LEFT JOIN LATERAL (
    SELECT SUM((d.data->>'OPPORTUNITY')::numeric) as total_value
    FROM bitrix.deals d
    WHERE d.data->>'CONTACT_ID' = c.data->>'ID'
      AND d.data->>'STAGE_ID' LIKE '%WON%'
) customer_value ON true
WHERE u.data->>'ACTIVE' = 'true'
GROUP BY u.id, u.data->>'NAME'
ORDER BY ortalama_musteri_degeri DESC NULLS LAST;
```

**Ölçütler:**
- ✅ Aktif müşteri sayısı
- ✅ Müşteri başına aktivite (iletişim sıklığı)
- ✅ Tekrar eden müşteri oranı
- ✅ Ortalama müşteri değeri (LTV)
- ✅ Müşteri kaybı riski
- ✅ Müşteri portföy büyüklüğü

---

## 🏆 8. PERFORMANS SKORLAMA SİSTEMİ

### H. Genel Performans Puanı
**Ağırlıklı skorlama sistemi**

```sql
-- Kapsamlı performans skoru (0-100)
WITH performance_metrics AS (
    SELECT 
        u.data->>'ID' as user_id,
        u.data->>'NAME' as personel,
        
        -- Satış skoru (40%)
        LEAST(100, (COUNT(DISTINCT CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' THEN d.id END) * 5)) as satis_skoru,
        
        -- Görev skoru (30%)
        COALESCE(ROUND(100.0 * COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END) / 
                 NULLIF(COUNT(t.id), 0)), 0) as gorev_skoru,
        
        -- Aktivite skoru (20%)
        LEAST(100, (COUNT(a.id) / 2)) as aktivite_skoru,
        
        -- Zamanında teslimat skoru (10%)
        COALESCE(ROUND(100.0 * COUNT(CASE 
            WHEN t.data->>'STATUS' = '5' 
            AND (t.data->>'CLOSED_DATE')::timestamp <= (t.data->>'DEADLINE')::timestamp 
            THEN 1 END) / NULLIF(COUNT(CASE WHEN t.data->>'STATUS' = '5' THEN 1 END), 0)), 0) 
            as zamaninda_teslimat_skoru
        
    FROM bitrix.users u
    LEFT JOIN bitrix.deals d ON d.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
    LEFT JOIN bitrix.tasks t ON t.data->>'RESPONSIBLE_ID' = u.data->>'ID'
    LEFT JOIN bitrix.activities a 
        ON a.data->>'RESPONSIBLE_ID' = u.data->>'ID'
        AND (a.data->>'CREATED')::timestamp > NOW() - INTERVAL '30 days'
    WHERE u.data->>'ACTIVE' = 'true'
    GROUP BY u.data->>'ID', u.data->>'NAME'
)
SELECT 
    personel,
    satis_skoru,
    gorev_skoru,
    aktivite_skoru,
    zamaninda_teslimat_skoru,
    
    -- Toplam performans skoru (ağırlıklı ortalama)
    ROUND(
        (satis_skoru * 0.40) + 
        (gorev_skoru * 0.30) + 
        (aktivite_skoru * 0.20) + 
        (zamaninda_teslimat_skoru * 0.10)
    , 1) as toplam_performans_skoru,
    
    CASE 
        WHEN ROUND((satis_skoru * 0.40) + (gorev_skoru * 0.30) + (aktivite_skoru * 0.20) + (zamaninda_teslimat_skoru * 0.10), 1) >= 80 
            THEN '⭐⭐⭐ Mükemmel'
        WHEN ROUND((satis_skoru * 0.40) + (gorev_skoru * 0.30) + (aktivite_skoru * 0.20) + (zamaninda_teslimat_skoru * 0.10), 1) >= 60 
            THEN '⭐⭐ İyi'
        WHEN ROUND((satis_skoru * 0.40) + (gorev_skoru * 0.30) + (aktivite_skoru * 0.20) + (zamaninda_teslimat_skoru * 0.10), 1) >= 40 
            THEN '⭐ Orta'
        ELSE '❌ Geliştirilmeli'
    END as performans_seviyesi
    
FROM performance_metrics
ORDER BY toplam_performans_skoru DESC;
```

**Skorlama Kriterleri:**
- 🔵 **Satış Skoru (40%)**: Deal sayısı ve kazanma oranı
- 🟢 **Görev Skoru (30%)**: Task tamamlama oranı
- 🟡 **Aktivite Skoru (20%)**: Günlük müşteri etkileşimi
- 🟣 **Zamanında Teslimat (10%)**: Deadline uyumu

**Performans Seviyeleri:**
- ⭐⭐⭐ Mükemmel: 80-100 puan
- ⭐⭐ İyi: 60-79 puan
- ⭐ Orta: 40-59 puan
- ❌ Geliştirilmeli: 0-39 puan

---

## 📈 9. TREND ANALİZİ & PROJEKSIYONLAR

### I. Büyüme ve Gelişim Analizi

```sql
-- Aylık performans trendi (son 6 ay)
WITH monthly_perf AS (
    SELECT 
        u.data->>'NAME' as personel,
        DATE_TRUNC('month', (d.data->>'CLOSEDATE')::timestamp) as ay,
        COUNT(DISTINCT d.id) as deal_sayisi,
        SUM((d.data->>'OPPORTUNITY')::numeric) as gelir
    FROM bitrix.users u
    JOIN bitrix.deals d ON d.data->>'ASSIGNED_BY_ID' = u.data->>'ID'
    WHERE (d.data->>'CLOSEDATE')::timestamp > NOW() - INTERVAL '6 months'
      AND d.data->>'STAGE_ID' LIKE '%WON%'
    GROUP BY u.data->>'NAME', DATE_TRUNC('month', (d.data->>'CLOSEDATE')::timestamp)
)
SELECT 
    personel,
    MAX(CASE WHEN ay = DATE_TRUNC('month', NOW()) - INTERVAL '5 months' THEN gelir END) as ay_1,
    MAX(CASE WHEN ay = DATE_TRUNC('month', NOW()) - INTERVAL '4 months' THEN gelir END) as ay_2,
    MAX(CASE WHEN ay = DATE_TRUNC('month', NOW()) - INTERVAL '3 months' THEN gelir END) as ay_3,
    MAX(CASE WHEN ay = DATE_TRUNC('month', NOW()) - INTERVAL '2 months' THEN gelir END) as ay_4,
    MAX(CASE WHEN ay = DATE_TRUNC('month', NOW()) - INTERVAL '1 month' THEN gelir END) as ay_5,
    MAX(CASE WHEN ay = DATE_TRUNC('month', NOW()) THEN gelir END) as bu_ay,
    
    -- Trend hesaplama
    CASE 
        WHEN AVG(gelir) OVER (PARTITION BY personel ORDER BY ay ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) > 
             AVG(gelir) OVER (PARTITION BY personel ORDER BY ay ROWS BETWEEN 5 PRECEDING AND 3 PRECEDING)
        THEN '📈 Yükseliş'
        ELSE '📉 Düşüş'
    END as trend
FROM monthly_perf
GROUP BY personel
ORDER BY bu_ay DESC NULLS LAST;
```

---

## 🎯 10. AKSİYON ÖNERİLERİ

### J. Otomatik Öneriler

```sql
-- Performans iyileştirme önerileri
SELECT 
    u.data->>'NAME' as personel,
    CASE 
        WHEN lead_conversion < 15 THEN '⚠️ Lead dönüşümü düşük - eğitim gerekli'
        WHEN deal_win_rate < 25 THEN '⚠️ Deal kazanma oranı düşük - mentorluk önerilir'
        WHEN avg_activities_per_day < 5 THEN '⚠️ Aktivite sayısı düşük - daha fazla müşteri etkileşimi gerekli'
        WHEN overdue_tasks > 10 THEN '⚠️ Çok fazla geciken görev - zaman yönetimi gerekli'
        WHEN last_activity_days > 7 THEN '⚠️ Uzun süredir aktivite yok - takip gerekli'
        ELSE '✅ Performans normal seviyelerde'
    END as oneri,
    
    lead_conversion,
    deal_win_rate,
    avg_activities_per_day,
    overdue_tasks,
    last_activity_days
    
FROM (
    SELECT 
        u.data->>'NAME',
        -- Metrikler buraya
    FROM bitrix.users u
    -- ...
) metrics
WHERE oneri != '✅ Performans normal seviyelerde'
ORDER BY personel;
```

---

## 📊 ÖZET: ANALİZ ÖLÇÜTLERİ TABLOSU

| Kategori | Temel Ölçütler | Hedef Değerler |
|----------|---------------|----------------|
| **Satış** | Lead dönüşüm, Deal kazanma, Gelir | >%20, >%30, Hedef tutara göre |
| **Görevler** | Tamamlama oranı, Zamanında teslimat | >%80, >%70 |
| **Aktivite** | Günlük aktivite, Müşteri etkileşimi | >8/gün, >3/müşteri |
| **Müşteri İlişkileri** | Aktif müşteri, Tekrar oranı | >20, >%30 |
| **Zaman Yönetimi** | Aktif gün, Verimlilik skoru | >20/ay, >8 |
| **Hedef Takibi** | Hedef gerçekleşme, Büyüme | >%90, >%10 |
| **Performans Skoru** | Toplam puan | >60 (İyi), >80 (Mükemmel) |

---

## 🚀 SONRAKI ADIMLAR

1. **Users tablosunu ekle** - Personel bilgileri için
2. **Departments tablosunu ekle** - Departman analizleri için
3. **Dashboard oluştur** - Power BI, Grafana veya custom web app
4. **Otomatik raporlar** - Haftalık/aylık email raporları
5. **Gamification** - Performans liderlik tablosu
6. **Erken uyarı sistemi** - Performans düşüşünde otomatik bildirim

Bu ölçütlerle çalışan performansını 360 derece analiz edebilirsiniz! 🎯
