'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileSpreadsheet, Database, Zap, ArrowRight } from 'lucide-react'

export default function Home() {
  const router = useRouter()

  return (
    <div className="container mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Database className="w-12 h-12 text-blue-600" />
          <ArrowRight className="w-8 h-8 text-gray-400" />
          <FileSpreadsheet className="w-12 h-12 text-green-600" />
        </div>
        <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent mb-4">
          Bitrix24 → Google Sheets
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Verilerinizi otomatik ilişki tespiti ile kolayca Google Sheets'e aktarın
        </p>
      </div>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-6 mb-12">
        <Card className="border-2 hover:border-blue-500 transition-colors">
          <CardHeader>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-blue-600" />
            </div>
            <CardTitle>Otomatik İlişki Tespiti</CardTitle>
            <CardDescription>
              Tabloları seçin, ilişkili verileri otomatik olarak bulup dahil edelim
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="border-2 hover:border-green-500 transition-colors">
          <CardHeader>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <FileSpreadsheet className="w-6 h-6 text-green-600" />
            </div>
            <CardTitle>Türkçe Formatlar</CardTitle>
            <CardDescription>
              Tarih ve saat kolonları DD/MM/YYYY formatında ayrı ayrı
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="border-2 hover:border-purple-500 transition-colors">
          <CardHeader>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <Database className="w-6 h-6 text-purple-600" />
            </div>
            <CardTitle>Toplu İşlem</CardTitle>
            <CardDescription>
              Binlerce kaydı batch'ler halinde hızlı ve güvenli şekilde aktarın
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Stats */}
      <Card className="mb-12 border-2">
        <CardHeader>
          <CardTitle>Veritabanı Durumu</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-1">166K+</div>
              <div className="text-sm text-gray-600">Aktivite</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 mb-1">113K+</div>
              <div className="text-sm text-gray-600">Görev Yorumu</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600 mb-1">43K+</div>
              <div className="text-sm text-gray-600">Görev</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600 mb-1">29K+</div>
              <div className="text-sm text-gray-600">İletişim</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* CTA */}
      <div className="text-center">
        <Button 
          size="lg" 
          className="text-lg px-8 py-6 bg-gradient-to-r from-blue-600 to-green-600 hover:from-blue-700 hover:to-green-700"
          onClick={() => router.push('/dashboard')}
        >
          <FileSpreadsheet className="w-5 h-5 mr-2" />
          Dashboard'a Git
        </Button>
        <p className="text-sm text-gray-500 mt-4">
          <Badge variant="outline" className="mr-2">v1.0.0</Badge>
          Kullanıma hazır • Otomatik ilişki tespiti aktif
        </p>
      </div>
    </div>
  )
}
