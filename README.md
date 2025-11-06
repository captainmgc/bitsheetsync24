# BitSheet24 - Bitrix24 → Google Sheets Export System

**Sürekli çalışan artırımlı senkronizasyon ile Bitrix24 CRM verilerinizi PostgreSQL'de saklayın ve Google Sheets'e aktarın.**

## 🎯 Ana Özellikler

- ✅ **Sürekli Artırımlı Sync**: Her 5 dakikada bir sadece değişen kayıtlar çekilir
- ✅ **Tüm Tablolar Desteklenir**: Leads, Contacts, Companies, Deals, Activities, Tasks, **Task Comments** dahil
- ✅ **Arka Plan Daemon**: Kesintisiz çalışır, sistem yeniden başladığında otomatik başlar
- ✅ **FastAPI Backend**: Modern async API (port 8001)
- ✅ **Next.js 16 Frontend**: Export Wizard UI (port 3000)
- ✅ **Otomatik İlişki Tespiti**: Foreign key'leri otomatik bulur ve ilişkili verileri dahil eder
- ✅ **Türkçe Destek**: Tarih formatları (DD/MM/YYYY), kolon isimleri

## � Veritabanı Durumu (Anlık)

| Tablo | Kayıt Sayısı | Son Güncelleme |
|-------|--------------|----------------|
| **activities** | 166,567 | Her 5 dakika ⏱️ |
| **task_comments** | 113,628 | Her 5 dakika ⏱️ |
| **tasks** | 43,722 | Her 5 dakika ⏱️ |
| **contacts** | 29,477 | Her 5 dakika ⏱️ |
| **deals** | 28,844 | Her 5 dakika ⏱️ |
| **leads** | 7,715 | Her 5 dakika ⏱️ |
| **companies** | 51 | Her 5 dakika ⏱️ |
| **users** | 50 | Her 50 dakika 🔁 |
| **departments** | 14 | Her 50 dakika 🔁 |

**Toplam**: ~390,000+ kayıt (260 MB veri)

## 🚀 Hızlı Başlangıç



## 🚀 Hızlı Başlangıç```

bitsheet24/

```bash├── venv/                    # Python sanal ortamı

# Servisi kur├── src/                     # Ana kaynak kodu

sudo ./install_service.sh│   ├── __init__.py

│   ├── config.py           # Ayar dosyası

# Durumu kontrol et│   ├── models.py           # Veritabanı modelleri

sudo systemctl status bitrix-sync│   └── main.py             # Ana uygulama

├── tests/                  # Test dosyaları

# Logları izle├── .env                    # Ortam değişkenleri (GIT'te yok)

sudo journalctl -u bitrix-sync -f├── requirements.txt        # Python bağımlılıkları

```├── test_db.py             # PostgreSQL bağlantı testi

├── test_sqlalchemy.py     # SQLAlchemy testi

## 📚 Dokümantasyon# Bitrix24 Sync Service



### Kurulum & KullanımBitrix24 CRM verilerini PostgreSQL veritabanına sürekli olarak senkronize eden daemon servisi.

- [📖 Kurulum Kılavuzu](docs/setup/README.md) - Detaylı kurulum adımları

- [🚀 Hızlı Başlangıç](docs/setup/QUICKSTART.md) - Temel komutlar ve kullanım## 🚀 Özellikler



### Analiz & Raporlama- ✅ Sürekli çalışan systemd servisi

- [📊 Veri Analiz Fırsatları](docs/analysis/BITRIX_DATA_ANALYSIS.md) - Eklenebilecek tablolar ve analiz örnekleri- ✅ Artırımlı senkronizasyon (sadece değişen kayıtlar)

- [👥 Personel Performans Analizi](docs/analysis/PERSONEL_ANALIZI.md) - Çalışan performans metrikleri- ✅ Otomatik yeniden başlatma (çökme durumunda)

- ✅ Detaylı loglama

### API Dokümantasyonu- ✅ Graceful shutdown (sinyal kontrolü)

- [🔌 Bitrix24 API Referansı](docs/api/) - API endpoint'leri ve kullanım- ✅ Kaynak sınırlamaları (Memory, CPU)



## 📊 Mevcut Tablolar## 📦 Desteklenen Tablolar



| Tablo | Kayıt Sayısı | Sync Tipi | Durum || Tablo | Senkronizasyon | Filtre Alanları |

|-------|--------------|-----------|-------||-------|----------------|-----------------|

| leads | 7,685 | Incremental | ✅ Aktif || leads | Artırımlı | DATE_CREATE, DATE_MODIFY |

