# 🚀 BitSheet24 Sunucu Deployment Rehberi

## Ön Gereksinimler (Sunucuda)

```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Git
apt install git -y
```

---

## 1️⃣ Projeyi Sunucuya Çek

```bash
cd /opt
git clone https://github.com/captainmgc/bitsheetsync24.git bitsheet24
cd bitsheet24
```

---

## 2️⃣ Production Env Dosyasını Oluştur

```bash
cp .env.production.template .env.production
nano .env.production
```

**Düzenle:**
```env
ENVIRONMENT=production
DB_PASSWORD=GÜÇLÜ_BİR_ŞİFRE
NEXTAUTH_SECRET=openssl rand -base64 32
FRONTEND_URL=https://etablo.japonkonutlari.com
NEXT_PUBLIC_API_URL=https://etablo.japonkonutlari.com/api
```

---

## 3️⃣ SSL Sertifikaları (Let's Encrypt)

```bash
# Certbot kur
apt install certbot -y

# Sertifika al
certbot certonly --standalone -d etablo.japonkonutlari.com

# Sertifikaları kopyala
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/etablo.japonkonutlari.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/etablo.japonkonutlari.com/privkey.pem nginx/ssl/
```

---

## 4️⃣ Lokal Veritabanını Aktar

**Lokal makinede:**
```bash
# Yedek oluştur
./scripts/db_backup.sh

# Sunucuya aktar (SSH key gerekli)
./scripts/db_transfer.sh --latest --restore
```

---

## 5️⃣ Deploy Et

```bash
# Docker ile başlat
./deploy.sh

# Veya manuel:
docker compose --env-file .env.production up -d
```

---

## 6️⃣ Kontrol Et

```bash
# Servis durumu
docker compose ps

# Loglar
docker compose logs -f

# Health check
curl https://etablo.japonkonutlari.com/api/health
```

---

## 🔄 Güncelleme (Sonraki Deploylar)

```bash
cd /opt/bitsheet24
git pull origin main
docker compose --env-file .env.production up -d --build
```

---

## 📋 Hızlı Komutlar

| İşlem | Komut |
|-------|-------|
| Başlat | `docker compose up -d` |
| Durdur | `docker compose down` |
| Loglar | `docker compose logs -f` |
| Yeniden başlat | `docker compose restart` |
| Rebuild | `docker compose up -d --build` |

---

## 🔧 Sorun Giderme

```bash
# Container durumu
docker compose ps

# Belirli servis logu
docker compose logs backend -f

# Container'a bağlan
docker compose exec backend bash

# Veritabanına bağlan
docker compose exec postgres psql -U bitsheet -d bitsheet_db
```
