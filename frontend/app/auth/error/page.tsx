'use client'

import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, ArrowLeft, RefreshCw } from 'lucide-react'
import { Suspense } from 'react'

function ErrorContent() {
  const searchParams = useSearchParams()
  const error = searchParams.get('error')

  const errorMessages: Record<string, { title: string; description: string }> = {
    Configuration: {
      title: 'Yapılandırma Hatası',
      description: 'Sunucu yapılandırmasında bir sorun var. Lütfen yöneticiyle iletişime geçin.',
    },
    AccessDenied: {
      title: 'Erişim Reddedildi',
      description: 'Bu sayfaya erişim izniniz yok.',
    },
    Verification: {
      title: 'Doğrulama Hatası',
      description: 'Doğrulama bağlantısı geçersiz veya süresi dolmuş.',
    },
    OAuthSignin: {
      title: 'OAuth Giriş Hatası',
      description: 'OAuth sağlayıcısıyla bağlantı kurulamadı.',
    },
    OAuthCallback: {
      title: 'OAuth Callback Hatası',
      description: 'OAuth callback işlemi başarısız oldu.',
    },
    OAuthCreateAccount: {
      title: 'Hesap Oluşturma Hatası',
      description: 'OAuth ile hesap oluşturulamadı.',
    },
    EmailCreateAccount: {
      title: 'E-posta Hesap Hatası',
      description: 'E-posta ile hesap oluşturulamadı.',
    },
    Callback: {
      title: 'Callback Hatası',
      description: 'Giriş callback işlemi başarısız oldu.',
    },
    OAuthAccountNotLinked: {
      title: 'Hesap Bağlantısı Hatası',
      description: 'Bu e-posta adresi farklı bir giriş yöntemiyle kayıtlı.',
    },
    SessionRequired: {
      title: 'Oturum Gerekli',
      description: 'Bu sayfaya erişmek için giriş yapmanız gerekiyor.',
    },
    Default: {
      title: 'Bir Hata Oluştu',
      description: 'Giriş işlemi sırasında beklenmeyen bir hata oluştu.',
    },
  }

  const errorInfo = errorMessages[error || 'Default'] || errorMessages.Default

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <Card className="w-full max-w-md border-2 border-red-700/50">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
            <AlertTriangle className="w-8 h-8 text-red-600" />
          </div>
          <CardTitle className="text-xl text-red-600">{errorInfo.title}</CardTitle>
          <CardDescription className="text-base">
            {errorInfo.description}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="bg-slate-100 dark:bg-slate-800 p-3 rounded-lg">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hata Kodu:</p>
              <code className="text-sm font-mono text-slate-700 dark:text-slate-300">{error}</code>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Button asChild className="w-full">
              <Link href="/auth/signin">
                <RefreshCw className="w-4 h-4 mr-2" />
                Tekrar Dene
              </Link>
            </Button>
            
            <Button asChild variant="outline" className="w-full">
              <Link href="/">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Ana Sayfaya Dön
              </Link>
            </Button>
          </div>

          <p className="text-xs text-center text-slate-500">
            Sorun devam ederse lütfen{' '}
            <a href="mailto:destek@japonkonutlari.com" className="text-blue-500 hover:underline">
              destek ekibimizle
            </a>
            {' '}iletişime geçin.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
      </div>
    }>
      <ErrorContent />
    </Suspense>
  )
}
