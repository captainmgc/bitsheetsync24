'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import MetricCard from '@/components/dashboard/MetricCard'
import { useDashboard } from '@/hooks/useDashboard'
import { apiUrl } from '@/lib/config'
import { cn } from '@/lib/utils'
import { 
  Users, 
  Building2, 
  Briefcase, 
  Activity,
  CheckCircle2,
  MessageSquare,
  TrendingUp,
  Database,
  RefreshCw,
  AlertCircle,
  Clock,
  CheckCircle,
  ArrowRight
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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
  const userId = session?.user?.id || session?.user?.email

  // Use dashboard hook for advanced stats
  const {
    isLoading: dashboardLoading,
    recentActivities,
    syncStatus,
    fetchAllData
  } = useDashboard(userId || undefined)

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

  // Fetch dashboard data when userId is available
  useEffect(() => {
    if (userId) {
      fetchAllData()
    }
  }, [userId, fetchAllData])

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
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Senkronizasyon Durumu
              </h3>
              {syncStatus && (
                <Badge 
                  variant={syncStatus.overall_status === 'healthy' ? 'default' : 
                           syncStatus.overall_status === 'warning' ? 'secondary' : 'destructive'}
                  className={syncStatus.overall_status === 'healthy' ? 'bg-green-500' : 
                             syncStatus.overall_status === 'warning' ? 'bg-yellow-500' : ''}
                >
                  {syncStatus.overall_status === 'healthy' ? 'Sağlıklı' : 
                   syncStatus.overall_status === 'warning' ? 'Uyarı' : 
                   syncStatus.overall_status === 'error' ? 'Hata' : 'Pasif'}
                </Badge>
              )}
            </div>
            
            {/* Sync Summary Stats */}
            {syncStatus && (
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    %{(syncStatus.success_rate ?? 0).toFixed(0)}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">Başarı Oranı</div>
                </div>
                <div className="text-center p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">
                    {syncStatus.errors_last_24h}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">Son 24 Saat Hata</div>
                </div>
              </div>
            )}
            
            <div className="space-y-3">
              {syncStatus && syncStatus.configs.slice(0, 5).map((config) => (
                <div key={config.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {config.status === 'healthy' ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : config.status === 'warning' ? (
                      <AlertCircle className="h-4 w-4 text-yellow-500" />
                    ) : config.status === 'error' ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Clock className="h-4 w-4 text-slate-400" />
                    )}
                    <span className="font-medium text-slate-900 dark:text-white text-sm truncate max-w-[150px]">
                      {config.name}
                    </span>
                    {config.direction && (
                      <Badge variant="outline" className="text-xs">
                        {config.direction === 'bitrix_to_sheet' ? 'B → S' : 'S → B'}
                      </Badge>
                    )}
                  </div>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {config.last_sync 
                      ? new Date(config.last_sync).toLocaleString('tr-TR', {
                          day: '2-digit',
                          month: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : 'Hiç'}
                  </span>
                </div>
              ))}
              
              {/* Fallback to table stats if no sync configs */}
              {(!syncStatus || syncStatus.configs.length === 0) && stats.slice(0, 5).map((table) => (
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
              <Link href="/sheet-sync" className="block w-full text-left px-4 py-3 rounded-lg bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950 dark:to-blue-950 border border-green-200 dark:border-green-800 hover:shadow-md transition-all">
                <div className="font-medium text-slate-900 dark:text-white">
                  🔄 Sheet Senkronizasyonu
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  Çift yönlü senkronizasyon yönetimi
                </div>
              </Link>
              
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
              
              <button 
                onClick={() => fetchAllData()}
                disabled={dashboardLoading}
                className="w-full text-left px-4 py-3 rounded-lg bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-950 dark:to-red-950 border border-orange-200 dark:border-orange-800 hover:shadow-md transition-all disabled:opacity-50"
              >
                <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                  <RefreshCw className={cn("h-4 w-4", dashboardLoading && "animate-spin")} />
                  Yenile
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  Dashboard verilerini yenile
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Recent Activities Section */}
        {recentActivities && recentActivities.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-blue-600" />
                Son Aktiviteler
              </CardTitle>
              <CardDescription>
                Sistem aktiviteleri ve senkronizasyon logları
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {recentActivities.slice(0, 10).map((activity) => {
                  const getActivityIcon = () => {
                    if (activity.status === 'error') {
                      return <AlertCircle className="h-4 w-4 text-red-500" />
                    }
                    switch (activity.type) {
                      case 'sync_log':
                        return <RefreshCw className="h-4 w-4 text-blue-500" />
                      case 'config_update':
                        return <CheckCircle className="h-4 w-4 text-purple-500" />
                      default:
                        return <Activity className="h-4 w-4 text-slate-500" />
                    }
                  }

                  const formatTime = (dateStr: string) => {
                    const date = new Date(dateStr)
                    const now = new Date()
                    const diff = now.getTime() - date.getTime()
                    
                    const minutes = Math.floor(diff / 60000)
                    const hours = Math.floor(diff / 3600000)
                    const days = Math.floor(diff / 86400000)
                    
                    if (minutes < 60) return `${minutes} dk önce`
                    if (hours < 24) return `${hours} saat önce`
                    if (days < 7) return `${days} gün önce`
                    
                    return date.toLocaleString('tr-TR', {
                      day: '2-digit',
                      month: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })
                  }

                  return (
                    <div 
                      key={activity.id} 
                      className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-700 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                    >
                      <div className="mt-0.5">
                        {getActivityIcon()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-sm text-slate-900 dark:text-white">
                            {activity.config_name || activity.entity_type || 'Sistem'}
                          </span>
                          {activity.direction && (
                            <Badge variant="outline" className="text-xs">
                              {activity.direction === 'bitrix_to_sheet' ? 'B → S' : 'S → B'}
                            </Badge>
                          )}
                          {activity.status && (
                            <Badge 
                              variant={activity.status === 'success' ? 'default' : 'destructive'}
                              className={cn("text-xs", activity.status === 'success' && 'bg-green-500')}
                            >
                              {activity.status === 'success' ? 'Başarılı' : 'Hata'}
                            </Badge>
                          )}
                        </div>
                        {activity.message && (
                          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 truncate">
                            {activity.message}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {formatTime(activity.timestamp)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
    </ProtectedRoute>
  )
}
