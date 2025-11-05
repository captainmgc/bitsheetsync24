# 📊 Bitrix24 Veri Analiz Fırsatları

Şu an **leads, contacts, deals, activities** tablolarını senkronize ediyoruz. İşte analiz edebileceğimiz ek veri kaynakları:

## 🎯 Öncelikli Tablolar (Hemen Eklenebilir)

### 1. 🏢 **Companies (Şirketler)** - 21 method
**Kullanım Amacı:**
- B2B müşteri analizi
- Şirket bazlı satış performansı
- Kurumsal müşteri segmentasyonu
- Contact-Company ilişkisi analizi

**Önemli Alanlar:**
- `TITLE`, `COMPANY_TYPE`, `INDUSTRY`, `EMPLOYEES`
- `REVENUE`, `CURRENCY_ID`, `ASSIGNED_BY_ID`
- `DATE_CREATE`, `DATE_MODIFY`

**Analiz Örnekleri:**
```sql
-- En çok contact'a sahip şirketler
SELECT 
    c.data->>'TITLE' as company,
    COUNT(DISTINCT con.id) as contact_count
FROM bitrix.companies c
LEFT JOIN bitrix.contacts con ON con.data->>'COMPANY_ID' = c.data->>'ID'
GROUP BY c.id, c.data->>'TITLE'
ORDER BY contact_count DESC;

-- Sektör bazlı deal dağılımı
SELECT 
    comp.data->>'INDUSTRY' as industry,
    COUNT(d.id) as deal_count,
    SUM((d.data->>'OPPORTUNITY')::numeric) as total_revenue
FROM bitrix.companies comp
LEFT JOIN bitrix.deals d ON d.data->>'COMPANY_ID' = comp.data->>'ID'
GROUP BY comp.data->>'INDUSTRY';
```

---

### 2. 📦 **Products (Ürünler)** - 15 method
**Kullanım Amacı:**
- Ürün bazlı satış analizi
- En çok satan ürünler
- Fiyat analizi
- Stok takibi

**Önemli Alanlar:**
- `NAME`, `PRICE`, `CURRENCY_ID`, `ACTIVE`
- `SECTION_ID` (kategori), `QUANTITY`, `MEASURE`

**Analiz Örnekleri:**
```sql
-- En çok satılan ürünler (productrow'dan)
SELECT 
    p.data->>'NAME' as product,
    COUNT(*) as sales_count,
    SUM((pr.data->>'QUANTITY')::numeric) as total_quantity,
    SUM((pr.data->>'PRICE')::numeric) as total_revenue
FROM bitrix.productrows pr
JOIN bitrix.products p ON pr.data->>'PRODUCT_ID' = p.data->>'ID'
GROUP BY p.id, p.data->>'NAME'
ORDER BY total_revenue DESC;
```

---

### 3. 📊 **Product Rows (Satış Kalemleri)** - 6 method
**Kullanım Amacı:**
- Deal/Invoice'lardaki satılan ürünler
- Ürün kombinasyon analizi
- Ortalama sepet büyüklüğü
- Cross-sell/upsell fırsatları

**Önemli Alanlar:**
- `PRODUCT_ID`, `PRODUCT_NAME`, `PRICE`, `QUANTITY`
- `DISCOUNT_RATE`, `TAX_RATE`, `MEASURE_NAME`
- `OWNER_TYPE` (D=Deal, I=Invoice), `OWNER_ID`

**Analiz Örnekleri:**
```sql
-- Birlikte satılan ürünler
SELECT 
    pr1.data->>'PRODUCT_NAME' as product1,
    pr2.data->>'PRODUCT_NAME' as product2,
    COUNT(*) as times_sold_together
FROM bitrix.productrows pr1
JOIN bitrix.productrows pr2 
    ON pr1.data->>'OWNER_ID' = pr2.data->>'OWNER_ID'
    AND pr1.data->>'OWNER_TYPE' = pr2.data->>'OWNER_TYPE'
    AND pr1.id < pr2.id
GROUP BY product1, product2
ORDER BY times_sold_together DESC;
```

---

### 4. 🧾 **Invoices (Faturalar)** - 25 method
**Kullanım Amacı:**
- Gelir analizi
- Ödeme takibi
- Tahsilat performansı
- Vergi raporları

**Önemli Alanlar:**
- `ORDER_TOPIC`, `STATUS_ID`, `PRICE`, `CURRENCY`
- `PAY_SYSTEM_ID`, `DATE_BILL`, `DATE_PAY_BEFORE`
- `UF_DEAL_ID`, `UF_COMPANY_ID`, `UF_CONTACT_ID`

