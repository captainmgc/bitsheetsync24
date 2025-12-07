'use client'

import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Wrench, ArrowLeft } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export default function ViewManagementPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="min-h-screen flex items-center justify-center p-4">
          <Card className="max-w-lg w-full text-center">
            <CardHeader>
              <div className="mx-auto w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mb-4">
                <Wrench className="w-8 h-8 text-amber-600" />
              </div>
              <CardTitle className="text-2xl">Sayfa Bakımda</CardTitle>
              <CardDescription className="text-base mt-2">
                View Yönetimi şu anda bakım çalışması nedeniyle kullanılamıyor.
                <br />
                Kısa süre içinde tekrar hizmetinizde olacağız.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
                <strong>Bakım Bildirimi:</strong> Sistem iyileştirmeleri ve performans optimizasyonları yapılmaktadır.
              </div>
              <Link href="/dashboard">
                <Button className="w-full">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Dashboard&apos;a Dön
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
