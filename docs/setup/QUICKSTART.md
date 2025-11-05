# Bitrix24 Sync Service - Hızlı Başlangıç

## 📊 Güncel Durum

✅ **Servis aktif ve çalışıyor!**

- **Servis Adı**: `bitrix-sync`
- **Durum**: Active (running)
- **PID**: Otomatik atanır
- **Sync Aralığı**: Her 10 dakika (600 saniye)
- **Kaynak Limitleri**: 
  - Memory: 1GB max
  - CPU: %50 max

## 🎯 İlk Sync Sonuçları

```
Sync cycle #1 completed in 1.04 seconds
Total records synced: 12
Results: 
  - leads: 0 (değişiklik yok)
  - contacts: 1 (1 yeni/güncelleme)
  - deals: 4 (4 yeni/güncelleme)
  - activities: 7 (7 yeni/güncelleme)
```

## 📋 Temel Komutlar

### Servis Yönetimi
```bash
# Durumu kontrol et
sudo systemctl status bitrix-sync

# Durdur
sudo systemctl stop bitrix-sync

# Başlat
sudo systemctl start bitrix-sync

# Yeniden başlat
sudo systemctl restart bitrix-sync

# Otomatik başlatmayı kapat
sudo systemctl disable bitrix-sync

# Otomatik başlatmayı aç
sudo systemctl enable bitrix-sync
```

### Log İzleme
```bash
# Canlı log takibi (Ctrl+C ile çık)
sudo journalctl -u bitrix-sync -f

# Son 50 satır
sudo journalctl -u bitrix-sync -n 50

# Bugünkü loglar
sudo journalctl -u bitrix-sync --since today

# Belirli tarih aralığı
sudo journalctl -u bitrix-sync --since "2025-11-05 10:00" --until "2025-11-05 18:00"

# Dosya logu
tail -f /home/captain/bitsheet24/logs/sync_daemon.log
```

### Manuel Sync (Servisten bağımsız)
```bash
cd /home/captain/bitsheet24
source venv/bin/activate

# Artırımlı sync
python sync_bitrix.py all --incremental

# Full sync
python sync_bitrix.py all

# Tek tablo
python sync_bitrix.py leads --incremental
```

## 🔧 Konfigürasyon Değişiklikleri

### Sync Aralığını Değiştir

1. Daemon dosyasını düzenle:
```bash
nano /home/captain/bitsheet24/bitrix_sync_daemon.py
```

2. Bu satırı bul ve değiştir:
```python
SYNC_INTERVAL_SECONDS = 600  # 10 dakika
```

Örnek değerler:
- 300 = 5 dakika
- 600 = 10 dakika (varsayılan)
- 900 = 15 dakika
- 1800 = 30 dakika
- 3600 = 1 saat

3. Servisi yeniden başlat:
```bash
sudo systemctl restart bitrix-sync
```

### Log Seviyesini Değiştir

`bitrix_sync_daemon.py` içinde:
```python
logging.basicConfig(
    level=logging.INFO,  # DEBUG, INFO, WARNING, ERROR olabilir
    ...
)
```

DEBUG = En detaylı loglar
INFO = Normal loglar (varsayılan)
WARNING = Sadece uyarılar
ERROR = Sadece hatalar

## 📊 Veritabanı Sorgulama

### Sync Durumunu Kontrol Et
```sql
-- psql ile bağlan
psql "postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db"

-- Tüm tabloların sync durumu
SELECT 
    entity,
    to_char(last_sync_at, 'DD.MM.YYYY HH24:MI:SS') as last_sync,
    record_count,
    status
FROM bitrix.sync_state
ORDER BY entity;

-- Kayıt sayıları
SELECT 'leads' as tbl, count(*) FROM bitrix.leads
UNION ALL
SELECT 'contacts', count(*) FROM bitrix.contacts
UNION ALL
SELECT 'deals', count(*) FROM bitrix.deals
UNION ALL
SELECT 'activities', count(*) FROM bitrix.activities
ORDER BY tbl;
```

