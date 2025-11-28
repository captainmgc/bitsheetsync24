# BitSheet24 - Ürün Gereksinimleri Dokümanı (PRD)

> **Versiyon:** 1.0  
> **Tarih:** 28 Kasım 2025  
> **Durum:** Geliştirme Aşamasında

---

## 🎯 Vizyon

**BitSheet24**, Bitrix24 CRM verilerini Google Sheets ile senkronize eden ve yapay zeka destekli müşteri analizi sunan bir platformdur. Teknik bilgisi olmayan kullanıcıların (patron/yönetici) tek tıkla tüm işlemleri gerçekleştirmesini hedefler.

---

## 👤 Hedef Kullanıcı

- **Birincil:** Şirket patronu/yöneticisi (teknik bilgisi yok)
- **Gereksinim:** Basit, tek tıkla çalışan arayüz
- **Beklenti:** Karmaşık ayarlar olmadan veri senkronizasyonu ve analiz

---

## 🔄 Ana Özellikler

### A. Bitrix24 → Google Sheets Senkronizasyonu

#### [x] A.1 Tek Tıkla Kurulum Sihirbazı
- [x] Bitrix24 bağlantısı için basit webhook URL girişi
- [x] Google hesabı ile tek tıkla OAuth bağlantısı
- [x] Otomatik spreadsheet oluşturma
- [x] Kurulum tamamlandığında başarı bildirimi

#### [x] A.2 Veri Aktarımı
- [x] Anlaşmalar (Deals) aktarımı
- [x] Kişiler (Contacts) aktarımı
- [x] Şirketler (Companies) aktarımı
- [x] Aktiviteler aktarımı
- [x] Görevler aktarımı
- [x] Özel alanlar desteği
- [x] Türkçe tarih formatı (DD/MM/YYYY)
- [x] Tablolar arası ilişki tespiti ve aktarım (RelationshipAnalyzer)

#### [x] A.3 Otomatik Senkronizasyon
- [x] Zamanlayıcı ile otomatik senkronizasyon (5dk, 15dk, 1saat, günlük)
- [x] Manuel "Şimdi Senkronize Et" butonu
- [x] Son senkronizasyon durumu göstergesi
- [x] Senkronizasyon geçmişi

---

### B. Google Sheets → Bitrix24 Ters Senkronizasyon

#### [ ] B.1 Değişiklik Algılama
- [ ] Google Sheets'te yapılan değişikliklerin otomatik algılanması
- [ ] Değişen hücrelerin işaretlenmesi
- [ ] Değişiklik önizleme ekranı

#### [ ] B.2 Bitrix24'e Geri Yazma
- [ ] Tek tıkla değişiklikleri Bitrix24'e gönderme
- [ ] Seçili satırları güncelleme
- [ ] Toplu güncelleme desteği
- [ ] Güncelleme sonucu bildirimi (başarılı/hatalı)

#### [ ] B.3 Çakışma Yönetimi
- [ ] Aynı anda iki yerde değişiklik olduğunda uyarı
- [ ] "Hangisi geçerli?" seçim ekranı
- [ ] Değişiklik geçmişi karşılaştırması

---

### C. Yapay Zeka Destekli Müşteri Analizi

#### [ ] C.1 Müşteri Yolculuğu Özeti
- [ ] Seçilen müşteri/anlaşma için AI özeti oluşturma
- [ ] Tüm iletişim geçmişini analiz etme
- [ ] Türkçe özet üretimi
- [ ] Özeti Bitrix24'e yazma seçeneği

#### [ ] C.2 AI Sağlayıcı Desteği
- [x] OpenAI (GPT-4) desteği
- [x] Claude (Anthropic) desteği
- [x] Google Gemini desteği
- [x] OpenRouter desteği (100+ model)
- [x] Ollama (yerel model) desteği

#### [ ] C.3 Akıllı Öneriler
- [ ] Satış tahmini ve olasılık analizi
- [ ] Sonraki adım önerileri
- [ ] Risk uyarıları
- [ ] Müşteri segmentasyonu

---

### D. Dashboard ve Raporlama

#### [ ] D.1 Ana Kontrol Paneli
- [ ] Toplam anlaşma sayısı widget'ı
- [ ] Satış hunisi görselleştirmesi
- [ ] Son aktiviteler listesi
- [ ] Senkronizasyon durumu

#### [ ] D.2 Hata Takibi
- [ ] Hatalı senkronizasyonların listesi
- [ ] Hata detayları ve çözüm önerileri
- [ ] Yeniden deneme butonu

#### [ ] D.3 Raporlar
- [ ] Günlük/haftalık/aylık özet rapor
- [ ] Excel/PDF export
- [ ] E-posta ile rapor gönderimi

---

### E. Kullanıcı Deneyimi (UX)

#### [ ] E.1 Basit Arayüz
- [ ] Minimum tıklama ile işlem tamamlama
- [ ] Büyük ve anlaşılır butonlar
- [ ] Türkçe arayüz
- [ ] Yardım ipuçları (tooltip)

#### [ ] E.2 Bildirimler
- [ ] Başarılı işlem bildirimleri (yeşil)
- [ ] Hata bildirimleri (kırmızı)
- [ ] İlerleme göstergeleri
- [ ] Sesli/görsel uyarılar

#### [ ] E.3 Mobil Uyumluluk
- [ ] Responsive tasarım
- [ ] Mobil cihazlardan erişim
- [ ] Temel işlemler mobilde çalışmalı

---

## 📊 Mevcut Durum

### ✅ Tamamlanan
- [x] Bitrix24 veri çekme altyapısı
- [x] PostgreSQL veritabanı
- [x] Backend API (FastAPI)
- [x] Frontend iskelet (Next.js)
- [x] AI Summarizer servisi
- [x] Çoklu AI sağlayıcı desteği
- [x] Veri görüntülemede ayrı kolonlar (original_data gizlendi)
- [x] Normalize edilmiş tablo yapısı

### 🔄 Devam Eden
- [ ] Google Sheets OAuth entegrasyonu
- [ ] Ters senkronizasyon (Sheets → Bitrix)
- [ ] AI özet arayüzü

### ❌ Başlanmadı
- [ ] Tek tıkla kurulum sihirbazı
- [ ] Çakışma yönetimi
- [ ] Mobil uyumluluk
- [ ] Raporlama modülü

---

## 🚀 Öncelik Sırası

| Öncelik | Özellik | Neden? |
|---------|---------|--------|
| 1 | Google Sheets OAuth | Temel işlevsellik |
| 2 | Tek Tıkla Kurulum | Patron kullanabilmeli |
| 3 | Ters Senkronizasyon | Ana değer önerisi |
| 4 | AI Analiz Arayüzü | Rekabet avantajı |
| 5 | Dashboard | Görselleştirme |
| 6 | Raporlama | İleri seviye |

---

## 📝 Notlar

- Tüm arayüz Türkçe olmalı
- Hata mesajları anlaşılır ve çözüm odaklı olmalı
- Patron için "Uzman Modu" gizli olmalı, varsayılan basit mod
- Her işlem maksimum 3 tıkla tamamlanabilmeli

---