**Analiz Örnekleri:**
```sql
-- Aylık gelir trendi
SELECT 
    DATE_TRUNC('month', (data->>'DATE_BILL')::timestamp) as month,
    COUNT(*) as invoice_count,
    SUM((data->>'PRICE')::numeric) as total_revenue,
    AVG((data->>'PRICE')::numeric) as avg_invoice_value
FROM bitrix.invoices
WHERE data->>'STATUS_ID' = 'P' -- Paid
GROUP BY month
ORDER BY month DESC;
```

---

### 5. 📄 **Quotes (Teklifler)** - 19 method
**Kullanım Amacı:**
- Teklif kabul oranı analizi
- Teklif-Deal dönüşüm analizi
- Ortalama teklif süresi
- En başarılı teklif şablonları

**Önemli Alanlar:**
- `TITLE`, `STATUS_ID`, `OPPORTUNITY`, `CURRENCY_ID`
- `DEAL_ID`, `LEAD_ID`, `CONTACT_ID`, `COMPANY_ID`
- `BEGINDATE`, `CLOSEDATE`

---

### 6. ⏱️ **Timeline (Zaman Çizelgesi)** - 4 method
**Kullanım Amacı:**
- Müşteri etkileşim geçmişi
- Aktivite feed
- Değişiklik takibi
- Audit trail

**Önemli Alanlar:**
- `ENTITY_ID`, `ENTITY_TYPE`, `TYPE_ID`, `CREATED`
- `AUTHOR_ID`, `COMMENT`, `ASSOCIATED_ENTITY_ID`

---

## 📈 İleri Seviye Analizler

### 7. 💱 **Currency (Para Birimleri)** - 12 method
- Döviz kuru geçmişi
- Multi-currency gelir raporları
- Kur etkisi analizi

### 8. 🏷️ **Status (Durum Listeleri)** - 9 method
- Lead/Deal funnel tanımları
- Pipeline aşama dağılımı
- Durum bazlı dönüşüm oranları

### 9. 📋 **Requisite (Fatura Bilgileri)** - 36 method
- Vergi numarası takibi
- Şirket yasal bilgileri
- Fatura adres bilgileri

### 10. 📍 **Address (Adresler)** - 7 method
- Coğrafi satış analizi
- Bölgesel performans
- Müşteri dağılım haritası

---

## 🎨 Özel Analizler

### A. Satış Funnel Analizi
**Gerekli Tablolar:** leads, contacts, deals, activities, timeline
```sql
-- Lead'den Deal'e dönüşüm hunisi
WITH funnel AS (
  SELECT 
    COUNT(DISTINCT l.id) as total_leads,
    COUNT(DISTINCT CASE WHEN d.id IS NOT NULL THEN l.id END) as converted_leads,
    COUNT(DISTINCT d.id) as total_deals,
    COUNT(DISTINCT CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' THEN d.id END) as won_deals
  FROM bitrix.leads l
  LEFT JOIN bitrix.deals d ON d.data->>'LEAD_ID' = l.data->>'ID'
)
SELECT 
  total_leads,
  converted_leads,
  ROUND(100.0 * converted_leads / total_leads, 2) as lead_conversion_rate,
  total_deals,
  won_deals,
  ROUND(100.0 * won_deals / total_deals, 2) as deal_win_rate
FROM funnel;
```

### B. Satış Performansı Analizi
**Gerekli Tablolar:** deals, products, productrows, users
```sql
-- Satış temsilcisi performansı
SELECT 
    d.data->>'ASSIGNED_BY_ID' as sales_rep_id,
    COUNT(*) as deal_count,
    COUNT(CASE WHEN d.data->>'STAGE_ID' LIKE '%WON%' THEN 1 END) as won_deals,
    SUM((d.data->>'OPPORTUNITY')::numeric) as total_revenue,
    AVG(
        EXTRACT(DAY FROM 
            (d.data->>'CLOSEDATE')::timestamp - (d.data->>'DATE_CREATE')::timestamp
        )
    ) as avg_days_to_close
FROM bitrix.deals d
GROUP BY d.data->>'ASSIGNED_BY_ID'
ORDER BY total_revenue DESC;
```

