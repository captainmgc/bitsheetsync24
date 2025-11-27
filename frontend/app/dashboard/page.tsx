'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import MetricCard from '@/components/dashboard/MetricCard'
import { apiUrl } from '@/lib/config'
import { 
  Users, 
  Building2, 
  Briefcase, 
  Activity,
  CheckCircle2,
  MessageSquare,
  TrendingUp,
  Database
} from 'lucide-react'

interface TableStats {
  name: string
  display_name: string
  record_count: number
  last_updated: string
}

export default function DashboardPage() {
  const [stats, setStats] = useState<TableStats[]>([])
  const [loading, setLoading] = useState(true)
  const { data: session } = useSession()

  useEffect(() => {
    fetch(apiUrl('/api/tables/'))
      .then(res => res.json())
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch stats:', err)
        setLoading(false)
      })
  }, [])

  const getTableCount = (name: string) => {
    const table = stats.find(t => t.name === name)
    return table?.record_count || 0
  }

  const metrics = [
    {
      title: 'Toplam Müşteriler',
      value: getTableCount('contacts'),
      icon: Users,
      gradient: 'bg-gradient-to-br from-blue-500 to-blue-600',
      change: { value: 2.5, trend: 'up' as const }
    },
    {
      title: 'Şirketler',
      value: getTableCount('companies'),
      icon: Building2,
      gradient: 'bg-gradient-to-br from-purple-500 to-purple-600',
      change: { value: 1.2, trend: 'up' as const }
    },
    {
      title: 'Anlaşmalar',
      value: getTableCount('deals'),
      icon: Briefcase,
      gradient: 'bg-gradient-to-br from-green-500 to-green-600',
      change: { value: 5.4, trend: 'up' as const }
    },
    {
      title: 'Aktiviteler',
      value: getTableCount('activities'),
      icon: Activity,
      gradient: 'bg-gradient-to-br from-orange-500 to-orange-600',
      change: { value: 12.3, trend: 'up' as const }
    },
    {
      title: 'Görevler',
      value: getTableCount('tasks'),
      icon: CheckCircle2,
      gradient: 'bg-gradient-to-br from-cyan-500 to-cyan-600',
      change: { value: 3.1, trend: 'down' as const }
    },
    {
      title: 'Görev Yorumları',
      value: getTableCount('task_comments'),
      icon: MessageSquare,
      gradient: 'bg-gradient-to-br from-pink-500 to-pink-600',
      change: { value: 8.7, trend: 'up' as const }
    },
    {
      title: 'Potansiyel Müşteriler',
      value: getTableCount('leads'),
      icon: TrendingUp,
      gradient: 'bg-gradient-to-br from-yellow-500 to-yellow-600',
      change: { value: 4.2, trend: 'up' as const }
    },
    {
      title: 'Toplam Kayıt',
      value: stats.reduce((sum, t) => sum + t.record_count, 0),
      icon: Database,
      gradient: 'bg-gradient-to-br from-slate-600 to-slate-700',
    }
  ]

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Welcome Section */}
          <div className="bg-gradient-to-r from-blue-600 to-green-600 rounded-xl p-6 text-white shadow-lg">
            <h1 className="text-2xl font-bold mb-2">
              Hoş Geldiniz, {session?.user?.name?.split(' ')[0] || 'Kullanıcı'}! 👋
            </h1>
            <p className="text-blue-100">
              Bitrix24 verileriniz sürekli olarak senkronize ediliyor. Tüm metriklerinizi buradan takip edebilirsiniz.
            </p>
          </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {metrics.map((metric) => (
            <MetricCard
              key={metric.title}
              title={metric.title}
              value={metric.value}
              icon={metric.icon}
              gradient={metric.gradient}
              change={metric.change}
              loading={loading}
            />
          ))}
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sync Status */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
              Senkronizasyon Durumu
            </h3>
            <div className="space-y-3">
              {stats.slice(0, 5).map((table) => (
                <div key={table.name} className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-slate-900 dark:text-white">
                      {table.display_name}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      Son güncelleme: {new Date(table.last_updated).toLocaleString('tr-TR')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-green-600 dark:text-green-400">
                      {table.record_count.toLocaleString('tr-TR')} kayıt
                    </span>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-4">
              Hızlı İşlemler
            </h3>
            <div className="space-y-3">
              <Link href="/data" className="block w-full text-left px-4 py-3 rounded-lg bg-gradient-to-r from-blue-50 to-green-50 dark:from-blue-950 dark:to-green-950 border border-blue-200 dark:border-blue-800 hover:shadow-md transition-all">
                <div className="font-medium text-slate-900 dark:text-white">
                  📊 Veri Görüntüle
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  Tabloları görüntüleyin ve filtreleyin
                </div>
              </Link>
              
              <Link href="/export" className="block w-full text-left px-4 py-3 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-950 dark:to-pink-950 border border-purple-200 dark:border-purple-800 hover:shadow-md transition-all">
                <div className="font-medium text-slate-900 dark:text-white">
                  ↗️ Google Sheets'e Aktar
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  Verileri Google E-Tablolar'a aktarın
                </div>
              </Link>
              
              <button className="w-full text-left px-4 py-3 rounded-lg bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-950 dark:to-red-950 border border-orange-200 dark:border-orange-800 hover:shadow-md transition-all">
                <div className="font-medium text-slate-900 dark:text-white">
                  🔄 Manuel Senkronizasyon
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  Şimdi senkronize et
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
    </ProtectedRoute>
  )
}
