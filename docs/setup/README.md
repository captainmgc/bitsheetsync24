# BitSheet24 - Python + PostgreSQL Projesi

## 📋 Proje Yapısı

```
bitsheet24/
├── venv/                    # Python sanal ortamı
├── src/                     # Ana kaynak kodu
│   ├── __init__.py
│   ├── config.py           # Ayar dosyası
│   ├── models.py           # Veritabanı modelleri
│   └── main.py             # Ana uygulama
├── tests/                  # Test dosyaları
├── .env                    # Ortam değişkenleri (GIT'te yok)
├── requirements.txt        # Python bağımlılıkları
├── test_db.py             # PostgreSQL bağlantı testi
├── test_sqlalchemy.py     # SQLAlchemy testi
# Bitrix24 Sync Service

Bitrix24 CRM verilerini PostgreSQL veritabanına sürekli olarak senkronize eden daemon servisi.

## 🚀 Özellikler

- ✅ Sürekli çalışan systemd servisi
- ✅ Artırımlı senkronizasyon (sadece değişen kayıtlar)
- ✅ Otomatik yeniden başlatma (çökme durumunda)
- ✅ Detaylı loglama
- ✅ Graceful shutdown (sinyal kontrolü)
- ✅ Kaynak sınırlamaları (Memory, CPU)

## 📦 Desteklenen Tablolar

| Tablo | Senkronizasyon | Filtre Alanları |
|-------|----------------|-----------------|
| leads | Artırımlı | DATE_CREATE, DATE_MODIFY |
| contacts | Artırımlı | DATE_CREATE, DATE_MODIFY |
| deals | Artırımlı | DATE_CREATE, DATE_MODIFY |
| activities | Artırımlı | CREATED, LAST_UPDATED |
| tasks | Full sync | (artırımlı geliştiriliyor) |

## 🔧 Kurulum

### 1. Bağımlılıkları Yükle

```bash
# PostgreSQL kurulu olmalı
sudo apt-get install postgresql postgresql-contrib

# Python bağımlılıkları
cd /home/captain/bitsheet24
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Veritabanı Konfigürasyonu

`.env` dosyasını düzenle:
```bash
BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.com/rest/1/your-webhook-key/
DATABASE_URL=postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db
```

### 3. İlk Full Sync

```bash
# Tüm tabloları ilk kez senkronize et
python sync_bitrix.py all

# Veya teker teker
python sync_bitrix.py leads
python sync_bitrix.py contacts
python sync_bitrix.py deals
python sync_bitrix.py activities
```

### 4. Servisi Kur

```bash
# Servisi systemd'ye kur ve başlat
sudo ./install_service.sh
```

## 📊 Kullanım

### Servis Komutları

```bash
# Servis durumunu kontrol et
sudo systemctl status bitrix-sync

# Logları takip et
sudo journalctl -u bitrix-sync -f

# Servisi durdur
sudo systemctl stop bitrix-sync

# Servisi başlat
sudo systemctl start bitrix-sync

# Servisi yeniden başlat
sudo systemctl restart bitrix-sync

# Servisi devre dışı bırak (otomatik başlatma)
sudo systemctl disable bitrix-sync

# Servisi kaldır
sudo ./uninstall_service.sh
```

### Manuel Sync

```bash
# Artırımlı sync (son sync'den bu yana değişenler)
python sync_bitrix.py all --incremental
python sync_bitrix.py leads --incremental

# Full sync (tüm kayıtlar)
python sync_bitrix.py all
python sync_bitrix.py contacts

# Test için limit ile
python sync_bitrix.py deals --incremental --limit 10
```

## ⚙️ Konfigürasyon

### Sync Aralığını Değiştir

`bitrix_sync_daemon.py` dosyasında:
```python
SYNC_INTERVAL_SECONDS = 600  # 10 dakika (varsayılan)
```

Değiştirdikten sonra servisi yeniden başlat:
```bash
sudo systemctl restart bitrix-sync
```

### Log Seviyesini Değiştir

`bitrix_sync_daemon.py` dosyasında:
```python
logging.basicConfig(
    level=logging.INFO,  # DEBUG, INFO, WARNING, ERROR
    ...
)
```

## 📁 Dosya Yapısı

