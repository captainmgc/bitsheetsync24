import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Kullanım Şartları - BitSheet24",
  description: "BitSheet24 hizmet kullanım şartları ve koşulları",
};

export default function TermsPage() {
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
          <h1 className="text-3xl font-bold text-slate-900">Kullanım Şartları</h1>
          <p className="text-slate-500 mt-2">Son güncelleme: 27 Kasım 2025</p>
        </div>

        {/* Content */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-8">
          
          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">1. Hizmet Tanımı</h2>
            <p className="text-slate-600 leading-relaxed">
              BitSheet24 (&quot;Hizmet&quot;), Bitrix24 CRM sistemindeki verilerinizi Google Sheets ile 
              senkronize etmenizi sağlayan bir web uygulamasıdır. Hizmetimiz, veri entegrasyonu 
              ve otomatik senkronizasyon özellikleri sunar.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">2. Hesap Sorumlulukları</h2>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Google ve Bitrix24 hesap bilgilerinizin güvenliğinden siz sorumlusunuz.</li>
              <li>Hesabınız üzerinden gerçekleştirilen tüm işlemlerden siz sorumlusunuz.</li>
              <li>Yetkisiz erişim durumunda derhal bizi bilgilendirmelisiniz.</li>
              <li>Hizmeti yalnızca yasal amaçlar için kullanabilirsiniz.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">3. Veri Kullanımı</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              Hizmetimizi kullanarak, aşağıdaki veri işlemelerine onay vermiş olursunuz:
            </p>
            <ul className="list-disc list-inside text-slate-600 space-y-2">
              <li>Bitrix24 verilerinize okuma erişimi</li>
              <li>Google Sheets dosyalarınıza yazma erişimi</li>
              <li>Senkronizasyon için gerekli meta verilerin işlenmesi</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">4. Google API Hizmetleri</h2>
            <p className="text-slate-600 leading-relaxed">
              Bu uygulama Google API Hizmetleri&apos;ni kullanmaktadır. Google hesabınızla 
              oturum açtığınızda, Google&apos;ın{" "}
              <a 
                href="https://policies.google.com/terms" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Hizmet Şartları
              </a>
              {" "}ve{" "}
              <a 
                href="https://policies.google.com/privacy" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Gizlilik Politikası
              </a>
              &apos;nı da kabul etmiş olursunuz.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">5. Hizmet Değişiklikleri</h2>
            <p className="text-slate-600 leading-relaxed">
              Hizmetimizi önceden haber vermeksizin değiştirme, askıya alma veya sonlandırma 
              hakkını saklı tutarız. Önemli değişiklikler için kullanıcılarımızı bilgilendirmeye 
              çalışacağız.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">6. Sorumluluk Sınırlaması</h2>
            <p className="text-slate-600 leading-relaxed">
              Hizmet &quot;olduğu gibi&quot; sunulmaktadır. Veri kaybı, kesinti veya diğer 
              zararlardan doğrudan veya dolaylı olarak sorumlu tutulamayız. Kritik verilerinizin 
              yedeğini almanızı öneririz.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">7. Fikri Mülkiyet</h2>
            <p className="text-slate-600 leading-relaxed">
              BitSheet24 ve ilgili tüm içerik, tasarım ve kod telif hakkı ile korunmaktadır. 
              Yazılı izin olmadan kopyalama, değiştirme veya dağıtma yasaktır.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-slate-900 mb-4">8. İletişim</h2>
            <p className="text-slate-600 leading-relaxed">
              Bu kullanım şartları hakkında sorularınız için bizimle iletişime geçebilirsiniz:
            </p>
            <p className="text-slate-600 mt-2">
              E-posta: <a href="mailto:support@japonkonutlari.com" className="text-blue-600 hover:underline">support@japonkonutlari.com</a>
            </p>
          </section>

        </div>

        {/* Footer Links */}
        <div className="mt-8 text-center text-sm text-slate-500">
          <Link href="/privacy-policy" className="text-blue-600 hover:underline">
            Gizlilik Politikası
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
