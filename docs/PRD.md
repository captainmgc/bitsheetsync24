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

#### [x] B.1 Değişiklik Algılama
- [x] Google Sheets'te yapılan değişikliklerin otomatik algılanması
- [x] Değişen hücrelerin işaretlenmesi
- [x] Değişiklik önizleme ekranı

#### [x] B.2 Bitrix24'e Geri Yazma
- [x] Tek tıkla değişiklikleri Bitrix24'e gönderme
- [x] Seçili satırları güncelleme
- [x] Toplu güncelleme desteği
- [x] Güncelleme sonucu bildirimi (başarılı/hatalı)

#### [x] B.3 Çakışma Yönetimi
- [x] Aynı anda iki yerde değişiklik olduğunda uyarı
- [x] "Hangisi geçerli?" seçim ekranı
- [x] Değişiklik geçmişi karşılaştırması

---

### C. Yapay Zeka Destekli Müşteri Analizi

#### [x] C.1 Müşteri Yolculuğu Özeti
- [x] Seçilen müşteri/anlaşma için AI özeti oluşturma
- [x] Tüm iletişim geçmişini analiz etme
- [x] Türkçe özet üretimi
- [x] Özeti Bitrix24'e yazma seçeneği

#### [x] C.2 AI Sağlayıcı Desteği
- [x] OpenAI (GPT-4) desteği
- [x] Claude (Anthropic) desteği
- [x] Google Gemini desteği
- [x] OpenRouter desteği (100+ model)
- [x] Ollama (yerel model) desteği

#### [x] C.3 Akıllı Öneriler
- [x] Satış tahmini ve olasılık analizi
- [x] Sonraki adım önerileri
- [x] Risk uyarıları
- [x] Müşteri segmentasyonu

---

### D. Dashboard ve Raporlama

#### [x] D.1 Ana Kontrol Paneli
- [x] Toplam anlaşma sayısı widget'ı
- [x] Satış hunisi görselleştirmesi
- [x] Son aktiviteler listesi
- [x] Senkronizasyon durumu

#### [x] D.2 Hata Takibi
- [x] Hatalı senkronizasyonların listesi
- [x] Hata detayları ve çözüm önerileri
- [x] Yeniden deneme butonu

#### [x] D.3 Raporlar
- [x] Günlük/haftalık/aylık özet rapor
- [x] Excel/PDF export

---

### E. Kullanıcı Deneyimi (UX)

#### [x] E.1 Basit Arayüz
- [x] Minimum tıklama ile işlem tamamlama
- [x] Büyük ve anlaşılır butonlar
- [x] Türkçe arayüz
- [x] Yardım ipuçları (tooltip)

#### [x] E.2 Bildirimler
- [x] Başarılı işlem bildirimleri (yeşil)
- [x] Hata bildirimleri (kırmızı)
- [x] İlerleme göstergeleri



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
- [x] Google Sheets OAuth entegrasyonu
- [x] Ters senkronizasyon (Sheets → Bitrix)
- [x] AI özet arayüzü
- [x] Tek tıkla kurulum sihirbazı
- [x] Çakışma yönetimi
- [x] Dashboard (Ana Kontrol Paneli)
- [x] Hata Takibi sayfası
- [x] Export/Raporlama modülü




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

