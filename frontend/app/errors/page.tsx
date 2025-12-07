'use client'

import { useState, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { apiUrl } from '@/lib/config'
import { 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertCircle,
  Calendar,
  RotateCcw,
  Trash2,
  Eye,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Bug,
  Server,
  Database,
  Wifi,
  FileWarning
} from 'lucide-react'

interface ErrorLog {
  id: number
  error_type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  source: string
  message: string
  stack_trace: string | null
  entity_type: string | null
  entity_id: string | null
  created_at: string
  resolved: boolean
  resolved_at: string | null
  retry_count: number
  max_retries: number
}

interface ErrorStats {
  total_errors: number
  unresolved_errors: number
  critical_errors: number
  today_errors: number
  error_rate: number
}

export default function ErrorDashboardPage() {
  const [errors, setErrors] = useState<ErrorLog[]>([])
  const [stats, setStats] = useState<ErrorStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [resolvedFilter, setResolvedFilter] = useState<string>('')
  const [selectedError, setSelectedError] = useState<ErrorLog | null>(null)
  const [retrying, setRetrying] = useState<number | null>(null)

  useEffect(() => {
    fetchErrors()
    fetchStats()
  }, [page, severityFilter, resolvedFilter])

  async function fetchErrors() {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20'
      })
      
      if (severityFilter) {
        params.append('severity', severityFilter)
      }
      if (resolvedFilter === 'resolved') {
        params.append('resolved', 'true')
      } else if (resolvedFilter === 'unresolved') {
        params.append('resolved', 'false')
      }
      
      const response = await fetch(apiUrl(`/api/v1/errors/?${params.toString()}`))
      
      if (!response.ok) {
        throw new Error('Failed to fetch errors')
      }
      
      const data = await response.json()
      setErrors(data.errors || [])
      setTotalPages(data.total_pages || 1)
      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch errors:', err)
      setErrors([])
      setLoading(false)
    }
  }

  async function fetchStats() {
    try {
      const response = await fetch(apiUrl('/api/v1/errors/stats'))
      
      if (!response.ok) {
        throw new Error('Failed to fetch stats')
      }
      
      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
      setStats({
        total_errors: 0,
        unresolved_errors: 0,
        critical_errors: 0,
        today_errors: 0,
        error_rate: 0
      })
    }
  }

  async function retryError(errorId: number) {
    setRetrying(errorId)
    try {
      const response = await fetch(apiUrl(`/api/v1/errors/${errorId}/retry`), {
        method: 'POST'
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Retry failed')
      }
      
      // Refresh errors list
      await fetchErrors()
      await fetchStats()
    } catch (err) {
      console.error('Retry failed:', err)
      alert(err instanceof Error ? err.message : 'Yeniden deneme başarısız')
    } finally {
      setRetrying(null)
    }
  }

  async function resolveError(errorId: number) {
    try {
      const response = await fetch(apiUrl(`/api/v1/errors/${errorId}/resolve`), {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error('Failed to resolve error')
      }
      
      // Refresh errors list
      await fetchErrors()
      await fetchStats()
    } catch (err) {
      console.error('Resolve failed:', err)
    }
  }

  async function deleteError(errorId: number) {
    if (!confirm('Bu hata kaydını silmek istediğinizden emin misiniz?')) {
      return
    }
    
    try {
      const response = await fetch(apiUrl(`/api/v1/errors/${errorId}`), {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete error')
      }
      
      // Refresh errors list
      await fetchErrors()
      await fetchStats()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  function getSeverityBadge(severity: string) {
    switch (severity) {
      case 'critical':
        return <Badge className="bg-red-600 text-white">Kritik</Badge>
      case 'high':
        return <Badge className="bg-orange-500 text-white">Yüksek</Badge>
      case 'medium':
        return <Badge className="bg-yellow-500 text-white">Orta</Badge>
      case 'low':
        return <Badge className="bg-blue-500 text-white">Düşük</Badge>
      default:
        return <Badge variant="outline">{severity}</Badge>
    }
  }

  function getErrorIcon(errorType: string) {
    switch (errorType) {
      case 'API_ERROR':
        return <Wifi className="w-5 h-5 text-orange-500" />
      case 'DATABASE_ERROR':
        return <Database className="w-5 h-5 text-red-500" />
      case 'VALIDATION_ERROR':
        return <FileWarning className="w-5 h-5 text-yellow-500" />
      case 'NETWORK_ERROR':
        return <Server className="w-5 h-5 text-purple-500" />
      case 'RATE_LIMIT':
        return <Clock className="w-5 h-5 text-blue-500" />
      default:
        return <Bug className="w-5 h-5 text-slate-500" />
    }
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
                <AlertTriangle className="w-7 h-7 text-orange-500" />
                Hata Merkezi
              </h1>
              <p className="text-slate-600 mt-1">
                Sistem hatalarını izleyin ve yönetin
              </p>
            </div>
            <Button onClick={() => fetchErrors()} variant="outline">
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
                      <p className="text-sm text-slate-500">Toplam Hata</p>
                      <p className="text-2xl font-bold">{stats.total_errors}</p>
                    </div>
                    <Bug className="w-8 h-8 text-slate-400" />
                  </div>
                </CardContent>
              </Card>
              
              <Card className="border-orange-200 bg-orange-50">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-orange-700">Çözülmemiş</p>
                      <p className="text-2xl font-bold text-orange-600">{stats.unresolved_errors}</p>
                    </div>
                    <AlertCircle className="w-8 h-8 text-orange-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card className="border-red-200 bg-red-50">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-red-700">Kritik</p>
                      <p className="text-2xl font-bold text-red-600">{stats.critical_errors}</p>
                    </div>
                    <XCircle className="w-8 h-8 text-red-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Bugün</p>
                      <p className="text-2xl font-bold">{stats.today_errors}</p>
                    </div>
                    <Calendar className="w-8 h-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Hata Oranı</p>
                      <p className="text-2xl font-bold">{stats.error_rate}%</p>
                    </div>
                    <CheckCircle2 className="w-8 h-8 text-green-500" />
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
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="">Tüm Önem Seviyeleri</option>
                  <option value="critical">Kritik</option>
                  <option value="high">Yüksek</option>
                  <option value="medium">Orta</option>
                  <option value="low">Düşük</option>
                </select>

                <select
                  value={resolvedFilter}
                  onChange={(e) => setResolvedFilter(e.target.value)}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="">Tüm Durumlar</option>
                  <option value="unresolved">Çözülmemiş</option>
                  <option value="resolved">Çözülmüş</option>
                </select>

                {(severityFilter || resolvedFilter) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSeverityFilter('')
                      setResolvedFilter('')
                    }}
                  >
                    Temizle
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Error List */}
          <div className="space-y-4">
            {errors.map(error => (
              <Card 
                key={error.id}
                className={`transition-colors ${
                  error.severity === 'critical' ? 'border-red-300 bg-red-50/50' :
                  error.severity === 'high' ? 'border-orange-300 bg-orange-50/50' :
                  ''
                }`}
              >
                <CardContent className="pt-6">
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className="flex-shrink-0 mt-1">
                      {getErrorIcon(error.error_type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        {getSeverityBadge(error.severity)}
                        <Badge variant="outline">{error.error_type}</Badge>
                        <Badge variant="outline" className="text-slate-500">{error.source}</Badge>
                        {error.resolved && (
                          <Badge className="bg-green-100 text-green-700">
                            <CheckCircle2 className="w-3 h-3 mr-1" />
                            Çözüldü
                          </Badge>
                        )}
                      </div>

                      <p className="font-medium text-slate-900 mb-2">{error.message}</p>

                      <div className="flex items-center gap-4 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(error.created_at)}
                        </span>
                        {error.entity_type && (
                          <span>
                            {error.entity_type}
                            {error.entity_id && ` #${error.entity_id}`}
                          </span>
                        )}
                        <span>
                          Deneme: {error.retry_count}/{error.max_retries}
                        </span>
                      </div>

                      {/* Stack Trace (Expandable) */}
                      {selectedError?.id === error.id && error.stack_trace && (
                        <pre className="mt-4 p-3 bg-slate-900 text-green-400 text-xs rounded-lg overflow-x-auto">
                          {error.stack_trace}
                        </pre>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {error.stack_trace && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedError(
                            selectedError?.id === error.id ? null : error
                          )}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                      )}
                      
                      {!error.resolved && error.retry_count < error.max_retries && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => retryError(error.id)}
                          disabled={retrying === error.id}
                        >
                          {retrying === error.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RotateCcw className="w-4 h-4" />
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {errors.length === 0 && (
              <Card>
                <CardContent className="py-12 text-center">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-green-500" />
                  <p className="text-slate-600">Harika! Şu anda hata bulunmuyor.</p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
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
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