### Örnek Veri Sorguları
```sql
-- Son 10 lead
SELECT 
    id,
    data->>'TITLE' as title,
    data->>'STATUS_ID' as status,
    to_char(updated_at, 'DD.MM.YYYY HH24:MI') as updated
FROM bitrix.leads
ORDER BY updated_at DESC
LIMIT 10;

-- Telefonu olan kişiler
SELECT 
    id,
    data->>'NAME' as name,
    data->>'LAST_NAME' as surname,
    data->'PHONE' as phones
FROM bitrix.contacts
WHERE data->'PHONE' IS NOT NULL
LIMIT 10;

-- Aktif deallar
SELECT 
    id,
    data->>'TITLE' as title,
    data->>'STAGE_ID' as stage,
    data->>'OPPORTUNITY' as amount
FROM bitrix.deals
WHERE data->>'STAGE_ID' NOT LIKE '%WON%'
  AND data->>'STAGE_ID' NOT LIKE '%LOST%'
ORDER BY updated_at DESC
LIMIT 10;
```

## 🚨 Sorun Giderme

### Servis Çalışmıyor
```bash
# Detaylı durum
sudo systemctl status bitrix-sync -l

# Son 100 log satırı
sudo journalctl -u bitrix-sync -n 100

# Hata logları
sudo journalctl -u bitrix-sync -p err

# Manuel test
cd /home/captain/bitsheet24
source venv/bin/activate
python bitrix_sync_daemon.py
```

### Veritabanı Bağlantı Hatası
```bash
# Bağlantıyı test et
python -c "from src.storage import get_engine; get_engine().connect(); print('OK')"

# PostgreSQL çalışıyor mu?
sudo systemctl status postgresql

# PostgreSQL başlat
sudo systemctl start postgresql
```

### Bitrix24 API Hatası
```bash
# API'yi test et
python -c "
from src.bitrix.client import BitrixClient
c = BitrixClient()
result = c.call('crm.lead.list', {'select': ['ID'], 'filter': {'ID': 1}})
print('OK' if result else 'FAIL')
"
```

### Yüksek Memory/CPU Kullanımı
```bash
# Kaynak kullanımını kontrol et
systemctl show bitrix-sync | grep -E "Memory|CPU"

# Limit değiştir (/etc/systemd/system/bitrix-sync.service)
sudo nano /etc/systemd/system/bitrix-sync.service

# MemoryLimit=1G  -> 512M yapabilirsin
# CPUQuota=50%    -> 25% yapabilirsin

# Değişiklikleri uygula
sudo systemctl daemon-reload
sudo systemctl restart bitrix-sync
```

## 🔄 Servis Güncelleme

Kod değişikliği yaptıktan sonra:
```bash
# Servisi durdur
sudo systemctl stop bitrix-sync

# (Kod değişikliklerini yap)

# Servisi başlat
sudo systemctl start bitrix-sync

# Veya direkt restart
sudo systemctl restart bitrix-sync
```

## 🗑️ Servisi Kaldırma

```bash
cd /home/captain/bitsheet24
sudo ./uninstall_service.sh
```

## 📈 Performans İpuçları

1. **Sync aralığını ayarla**: Veri değişim sıklığına göre 5-30 dakika arası seç
2. **Gereksiz tabloları kapat**: `bitrix_sync_daemon.py` içinde sadece ihtiyacın olan tabloları sync et
3. **Log seviyesini düşür**: Production'da INFO veya WARNING kullan
4. **Veritabanı indexleri**: JSONB alanları için GIN index ekle

## 💡 İpuçları

- Servis her 10 dakikada otomatik çalışır
- System reboot sonrası otomatik başlar
- Hata durumunda 10 saniye sonra otomatik yeniden başlar
- Loglar hem journald hem de dosyaya yazılır
- Graceful shutdown destekler (Ctrl+C ile güvenli kapanır)

## 📞 Destek

Sorun yaşarsan:
1. Logları kontrol et: `sudo journalctl -u bitrix-sync -n 100`
2. Manuel test yap: `python sync_bitrix.py all --incremental`
3. Veritabanını kontrol et: sync_state tablosuna bak
4. Servis durumunu kontrol et: `sudo systemctl status bitrix-sync`

---
**Son Güncelleme**: 5 Kasım 2025
**Sürüm**: 1.0.0
