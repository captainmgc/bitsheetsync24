# 🗄️ BitSheet24 Veritabanı Yedekleme Sistemi

Otomatik PostgreSQL yedekleme ve geri yükleme sistemi.

## 📦 Hızlı Başlangıç

### 1️⃣ İlk Yedek Alma
```bash
./scripts/backup_database.sh
```

### 2️⃣ Yedekleri Listeleme
```bash
./scripts/list_backups.sh
```

### 3️⃣ Yedek Test Etme
```bash
./scripts/test_backup.sh
```

### 4️⃣ Otomatik Yedekleme Kurulumu
```bash
./scripts/setup_automated_backups.sh
```

## 🎯 Özellikler

✅ **Tam Veritabanı Yedeği** - Tüm tablolar ve veriler  
✅ **Sıkıştırma** - GZIP ile %80+ boyut azaltma  
✅ **Checksum** - MD5 ile integrity kontrolü  
✅ **Rotation** - Eski yedekleri otomatik sil  
✅ **Logging** - Detaylı log kayıtları  
✅ **Automated** - Cron ile otomatik yedekleme  
✅ **Safe Restore** - Geri yüklemeden önce safety backup  

## 📋 Saklama Politikası

| Periyot | Saklama Süresi | Açıklama |
|---------|----------------|----------|
| **Günlük** | 7 gün | Son 1 haftanın tüm yedekleri |
| **Haftalık** | 4 hafta | Her Pazar günü yedeği |
| **Aylık** | 6 ay | Her ayın 1'i yedeği |

## 🔄 Geri Yükleme

### Adım 1: Mevcut Yedekleri Listele
```bash
./scripts/list_backups.sh
```

### Adım 2: Restore Et
```bash
./scripts/restore_database.sh /path/to/backup.sql.gz
```

**⚠️ UYARI:** Restore mevcut veritabanını tamamen değiştirir!

## 🤖 Otomatik Yedekleme

### Cron Kurulumu
```bash
./scripts/setup_automated_backups.sh
```

### Manuel Cron Ekle
```bash
crontab -e

# Her gece saat 02:00
0 2 * * * /home/captain/bitsheet24/scripts/backup_database.sh

# Her Pazar 03:00
0 3 * * 0 /home/captain/bitsheet24/scripts/backup_database.sh

# Her ayın 1'i 04:00
0 4 1 * * /home/captain/bitsheet24/scripts/backup_database.sh
```

## 📊 Mevcut Durum

```bash
# Son backup
ls -lht backups/*.sql.gz | head -1

# Toplam boyut
du -sh backups/

# Log kontrolü
tail -f backups/backup.log
```

## 🔐 Güvenlik

### PostgreSQL Şifre Dosyası
```bash
# ~/.pgpass dosyası otomatik oluşturuldu
# Format: hostname:port:database:username:password
cat ~/.pgpass
```

### Backup Şifreleme (Opsiyonel)
```bash
# Encrypt backup
gpg -c bitsheet_backup_*.sql.gz

# Decrypt backup
gpg -d bitsheet_backup_*.sql.gz.gpg | gunzip | psql
```

## 🧪 Test ve Doğrulama

### Integrity Test
```bash
./scripts/test_backup.sh
```

### Manuel Checksum Kontrolü
```bash
md5sum -c backups/bitsheet_backup_*.sql.gz.md5
```

### Test Restore (Development)
```bash
# Test database'e restore
gunzip < backup.sql.gz | psql -U bitsheet -d test_db
```

## 📁 Dosya Yapısı

```
bitsheet24/
├── backups/
│   ├── bitsheet_backup_20251106_173556.sql.gz
│   ├── bitsheet_backup_20251106_173556.sql.gz.md5
│   ├── backup.log
│   └── restore.log
└── scripts/
    ├── backup_database.sh           # Yedek alma
    ├── restore_database.sh          # Geri yükleme
    ├── list_backups.sh              # Yedekleri listele
    ├── test_backup.sh               # Integrity testi
    └── setup_automated_backups.sh   # Cron kurulumu
```

## 🚨 Sorun Giderme

### Backup Başarısız
```bash
# Log kontrol
cat backups/backup.log

# Bağlantı test
psql -U bitsheet -d bitsheet_db -c "SELECT version();"

# Disk alanı
df -h backups/
```

### Restore Başarısız
```bash
# Restore log
cat backups/restore.log

# Safety backup kullan
ls -t backups/pre_restore_*.sql.gz | head -1
```

### Connection Error
```bash
# .pgpass dosyası kontrol
cat ~/.pgpass
chmod 600 ~/.pgpass

# PostgreSQL çalışıyor mu?
sudo systemctl status postgresql
```

## 📈 İleri Düzey

### Uzak Sunucuya Yedekleme
```bash
# SCP
scp backups/*.sql.gz user@remote:/backup/

# Rsync
rsync -avz backups/ user@remote:/backup/
```

### Belirli Tabloları Yedekleme
```bash
# Sadece contacts
pg_dump -U bitsheet -t bitrix.contacts bitsheet_db | gzip > contacts.sql.gz

# Birden fazla tablo
pg_dump -U bitsheet -t bitrix.contacts -t bitrix.deals bitsheet_db | gzip > selected.sql.gz
```

### S3/Cloud Backup
```bash
# AWS S3
aws s3 cp backups/ s3://my-bucket/bitsheet-backups/ --recursive

# Rclone (Google Drive, Dropbox, etc.)
rclone sync backups/ gdrive:bitsheet-backups/
```

## ✅ Checklist

- [x] Backup script çalışıyor
- [x] Checksum doğrulama aktif
- [x] Rotation politikası uygulanıyor
- [x] .pgpass dosyası oluşturuldu
- [ ] Cron job'ları kuruldu
- [ ] Offsite backup yapılandırıldı
- [ ] Restore test edildi
- [ ] Monitoring kuruldu

## 📞 Komutlar

| Komut | Açıklama |
|-------|----------|
| `./scripts/backup_database.sh` | Yeni yedek al |
| `./scripts/list_backups.sh` | Yedekleri listele |
| `./scripts/test_backup.sh` | Yedek doğrula |
| `./scripts/restore_database.sh <file>` | Geri yükle |
| `./scripts/setup_automated_backups.sh` | Cron kur |

---

**Son Güncelleme:** 2025-11-06  
**Versiyon:** 1.0  
**Durum:** ✅ Aktif
