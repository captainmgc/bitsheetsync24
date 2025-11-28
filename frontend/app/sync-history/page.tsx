'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { apiUrl } from '@/lib/config'
import { 
  History, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Database,
  Calendar,
  Timer,
  FileSpreadsheet,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  TrendingUp,
  BarChart3
} from 'lucide-react'

interface SyncLog {
  id: number
  entity_name: string
  sync_type: string
  status: 'running' | 'completed' | 'failed'
  records_processed: number
  records_total: number
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  error_message: string | null
}

interface SyncStats {
  total_syncs: number
  successful_syncs: number
  failed_syncs: number
  total_records: number
  avg_duration: number
}

export default function SyncHistoryPage() {
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [stats, setStats] = useState<SyncStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [entityFilter, setEntityFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    fetchLogs()
    fetchStats()
  }, [page, entityFilter, statusFilter])

  async function fetchLogs() {
    try {
      // TODO: Replace with actual API endpoint when available
      // For now, simulate with mock data
      const mockLogs: SyncLog[] = [
        {
          id: 1,
          entity_name: 'deals',
          sync_type: 'incremental',
          status: 'completed',
          records_processed: 150,
          records_total: 150,
          started_at: new Date(Date.now() - 300000).toISOString(),
          completed_at: new Date(Date.now() - 295000).toISOString(),
          duration_seconds: 5,
          error_message: null
        },
        {
          id: 2,
          entity_name: 'contacts',
          sync_type: 'incremental',
          status: 'completed',
          records_processed: 45,
          records_total: 45,
          started_at: new Date(Date.now() - 600000).toISOString(),
          completed_at: new Date(Date.now() - 597000).toISOString(),
          duration_seconds: 3,
          error_message: null
        },
        {
          id: 3,
          entity_name: 'activities',
          sync_type: 'incremental',
          status: 'completed',
          records_processed: 523,
          records_total: 523,
          started_at: new Date(Date.now() - 900000).toISOString(),
          completed_at: new Date(Date.now() - 885000).toISOString(),
          duration_seconds: 15,
          error_message: null
        },
        {
          id: 4,
          entity_name: 'tasks',
          sync_type: 'incremental',
          status: 'failed',
          records_processed: 120,
          records_total: 200,
          started_at: new Date(Date.now() - 1200000).toISOString(),
          completed_at: new Date(Date.now() - 1190000).toISOString(),
          duration_seconds: 10,
          error_message: 'Connection timeout after 30 seconds'
        },
        {
          id: 5,
          entity_name: 'task_comments',
          sync_type: 'incremental',
          status: 'completed',
          records_processed: 89,
          records_total: 89,
          started_at: new Date(Date.now() - 1500000).toISOString(),
          completed_at: new Date(Date.now() - 1493000).toISOString(),
          duration_seconds: 7,
          error_message: null
        }
      ]

      // Filter
      let filtered = mockLogs
      if (entityFilter) {
        filtered = filtered.filter(l => l.entity_name === entityFilter)
      }
      if (statusFilter) {
        filtered = filtered.filter(l => l.status === statusFilter)
      }

      setLogs(filtered)
      setTotalPages(1)
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch logs:', err)
      setLoading(false)
    }
  }

  async function fetchStats() {
    // Mock stats
    setStats({
      total_syncs: 1247,
      successful_syncs: 1235,
      failed_syncs: 12,
      total_records: 389542,
      avg_duration: 8.5
    })
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  function formatDuration(seconds: number | null) {
    if (seconds === null) return '-'
    if (seconds < 60) return `${seconds}s`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-700"><CheckCircle2 className="w-3 h-3 mr-1" />Tamamlandı</Badge>
      case 'running':
        return <Badge className="bg-blue-100 text-blue-700"><Loader2 className="w-3 h-3 mr-1 animate-spin" />Çalışıyor</Badge>
      case 'failed':
        return <Badge className="bg-red-100 text-red-700"><XCircle className="w-3 h-3 mr-1" />Başarısız</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  function getEntityIcon(entity: string) {
    const icons: Record<string, string> = {
      deals: '💼',
      contacts: '👥',
      companies: '🏢',
      activities: '📊',
      tasks: '✅',
      task_comments: '💬',
      leads: '🎯',
      users: '👤',
      departments: '🏛️'
    }
    return icons[entity] || '📁'
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center h-96">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <History className="w-7 h-7 text-blue-500" />
                Senkronizasyon Geçmişi
              </h1>
              <p className="text-slate-600 mt-1">
                Bitrix24 veri senkronizasyonlarını izleyin
              </p>
            </div>
            <Button onClick={() => fetchLogs()} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Yenile
            </Button>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-5 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Toplam Sync</p>
                      <p className="text-2xl font-bold">{stats.total_syncs.toLocaleString()}</p>
                    </div>
                    <BarChart3 className="w-8 h-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Başarılı</p>
                      <p className="text-2xl font-bold text-green-600">{stats.successful_syncs.toLocaleString()}</p>
                    </div>
                    <CheckCircle2 className="w-8 h-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Başarısız</p>
                      <p className="text-2xl font-bold text-red-600">{stats.failed_syncs.toLocaleString()}</p>
                    </div>
                    <XCircle className="w-8 h-8 text-red-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Toplam Kayıt</p>
                      <p className="text-2xl font-bold">{stats.total_records.toLocaleString()}</p>
                    </div>
                    <Database className="w-8 h-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Ort. Süre</p>
                      <p className="text-2xl font-bold">{stats.avg_duration}s</p>
                    </div>
                    <Timer className="w-8 h-8 text-orange-500" />
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-medium">Filtreler:</span>
                </div>
                
                <select
                  value={entityFilter}
                  onChange={(e) => setEntityFilter(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="">Tüm Tablolar</option>
                  <option value="deals">Anlaşmalar</option>
                  <option value="contacts">Müşteriler</option>
                  <option value="companies">Şirketler</option>
                  <option value="activities">Aktiviteler</option>
                  <option value="tasks">Görevler</option>
                  <option value="task_comments">Yorumlar</option>
                  <option value="leads">Potansiyeller</option>
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="">Tüm Durumlar</option>
                  <option value="completed">Tamamlandı</option>
                  <option value="running">Çalışıyor</option>
                  <option value="failed">Başarısız</option>
                </select>

                {(entityFilter || statusFilter) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEntityFilter('')
                      setStatusFilter('')
                    }}
                  >
                    Temizle
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Sync Logs Table */}
          <Card>
            <CardHeader>
              <CardTitle>Sync Kayıtları</CardTitle>
              <CardDescription>Son senkronizasyon işlemleri</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Tablo</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Tip</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Durum</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Kayıt</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Başlangıç</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Süre</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">Hata</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.id} className="border-b hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{getEntityIcon(log.entity_name)}</span>
                            <span className="font-medium">{log.entity_name}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="outline">{log.sync_type}</Badge>
                        </td>
                        <td className="py-3 px-4">
                          {getStatusBadge(log.status)}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-medium">{log.records_processed}</span>
                          <span className="text-slate-400"> / {log.records_total}</span>
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-600">
                          {formatDate(log.started_at)}
                        </td>
                        <td className="py-3 px-4 text-sm">
                          {formatDuration(log.duration_seconds)}
                        </td>
                        <td className="py-3 px-4">
                          {log.error_message ? (
                            <span className="text-sm text-red-600 truncate max-w-xs block" title={log.error_message}>
                              {log.error_message}
                            </span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {logs.length === 0 && (
                <div className="text-center py-12 text-slate-500">
                  <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Henüz senkronizasyon kaydı yok</p>
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Önceki
                  </Button>
                  <span className="text-sm text-slate-600">
                    Sayfa {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Sonraki
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