```
bitsheet24/
├── bitrix_sync_daemon.py      # Ana daemon script
├── sync_bitrix.py              # Manuel sync CLI
├── bitrix-sync.service         # Systemd service tanımı
├── install_service.sh          # Kurulum scripti
├── uninstall_service.sh        # Kaldırma scripti
├── daemon.conf                 # Konfigürasyon (gelecekte kullanılacak)
├── logs/
│   └── sync_daemon.log         # Daemon logları
├── src/
│   ├── bitrix/
│   │   ├── client.py           # Bitrix24 API istemcisi
│   │   └── ingestors/          # Tablo senkronizasyon modülleri
│   │       ├── leads.py
│   │       ├── contacts.py
│   │       ├── deals.py
│   │       ├── activities.py
│   │       └── tasks.py
│   └── storage.py              # Veritabanı işlemleri
└── .env                        # Ortam değişkenleri
```

## 🔍 Veritabanı Yapısı

### sync_state Tablosu

Her tablo için son senkronizasyon durumunu takip eder:

```sql
SELECT * FROM bitrix.sync_state;
```

| Sütun | Açıklama |
|-------|----------|
| entity | Tablo adı (leads, contacts, vb.) |
| last_sync_at | Son artırımlı sync zamanı |
| last_full_sync_at | Son full sync zamanı |
| record_count | Toplam kayıt sayısı |
| status | Durum (completed, running, failed) |
| error_message | Hata mesajı (varsa) |
| updated_at | Güncelleme zamanı |

### Veri Tabloları

Her tablo JSONB formatında orijinal Bitrix24 verisini saklar:

```sql
-- Örnek: Son 10 lead
SELECT 
    id, 
    data->>'TITLE' as title,
    data->>'STATUS_ID' as status,
    updated_at 
FROM bitrix.leads 
ORDER BY updated_at DESC 
LIMIT 10;

-- Örnek: Telefon numarası olan kişiler
SELECT 
    id,
    data->>'NAME' as name,
    data->'PHONE' as phones
FROM bitrix.contacts 
WHERE data->'PHONE' IS NOT NULL;
```

## 🐛 Sorun Giderme

### Servis Başlamıyor

```bash
# Detaylı logları kontrol et
sudo journalctl -u bitrix-sync -n 100

# Veritabanı bağlantısını test et
python -c "from src.storage import get_engine; get_engine().connect()"

# Bitrix24 API'yi test et
python -c "from src.bitrix.client import BitrixClient; c = BitrixClient(); print(c.call('crm.lead.list', {'select': ['ID'], 'filter': {'ID': 1}}))"
```

### Memory/CPU Limiti

`bitrix-sync.service` dosyasında:
```ini
MemoryLimit=1G      # Hafıza limiti
CPUQuota=50%        # CPU kullanımı
```

### Sync Hataları

Logları kontrol et:
```bash
# Daemon logları
sudo journalctl -u bitrix-sync -f

# Veya dosyadan
tail -f logs/sync_daemon.log
```

## 📈 Performans

- **Artırımlı Sync**: ~1-5 saniye (değişiklik yoksa)
- **Full Sync**: 
  - leads: ~2 dk (7,685 kayıt)
  - contacts: ~5 dk (29,430 kayıt)
  - deals: ~4 dk (28,781 kayıt)
  - activities: ~8 dk (165,950 kayıt)

## 🔐 Güvenlik

- Service isolated environment'ta çalışır (`PrivateTmp=true`)
- Privilege escalation engellenir (`NoNewPrivileges=true`)
- Kaynak limitleri uygulanır (Memory, CPU)
- PostgreSQL şifresi `.env` dosyasında (600 permissions)

## 📝 Lisans

Bu proje şirket içi kullanım içindir.

## 🆘 Destek

