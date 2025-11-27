import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Gizlilik Politikası - BitSheet24",
  description: "BitSheet24 gizlilik politikası ve veri koruma uygulamaları",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="max-w-4xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <Link 
            href="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Ana Sayfaya Dön
          </Link>
          <h1 className="text-3xl font-bold text-slate-900">Gizlilik Politikası</h1>
          <p className="text-slate-500 mt-2">Son güncelleme: 27 Kasım 2025</p>
        </div>

        {/* Content */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-8">
          
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Genel Bakış</h2>
            <p className="text-slate-600 leading-relaxed">
              BitSheet24 (&quot;biz&quot;, &quot;bizim&quot; veya &quot;Hizmet&quot;), kullanıcılarımızın 
              gizliliğine büyük önem vermektedir. Bu gizlilik politikası, hizmetimizi kullandığınızda 
              toplanan, kullanılan ve paylaşılan bilgileri açıklamaktadır.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Topladığımız Bilgiler</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium text-slate-800 mb-2">Google Hesap Bilgileri</h3>
                <ul className="list-disc list-inside text-slate-600 space-y-1">
                  <li>E-posta adresiniz</li>
                  <li>Profil fotoğrafınız</li>
                  <li>Google hesap kimliğiniz</li>
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-slate-800 mb-2">Google Sheets Erişimi</h3>
                <ul className="list-disc list-inside text-slate-600 space-y-1">
                  <li>Yetkilendirdiğiniz Google Sheets dosyalarına okuma/yazma erişimi</li>
                  <li>Sheets meta verileri (dosya adı, ID)</li>
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-slate-800 mb-2">Kullanım Verileri</h3>
                <ul className="list-disc list-inside text-slate-600 space-y-1">
                  <li>Senkronizasyon geçmişi ve logları</li>
                  <li>Hata raporları</li>
                  <li>Hizmet kullanım istatistikleri</li>
                </ul>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Bilgilerin Kullanımı</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              Topladığımız bilgileri aşağıdaki amaçlarla kullanıyoruz:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Bitrix24 ve Google Sheets arasında veri senkronizasyonu sağlamak</li>
              <li>Hizmet kalitesini iyileştirmek</li>
              <li>Teknik sorunları tespit etmek ve çözmek</li>
              <li>Kullanıcı desteği sağlamak</li>
              <li>Yasal yükümlülükleri yerine getirmek</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Google API Kullanımı</h2>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-800 leading-relaxed">
                <strong>Önemli:</strong> BitSheet24&apos;ün Google API Hizmetleri&apos;nden aldığı ve 
                kullandığı bilgiler,{" "}
                <a 
                  href="https://developers.google.com/terms/api-services-user-data-policy" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline font-medium"
                >
                  Google API Hizmetleri Kullanıcı Verileri Politikası
                </a>
                &apos;na, Sınırlı Kullanım gereksinimleri dahil olmak üzere uygundur.
              </p>
            </div>
            <div className="mt-4 space-y-2 text-slate-600">
              <p>Google API&apos;leri aracılığıyla erişilen veriler:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Yalnızca senkronizasyon işlemleri için kullanılır</li>
                <li>Üçüncü taraflarla paylaşılmaz</li>
                <li>Reklam amaçlı kullanılmaz</li>
                <li>Oturumunuz sona erdiğinde veya hesabınızı sildiğinizde kaldırılır</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Veri Güvenliği</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              Verilerinizi korumak için aşağıdaki güvenlik önlemlerini alıyoruz:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>SSL/TLS ile şifreli veri iletimi</li>
              <li>OAuth 2.0 tabanlı güvenli kimlik doğrulama</li>
              <li>Access token&apos;ların güvenli saklanması</li>
              <li>Düzenli güvenlik güncellemeleri</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Veri Saklama</h2>
            <p className="text-slate-600 leading-relaxed">
              Verilerinizi yalnızca hizmet sağlamak için gerekli olduğu sürece saklarız. 
              Hesabınızı sildiğinizde veya erişimi iptal ettiğinizde, verileriniz 30 gün 
              içinde sistemlerimizden kalıcı olarak silinir.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Çerezler (Cookies)</h2>
            <p className="text-slate-600 leading-relaxed">
              Hizmetimiz, oturum yönetimi ve tercihlerinizi hatırlamak için çerezler kullanır. 
              Tarayıcınızın ayarlarından çerezleri devre dışı bırakabilirsiniz, ancak bu 
              bazı özelliklerin çalışmamasına neden olabilir.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Üçüncü Taraf Hizmetleri</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              Hizmetimiz aşağıdaki üçüncü taraf hizmetlerini kullanır:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>
                <strong>Google OAuth:</strong> Kimlik doğrulama için
                {" "}(<a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Gizlilik Politikası</a>)
              </li>
              <li>
                <strong>Google Sheets API:</strong> Veri senkronizasyonu için
              </li>
              <li>
                <strong>Bitrix24 API:</strong> CRM veri erişimi için
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Haklarınız</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              KVKK ve GDPR kapsamında aşağıdaki haklara sahipsiniz:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Verilerinize erişim talep etme</li>
              <li>Verilerinizin düzeltilmesini isteme</li>
              <li>Verilerinizin silinmesini talep etme</li>
              <li>Veri işlemeye itiraz etme</li>
              <li>Verilerinizi başka bir hizmete taşıma</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">Politika Değişiklikleri</h2>
            <p className="text-slate-600 leading-relaxed">
              Bu gizlilik politikasını zaman zaman güncelleyebiliriz. Önemli değişiklikler 
              yapıldığında, web sitemizde duyuru yayınlayarak veya e-posta ile sizi 
              bilgilendireceğiz.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">İletişim</h2>
            <p className="text-slate-600 leading-relaxed">
              Gizlilik politikamız hakkında sorularınız veya veri talepleriniz için 
              bizimle iletişime geçebilirsiniz:
            </p>
            <div className="mt-4 bg-slate-50 rounded-lg p-4">
              <p className="text-slate-700">
                <strong>E-posta:</strong>{" "}
                <a href="mailto:privacy@japonkonutlari.com" className="text-blue-600 hover:underline">
                  privacy@japonkonutlari.com
                </a>
              </p>
              <p className="text-slate-700 mt-2">
                <strong>Web:</strong>{" "}
                <a href="https://etablo.japonkonutlari.com" className="text-blue-600 hover:underline">
                  etablo.japonkonutlari.com
                </a>
              </p>
            </div>
          </section>

        </div>

        {/* Footer Links */}
        <div className="mt-8 text-center text-sm text-slate-500">
          <Link href="/terms" className="text-blue-600 hover:underline">
            Kullanım Şartları
          </Link>
          <span className="mx-2">•</span>
          <Link href="/" className="text-blue-600 hover:underline">
            Ana Sayfa
          </Link>
        </div>
      </div>
    </div>
  );
}
