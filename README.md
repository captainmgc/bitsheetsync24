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
└── README.md              # Bu dosya
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
