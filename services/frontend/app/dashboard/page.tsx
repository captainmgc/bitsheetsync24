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
          <Card className="bg-gradient-to-r from-blue-600 to-green-600 border-none text-white shadow-lg">
            <CardContent className="p-8">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold mb-2">
                    Hoş Geldiniz, {session?.user?.name?.split(' ')[0] || 'Kullanıcı'}! 👋
                  </h1>
                  <p className="text-blue-50 text-lg opacity-90">
                    Bitrix24 verileriniz sürekli olarak senkronize ediliyor. Tüm metriklerinizi buradan takip edebilirsiniz.
                  </p>
                </div>
                <div className="hidden md:block p-3 bg-white/10 rounded-full backdrop-blur-sm">
                  <Activity className="h-8 w-8 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

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
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg font-bold">
                Senkronizasyon Durumu
              </CardTitle>
              {syncStatus && (
                <Badge 
                  variant={syncStatus.overall_status === 'healthy' ? 'default' : 
                           syncStatus.overall_status === 'warning' ? 'secondary' : 'destructive'}
                  className={syncStatus.overall_status === 'healthy' ? 'bg-green-500 hover:bg-green-600' : 
                             syncStatus.overall_status === 'warning' ? 'bg-yellow-500 hover:bg-yellow-600' : ''}
                >
                  {syncStatus.overall_status === 'healthy' ? 'Sağlıklı' : 
                   syncStatus.overall_status === 'warning' ? 'Uyarı' : 
                   syncStatus.overall_status === 'error' ? 'Hata' : 'Pasif'}
                </Badge>
              )}
            </CardHeader>
            <CardContent>
            
            {/* Sync Summary Stats */}
            {syncStatus && (
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="text-center p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700">
                  <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                    %{(syncStatus.success_rate ?? 0).toFixed(0)}
                  </div>
                  <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mt-1">Başarı Oranı</div>
                </div>
                <div className="text-center p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700">
                  <div className="text-3xl font-bold text-red-600 dark:text-red-400">
                    {syncStatus.errors_last_24h}
                  </div>
                  <div className="text-sm font-medium text-slate-600 dark:text-slate-400 mt-1">Son 24 Saat Hata</div>
                </div>
              </div>
            )}
            
            <div className="space-y-4">
              {syncStatus && syncStatus.configs.slice(0, 5).map((config) => (
                <div key={config.id} className="flex items-center justify-between p-2 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-full bg-slate-100 dark:bg-slate-800", 
                      config.status === 'healthy' ? "bg-green-100 dark:bg-green-900/30" : 
                      config.status === 'warning' ? "bg-yellow-100 dark:bg-yellow-900/30" : 
                      config.status === 'error' ? "bg-red-100 dark:bg-red-900/30" : ""
                    )}>
                      {config.status === 'healthy' ? (
                        <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                      ) : config.status === 'warning' ? (
                        <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                      ) : config.status === 'error' ? (
                        <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                      ) : (
                        <Clock className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                    <div>
                      <div className="font-medium text-slate-900 dark:text-white text-sm">
                        {config.name}
                      </div>
                      {config.direction && (
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          {config.direction === 'bitrix_to_sheet' ? 'Bitrix → Sheet' : 'Sheet → Bitrix'}
                        </div>
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full">
                    {config.last_sync 
                      ? new Date(config.last_sync).toLocaleString('tr-TR', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : '-'}
                  </span>
                </div>
              ))}
              
              {/* Fallback to table stats if no sync configs */}
              {(!syncStatus || syncStatus.configs.length === 0) && stats.slice(0, 5).map((table) => (
                <div key={table.name} className="flex items-center justify-between p-2 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors">
                  <div>
                    <div className="font-medium text-slate-900 dark:text-white">
                      {table.display_name}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(table.last_updated).toLocaleDateString('tr-TR')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-normal">
                      {table.record_count.toLocaleString('tr-TR')} kayıt
                    </Badge>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-lg font-bold">
                Hızlı İşlemler
              </CardTitle>
              <CardDescription>
                Sık kullanılan işlemlere hızlı erişim
              </CardDescription>
            </CardHeader>
            <CardContent>
            <div className="space-y-3">
              <Link href="/sheet-sync" className="group block w-full text-left p-4 rounded-xl bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950/30 dark:to-blue-950/30 border border-green-100 dark:border-green-900/50 hover:shadow-md hover:border-green-200 dark:hover:border-green-800 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm group-hover:scale-110 transition-transform">
                      <RefreshCw className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-white">
                        Sheet Senkronizasyonu
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                        Çift yönlü senkronizasyon yönetimi
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-5 w-5 text-slate-400 group-hover:text-green-600 dark:group-hover:text-green-400 transform group-hover:translate-x-1 transition-all" />
                </div>
              </Link>
              
              <Link href="/data" className="group block w-full text-left p-4 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border border-blue-100 dark:border-blue-900/50 hover:shadow-md hover:border-blue-200 dark:hover:border-blue-800 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm group-hover:scale-110 transition-transform">
                      <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-white">
                        Veri Görüntüle
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                        Tabloları görüntüleyin ve filtreleyin
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-5 w-5 text-slate-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transform group-hover:translate-x-1 transition-all" />
                </div>
              </Link>
              
              <Link href="/export" className="group block w-full text-left p-4 rounded-xl bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-950/30 dark:to-pink-950/30 border border-purple-100 dark:border-purple-900/50 hover:shadow-md hover:border-purple-200 dark:hover:border-purple-800 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm group-hover:scale-110 transition-transform">
                      <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-white">
                        Google Sheets'e Aktar
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                        Verileri Google E-Tablolar'a aktarın
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-5 w-5 text-slate-400 group-hover:text-purple-600 dark:group-hover:text-purple-400 transform group-hover:translate-x-1 transition-all" />
                </div>
              </Link>
              
              <button 
                onClick={() => fetchAllData()}
                disabled={dashboardLoading}
                className="group w-full text-left p-4 rounded-xl bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-950/30 dark:to-red-950/30 border border-orange-100 dark:border-orange-900/50 hover:shadow-md hover:border-orange-200 dark:hover:border-orange-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm group-hover:scale-110 transition-transform">
                      <RefreshCw className={cn("h-5 w-5 text-orange-600 dark:text-orange-400", dashboardLoading && "animate-spin")} />
                    </div>
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-white">
                        Verileri Yenile
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                        Dashboard verilerini güncelleyin
                      </div>
                    </div>
                  </div>
                </div>
              </button>
            </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activities Section */}
        {recentActivities && recentActivities.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-bold">
                <Clock className="h-5 w-5 text-blue-600" />
                Son Aktiviteler
              </CardTitle>
              <CardDescription>
                Sistem aktiviteleri ve senkronizasyon logları
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                {recentActivities.slice(0, 10).map((activity) => {
                  const getActivityIcon = () => {
                    if (activity.status === 'error') {
                      return <AlertCircle className="h-5 w-5 text-red-500" />
                    }
                    switch (activity.type) {
                      case 'sync_log':
                        return <RefreshCw className="h-5 w-5 text-blue-500" />
                      case 'config_update':
                        return <CheckCircle className="h-5 w-5 text-purple-500" />
                      default:
                        return <Activity className="h-5 w-5 text-slate-500" />
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
                      className="group flex items-start gap-4 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 hover:shadow-md transition-all"
                    >
                      <div className={cn("mt-1 p-2 rounded-full bg-white dark:bg-slate-800 shadow-sm", 
                        activity.status === 'error' ? "bg-red-50 dark:bg-red-900/20" : 
                        activity.type === 'sync_log' ? "bg-blue-50 dark:bg-blue-900/20" : 
                        "bg-slate-50 dark:bg-slate-900/20"
                      )}>
                        {getActivityIcon()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-slate-900 dark:text-white">
                              {activity.config_name || activity.entity_type || 'Sistem'}
                            </span>
                            {activity.direction && (
                              <Badge variant="outline" className="text-xs font-normal">
                                {activity.direction === 'bitrix_to_sheet' ? 'Bitrix → Sheet' : 'Sheet → Bitrix'}
                              </Badge>
                            )}
                          </div>
                          <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap ml-2">
                            {formatTime(activity.timestamp)}
                          </span>
                        </div>
                        
                        <div className="flex items-center gap-2 mb-1">
                          {activity.status && (
                            <Badge 
                              variant={activity.status === 'success' ? 'default' : 'destructive'}
                              className={cn("text-[10px] px-1.5 py-0 h-5", 
                                activity.status === 'success' ? "bg-green-500 hover:bg-green-600" : ""
                              )}
                            >
                              {activity.status === 'success' ? 'Başarılı' : 'Hata'}
                            </Badge>
                          )}
                        </div>

                        {activity.message && (
                          <p className="text-sm text-slate-600 dark:text-slate-300 line-clamp-2">
                            {activity.message}
                          </p>
                        )}
                      </div>
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