### C. Müşteri Aktivite Skoru
**Gerekli Tablolar:** contacts, activities, deals, timeline
```sql
-- Aktif/pasif müşteri segmentasyonu
SELECT 
    c.data->>'NAME' as contact_name,
    COUNT(DISTINCT a.id) as activity_count,
    COUNT(DISTINCT d.id) as deal_count,
    MAX(a.updated_at) as last_activity_date,
    CASE 
        WHEN MAX(a.updated_at) > NOW() - INTERVAL '30 days' THEN 'Active'
        WHEN MAX(a.updated_at) > NOW() - INTERVAL '90 days' THEN 'Warm'
        ELSE 'Cold'
    END as customer_status
FROM bitrix.contacts c
LEFT JOIN bitrix.activities a ON a.data->>'OWNER_ID' = c.data->>'ID' AND a.data->>'OWNER_TYPE_ID' = '3'
LEFT JOIN bitrix.deals d ON d.data->>'CONTACT_ID' = c.data->>'ID'
GROUP BY c.id, c.data->>'NAME';
```

### D. Ürün Affinity Analizi
**Gerekli Tablolar:** productrows, products, deals
```sql
-- Hangi ürünler birlikte satılıyor?
SELECT 
    p1.data->>'NAME' as product_a,
    p2.data->>'NAME' as product_b,
    COUNT(DISTINCT pr1.data->>'OWNER_ID') as co_occurrence_count,
    ROUND(
        100.0 * COUNT(DISTINCT pr1.data->>'OWNER_ID') / 
        (SELECT COUNT(DISTINCT data->>'OWNER_ID') FROM bitrix.productrows WHERE data->>'PRODUCT_ID' = p1.data->>'ID'),
        2
    ) as lift_percentage
FROM bitrix.productrows pr1
JOIN bitrix.productrows pr2 
    ON pr1.data->>'OWNER_ID' = pr2.data->>'OWNER_ID'
    AND pr1.data->>'OWNER_TYPE' = pr2.data->>'OWNER_TYPE'
    AND pr1.data->>'PRODUCT_ID' < pr2.data->>'PRODUCT_ID'
JOIN bitrix.products p1 ON pr1.data->>'PRODUCT_ID' = p1.data->>'ID'
JOIN bitrix.products p2 ON pr2.data->>'PRODUCT_ID' = p2.data->>'ID'
GROUP BY p1.id, p2.id, p1.data->>'NAME', p2.data->>'NAME'
HAVING COUNT(DISTINCT pr1.data->>'OWNER_ID') > 5
ORDER BY co_occurrence_count DESC;
```

---

## 🚀 Önerilen Uygulama Sırası

### Faz 1: Temel Genişletme (1-2 hafta)
1. ✅ **Companies** ekle (B2B analizi için kritik)
2. ✅ **Products** + **ProductRows** ekle (ürün analizi)
3. ✅ **Invoices** ekle (gelir takibi)

### Faz 2: İleri Analiz (2-4 hafta)
4. ✅ **Quotes** ekle (teklif kabul oranı)
5. ✅ **Timeline** ekle (müşteri etkileşim geçmişi)
6. ✅ **Status** ekle (funnel tanımları)

### Faz 3: Optimizasyon (sürekli)
7. ✅ Dashboard'lar oluştur
8. ✅ Otomatik raporlar
9. ✅ Makine öğrenmesi modelleri
10. ✅ Predictive analytics

---

## 💡 Önemli Notlar

**Artırımlı Sync Desteği:**
- Companies: `DATE_CREATE`, `DATE_MODIFY` ✅
- Products: `TIMESTAMP_X` ✅
- Invoices: `DATE_INSERT`, `DATE_UPDATE` ✅
- Quotes: `DATE_CREATE`, `DATE_MODIFY` ✅

**İlişkiler:**
```
Lead → Contact → Company
        ↓
      Deal → ProductRows → Products
        ↓
    Invoice → ProductRows → Products
        ↓
      Quote
```

**Veri Boyutları (Tahmini):**
- Companies: ~5,000 (contact sayısının %17'si)
- Products: ~500-2,000
- ProductRows: ~50,000-100,000 (deal/invoice başına 2-3 ürün)
- Invoices: ~20,000 (deal sayısının %70'i)
- Quotes: ~30,000 (deal sayısının %100'ü)

---

## 🎯 Sonraki Adım

Hangi tabloları eklemek istersiniz? Önerim:

```bash
# 1. Companies ekle
python add_entity.py companies

# 2. Products + ProductRows ekle
python add_entity.py products
python add_entity.py productrows

# 3. Invoices ekle
python add_entity.py invoices
```

Veya hepsini bir script ile:
```bash
./expand_crm_data.sh
```

Bu tablolar eklendiğinde çok daha zengin analizler yapabilirsiniz! 🚀
