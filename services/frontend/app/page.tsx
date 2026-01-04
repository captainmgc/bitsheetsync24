'use client'

import type { ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileSpreadsheet, Database, Zap, ArrowRight, CheckCircle2, BarChart3, ShieldCheck } from 'lucide-react'

const stats = [
  { label: 'Aktivite', value: '166K+', color: 'text-blue-600' },
  { label: 'Görev Yorumu', value: '113K+', color: 'text-green-600' },
  { label: 'Görev', value: '43K+', color: 'text-purple-600' },
  { label: 'İletişim', value: '29K+', color: 'text-orange-600' },
] as const

const features = [
  {
    icon: <Zap className="w-6 h-6 text-blue-600" />,
    title: 'Otomatik İlişki Tespiti',
    description:
      'Tabloları seçin; ilişkili verileri (Deal → Contact → Company) otomatik bulup bağlayalım.',
  },
  {
    icon: <FileSpreadsheet className="w-6 h-6 text-green-600" />,
    title: 'Türkçe Format Desteği',
    description:
      'Tarih, saat ve para birimi alanları Türkiye standartlarına (DD/MM/YYYY) uygun formatlanır.',
  },
  {
    icon: <Database className="w-6 h-6 text-purple-600" />,
    title: 'Yüksek Performans',
    description:
      'Binlerce kaydı batch processing ile hızlı aktarın. Kesinti olursa kaldığı yerden devam eder.',
  },
  {
    icon: <ShieldCheck className="w-6 h-6 text-indigo-600" />,
    title: 'Güvenli Aktarım',
    description:
      "Verileriniz şifreli kanallar üzerinden doğrudan Google Sheets API'sine iletilir.",
  },
  {
    icon: <CheckCircle2 className="w-6 h-6 text-teal-600" />,
    title: 'Kolay Kurulum',
    description:
      'Karmaşık konfigürasyon yok. Birkaç adımda Bitrix24 ve Google hesabınızı bağlayın.',
  },
  {
    icon: <BarChart3 className="w-6 h-6 text-orange-600" />,
    title: 'Detaylı Loglama',
    description:
      'Her işlemin kaydı tutulur. Hata durumunda hızlı aksiyon için net loglar sunulur.',
  },
] as const

export default function Home() {
  const router = useRouter()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <nav aria-label="Üst menü" className="border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Image src="/logo.png" alt="BitSheet24" width={32} height={32} className="rounded" />
            <span className="font-bold text-xl text-foreground">BitSheet24</span>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => router.push('/auth/signin')}>Giriş Yap</Button>
            <Button onClick={() => router.push('/dashboard')}>Dashboard</Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative flex-1 flex flex-col justify-center py-16 md:py-24 px-4">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 left-1/2 h-72 w-[42rem] -translate-x-1/2 rounded-full bg-gradient-to-r from-blue-200/50 to-cyan-200/50 blur-3xl" />
          <div className="absolute -bottom-28 left-1/2 h-72 w-[42rem] -translate-x-1/2 rounded-full bg-gradient-to-r from-purple-200/40 to-blue-200/40 blur-3xl" />
        </div>

        <div className="container mx-auto max-w-6xl">
          <div className="text-center">
            <Badge variant="secondary" className="mb-6 px-4 py-1 text-sm font-medium">
              v1.0.0 Yayında • Otomatik İlişki Tespiti
            </Badge>

            <h1 className="text-4xl md:text-6xl font-extrabold text-foreground tracking-tight mb-6">
              Bitrix24 Verilerinizi
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-600">
                Google Sheets'e Taşıyın
              </span>
            </h1>

            <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto leading-relaxed">
              Karmaşık veri yapılarını otomatik analiz eder, ilişkileri kurar ve raporlamaya hazır formatta Google Sheets'e aktarır.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
              <Button size="lg" className="h-12 px-8 text-base md:text-lg gap-2" onClick={() => router.push('/dashboard')}>
                Hemen Başlayın <ArrowRight className="w-5 h-5" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="h-12 px-8 text-base md:text-lg"
                onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Özellikleri İncele
              </Button>
            </div>

            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3 text-sm text-muted-foreground">
              <div className="inline-flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Kurulum dakikalar sürer
              </div>
              <div className="hidden sm:block">•</div>
              <div className="inline-flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-600" />
                Güvenli veri aktarımı
              </div>
              <div className="hidden sm:block">•</div>
              <div className="inline-flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-orange-600" />
                Loglarla tam görünürlük
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="mt-12 md:mt-16">
            <Card className="overflow-hidden">
              <div className="p-2 md:p-3">
                <div className="aspect-video rounded-lg border bg-muted/20 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-muted/10 to-transparent" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center text-muted-foreground px-6">
                      <BarChart3 className="w-14 h-14 mx-auto mb-4 opacity-70" />
                      <p className="text-base md:text-lg font-medium">Dashboard Önizlemesi</p>
                      <p className="text-sm mt-1">Senkronizasyon durumu, loglar ve özet metrikler</p>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-14 md:py-16 border-y bg-background">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 text-center">
            {stats.map((stat) => (
              <div key={stat.label} className="space-y-2">
                <div className={`text-3xl md:text-4xl font-bold ${stat.color}`}>{stat.value}</div>
                <div className="text-sm md:text-base text-muted-foreground font-medium">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 md:py-24 bg-muted/20">
        <div className="container mx-auto px-4 max-w-6xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-foreground mb-4">Neden BitSheet24?</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Veri senkronizasyonunu manuel yapmaktan kurtulun. Modern, hızlı ve güvenilir altyapı.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature) => (
              <FeatureCard
                key={feature.title}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-background py-12 border-t">
        <div className="container mx-auto px-4 text-center text-muted-foreground">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Image src="/logo.png" alt="BitSheet24" width={24} height={24} className="opacity-50 grayscale" />
            <span className="font-semibold text-foreground">BitSheet24</span>
          </div>
          <p className="text-sm">
            © {new Date().getFullYear()} Japon Konutları. Tüm hakları saklıdır.
          </p>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: ReactNode; title: string; description: string }) {
  return (
    <Card className="border-none shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5">
      <CardHeader>
        <div className="w-12 h-12 bg-muted rounded-xl flex items-center justify-center mb-4">
          {icon}
        </div>
        <CardTitle className="text-xl">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription className="text-base leading-relaxed">
          {description}
        </CardDescription>
      </CardContent>
    </Card>
  )
}
// test