| contacts | 29,430 | Incremental | ✅ Aktif || contacts | Artırımlı | DATE_CREATE, DATE_MODIFY |

| deals | 28,781 | Incremental | ✅ Aktif || deals | Artırımlı | DATE_CREATE, DATE_MODIFY |

| activities | 165,950 | Incremental | ✅ Aktif || activities | Artırımlı | CREATED, LAST_UPDATED |

| tasks | 43,431 | Full Sync | ⏳ Geliştirilecek || tasks | Full sync | (artırımlı geliştiriliyor) |

| users | 50 | Full Sync | ✅ Aktif |

| departments | 14 | Full Sync | ✅ Aktif |## 🔧 Kurulum



## 🎯 Özellikler### 1. Bağımlılıkları Yükle



- ✅ Otomatik artırımlı senkronizasyon (her 10 dakika)```bash

- ✅ Systemd daemon olarak çalışma# PostgreSQL kurulu olmalı

- ✅ Otomatik yeniden başlatma (hata durumunda)sudo apt-get install postgresql postgresql-contrib

- ✅ JSONB tabanlı esnek veri modeli

- ✅ Kaynak limitleri (Memory, CPU)# Python bağımlılıkları

- ✅ Detaylı loglamacd /home/captain/bitsheet24

python -m venv venv

## 🔧 Temel Komutlarsource venv/bin/activate

pip install -r requirements.txt

```bash```

# Servis yönetimi

sudo systemctl status bitrix-sync### 2. Veritabanı Konfigürasyonu

sudo systemctl stop bitrix-sync

sudo systemctl start bitrix-sync`.env` dosyasını düzenle:

sudo systemctl restart bitrix-sync```bash

BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.com/rest/1/your-webhook-key/

# Manuel syncDATABASE_URL=postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db

python sync_bitrix.py all --incremental```

python sync_bitrix.py leads --incremental

### 3. İlk Full Sync

# Loglar

sudo journalctl -u bitrix-sync -f```bash

tail -f logs/sync_daemon.log# Tüm tabloları ilk kez senkronize et

```python sync_bitrix.py all



## 📁 Proje Yapısı# Veya teker teker

python sync_bitrix.py leads

```python sync_bitrix.py contacts

bitsheet24/python sync_bitrix.py deals

├── docs/                       # Dokümantasyonpython sync_bitrix.py activities

│   ├── setup/                  # Kurulum kılavuzları```

│   ├── analysis/               # Analiz rehberleri

│   └── api/                    # API dokümantasyonu### 4. Servisi Kur

├── src/                        # Kaynak kod

│   ├── bitrix/                 # Bitrix24 entegrasyonu```bash

│   │   ├── client.py           # API istemcisi# Servisi systemd'ye kur ve başlat

│   │   └── ingestors/          # Tablo senkronizasyon modüllerisudo ./install_service.sh

│   ├── storage.py              # Veritabanı işlemleri```

│   └── config.py               # Konfigürasyon

├── logs/                       # Log dosyaları## 📊 Kullanım

├── bitrix_sync_daemon.py       # Ana daemon

├── sync_bitrix.py              # Manuel sync CLI### Servis Komutları

├── install_service.sh          # Kurulum scripti

└── uninstall_service.sh        # Kaldırma scripti```bash

```# Servis durumunu kontrol et

sudo systemctl status bitrix-sync

## 🔐 Konfigürasyon

# Logları takip et

`.env` dosyası:sudo journalctl -u bitrix-sync -f

```bash

BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.com/rest/1/your-key/# Servisi durdur

DATABASE_URL=postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_dbsudo systemctl stop bitrix-sync

```

# Servisi başlat

## 📈 Performanssudo systemctl start bitrix-sync



- **Artırımlı Sync**: ~1-5 saniye# Servisi yeniden başlat

- **Full Sync**: Entity başına 2-8 dakikasudo systemctl restart bitrix-sync

- **Kaynak Kullanımı**: <1GB RAM, <50% CPU

# Servisi devre dışı bırak (otomatik başlatma)

## 🆘 Desteksudo systemctl disable bitrix-sync



Sorunlar için:# Servisi kaldır

1. [Hızlı Başlangıç Kılavuzu](docs/setup/QUICKSTART.md)sudo ./uninstall_service.sh

2. [GitHub Issues](https://github.com/captainmgc/bitsheetsync24/issues)```



## 📝 Lisans### Manuel Sync



Şirket içi kullanım için geliştirilmiştir.```bash

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