Sorun bildirimi veya özellik isteği için:
- GitHub Issues: [bitsheetsync24/issues](https://github.com/captainmgc/bitsheetsync24/issues)
- Email: admin@example.com

```

## 🚀 Kurulum ve Kullanım

### 1. Sanal Ortamı Aktifleştir

```bash
source venv/bin/activate
```

### 2. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 3. PostgreSQL Servisi Çalışıyor mu Kontrol Et

```bash
sudo systemctl status postgresql
```

Eğer çalışmıyorsa başlat:
```bash
sudo systemctl start postgresql
```

### 4. Veritabanı Bağlantısını Test Et

```bash
python test_db.py          # psycopg2 ile test
python test_sqlalchemy.py  # SQLAlchemy ile test
```

## 🛠️ Kurulan Araçlar

### Sistem Paketleri
- **PostgreSQL 16.10** - Veritabanı sunucusu
- **PostgreSQL Client** - Komut satırı aracı (psql)
- **libpq-dev** - PostgreSQL C kütüphanesi
- **build-essential** - C++ derleyicileri
- **DBeaver Community** - GUI database client

### Python Paketleri
- **psycopg2-binary** - PostgreSQL adaptörü
- **SQLAlchemy** - ORM çerçevesi
- **Flask** - Web çerçevesi (isteğe bağlı)
- **Django** - Web çerçevesi (isteğe bağlı)
- **python-dotenv** - .env dosyası desteği

## 📚 Terminalde PostgreSQL Kullanımı

### psql ile Veritabanına Bağlan

```bash
# Yerel kullanıcı olarak bağlan
psql -U bitsheet -d bitsheet_db

# Şifreyle bağlan
psql -U bitsheet -d bitsheet_db -W

# Direkt SQL komutu çalıştır
psql -U bitsheet -d bitsheet_db -c "SELECT version();"
```

### Yaygın PostgreSQL Komutları

```sql
-- Veritabanlarını listele
\l

-- Mevcut veritabanı tablolarını listele
\dt

-- Tablo yapısını göster
\d table_name

-- Veritabanına bağlan
\c database_name

-- Kullanıcıları listele
\du

-- Veritabanından çık
\q

-- Komut satırında execute et
SELECT * FROM table_name;
```

## 🎨 GUI Araçları

### DBeaver ile Bağlantı

```bash
# Terminal'den başlat
dbeaver-ce

# veya Uygulama menüsünden DBeaver'ı aç
```

**Bağlantı Detayları:**
- **Host**: localhost
- **Port**: 5432
- **Database**: bitsheet_db
- **Username**: bitsheet
- **Password**: bitsheet123

## 📁 .env Dosyası

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bitsheet_db
DB_USER=bitsheet
DB_PASSWORD=bitsheet123
FLASK_ENV=development
DEBUG=True
```

## 🔐 PostgreSQL Kullanıcı Yönetimi

### Şifreyi Değiştir

```bash
sudo -u postgres psql -c "ALTER USER bitsheet WITH PASSWORD 'yeni_sifre';"
```

### Yeni Veritabanı Oluştur

```bash
sudo -u postgres createdb yeni_db -O bitsheet
```

### Yeni Kullanıcı Oluştur

```bash
sudo -u postgres createuser yeni_kullanici -P
```

## 📊 PostgreSQL Belgesi

PostgreSQL resmi belgesi: https://www.postgresql.org/docs/16/

Öne Çıkan Konular:
- [Veritabanı Yönetimi](https://www.postgresql.org/docs/16/managing-databases.html)
- [Tablo Oluşturma](https://www.postgresql.org/docs/16/sql-createtable.html)
- [SQL Komutları](https://www.postgresql.org/docs/16/sql-commands.html)

## ✅ Hızlı Başlangıç

1. **Sanal ortamı aktifleştir:**
   ```bash
   source venv/bin/activate
   ```

2. **PostgreSQL'i başlat:**
   ```bash
   sudo systemctl start postgresql
   ```

3. **Testleri çalıştır:**
   ```bash
   python test_db.py
   python test_sqlalchemy.py
   ```

4. **DBeaver'ı aç:**
   ```bash
   dbeaver-ce
   ```

5. **Geliştirmeye başla!** 🎉

## 📝 Notlar

- `.env` dosyasını GIT'e commit etmeyin (şifre içerir)
- `requirements.txt` her zaman güncel tutun: `pip freeze > requirements.txt`
- PostgreSQL servisini her sistem başlangıcında otomatik olarak başlatması için `systemctl enable` ayarlanmıştır

## 💡 İpuçları

- **Veritabanını sıfırla:** 
  ```bash
  sudo -u postgres dropdb bitsheet_db
  sudo -u postgres createdb bitsheet_db -O bitsheet
  ```

- **PostgreSQL loglama:**
  ```bash
  sudo tail -f /var/log/postgresql/postgresql-16-main.log
  ```

- **Tüm tabloları silmek:**
  ```sql
  DROP SCHEMA public CASCADE;
  CREATE SCHEMA public;
  ```

---

**Son Güncelleme:** 5 Kasım 2025
