'use client'

import { signIn } from 'next-auth/react'
import Image from 'next/image'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { CheckCircle2, ArrowLeft, ShieldCheck } from 'lucide-react'

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 p-4 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-6xl pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-200/20 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-200/20 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="mb-8 text-center">
           <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 transition-colors mb-6">
              <ArrowLeft className="w-4 h-4 mr-1" />
              Ana Sayfaya Dön
           </Link>
           <div className="flex justify-center mb-4">
             <Image
                src="/logo.png"
                alt="BitSheet24 Logo"
                width={64}
                height={64}
                className="rounded-xl shadow-lg"
                priority
              />
           </div>
           <h1 className="text-2xl font-bold text-slate-900">BitSheet24'e Hoş Geldiniz</h1>
           <p className="text-slate-500 mt-2">Devam etmek için giriş yapın</p>
        </div>

        <Card className="border-none shadow-xl bg-white/80 backdrop-blur-sm">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-xl text-center">Giriş Yap</CardTitle>
            <CardDescription className="text-center">
              Google hesabınızla güvenli bir şekilde oturum açın
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-slate-50/50 p-4 rounded-lg border border-slate-100 space-y-3">
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
                <span>Bitrix24 verilerinize erişim</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
                <span>Google Sheets senkronizasyonu</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <ShieldCheck className="w-4 h-4 text-blue-600 flex-shrink-0" />
                <span>Kurumsal seviyede güvenlik</span>
              </div>
            </div>

            <Button
              onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
              className="w-full h-12 text-base font-medium bg-white hover:bg-slate-50 text-slate-900 border border-slate-200 shadow-sm hover:shadow transition-all"
              variant="outline"
            >
              <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Google ile Devam Et
            </Button>
          </CardContent>
          <CardFooter className="flex flex-col gap-4 border-t bg-slate-50/50 p-6 rounded-b-xl">
             <p className="text-xs text-center text-slate-500 leading-relaxed">
              Devam ederek <Link href="/terms" className="text-blue-600 hover:underline font-medium">Kullanım Şartları</Link> ve <Link href="/privacy-policy" className="text-blue-600 hover:underline font-medium">Gizlilik Politikası</Link>'nı kabul etmiş olursunuz.
            </p>
          </CardFooter>
        </Card>
        
        <div className="mt-8 text-center">
          <p className="text-sm text-slate-400">
            © {new Date().getFullYear()} Japon Konutları
          </p>
        </div>
      </div>
    </div>
  )
}
