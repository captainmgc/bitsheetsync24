'use client'

import { useState, useCallback, useEffect } from 'react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { apiUrl } from '@/lib/config'
import { cn } from '@/lib/utils'
import { 
  Search, 
  User, 
  Building2, 
  Briefcase, 
  CheckCircle2,
  MessageSquare,
  Phone,
  Mail,
  Calendar,
  TrendingUp,
  TrendingDown,
  Clock,
  AlertCircle,
  ChevronRight,
  Activity,
  FileText,
  Heart,
  DollarSign,
  Target,
  Users,
  Loader2,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'

interface CustomerSearchResult {
  id: number
  bitrix_id: string
  entity_type: 'contact' | 'company'
  name: string
  phone?: string
  email?: string
}

interface DealSummary {
  bitrix_id: string
  title: string
  stage_name: string
  stage_color?: string
  opportunity?: number
  currency?: string
  responsible_name?: string
  created_date?: string
  close_date?: string
  is_closed: boolean
  is_won: boolean
}

interface TaskSummary {
  bitrix_id: string
  title: string
  status_name: string
  priority_name: string
  responsible_name?: string
  created_by_name?: string
  deadline?: string
  created_date?: string
  comments_count: number
  status: number
}

interface ActivitySummary {
  bitrix_id: string
  subject: string
  type_name: string
  responsible_name?: string
  created?: string
  description?: string
}

interface TimelineEvent {
  event_type: string
  event_date?: string
  title: string
  subtitle?: string
  icon: string
  color?: string
  responsible?: string
  details: Record<string, any>
}

interface Customer360Data {
  customer: Record<string, any>
  summary: {
    total_deals: number
    open_deals: number
    won_deals: number
    lost_deals: number
    total_value: number
    won_value: number
    total_tasks: number
    completed_tasks: number
    pending_tasks: number
    total_activities: number
    health_score: number
    health_label: string
  }
  deals: DealSummary[]
  tasks: TaskSummary[]
  activities: ActivitySummary[]
  timeline: TimelineEvent[]
  task_comments: any[]
}

export default function Customer360Page() {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<CustomerSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSearchResult | null>(null)
  const [customerData, setCustomerData] = useState<Customer360Data | null>(null)
  const [loadingData, setLoadingData] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  
  // New: Entity type selection and list
  const [selectedEntityType, setSelectedEntityType] = useState<'contact' | 'company' | null>(null)
  const [entityList, setEntityList] = useState<CustomerSearchResult[]>([])
  const [listLoading, setListLoading] = useState(false)
  const [listTotal, setListTotal] = useState(0)
  const [listOffset, setListOffset] = useState(0)
  const [listSearch, setListSearch] = useState('')
  const listLimit = 20

  // Load entity list when type is selected
  const loadEntityList = async (entityType: 'contact' | 'company', offset: number = 0, search: string = '') => {
    setListLoading(true)
    try {
      const searchParam = search ? `&search=${encodeURIComponent(search)}` : ''
      const response = await fetch(apiUrl(`/api/v1/customer360/list/${entityType}s?limit=${listLimit}&offset=${offset}${searchParam}`))
      if (response.ok) {
        const data = await response.json()
        setEntityList(data.items)
        setListTotal(data.total)
        setListOffset(offset)
      }
    } catch (error) {
      console.error('Failed to load entity list:', error)
    } finally {
      setListLoading(false)
    }
  }

  // Handle entity type selection
  const handleEntityTypeSelect = (entityType: 'contact' | 'company') => {
    setSelectedEntityType(entityType)
    setSelectedCustomer(null)
    setCustomerData(null)
    setListSearch('')
    setListOffset(0)
    loadEntityList(entityType, 0, '')
  }

  // Handle list search
  const handleListSearch = (search: string) => {
    setListSearch(search)
    setListOffset(0)
    if (selectedEntityType) {
      loadEntityList(selectedEntityType, 0, search)
    }
  }

  // Debounced search (for combined search)
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([])
      return
    }

    const timer = setTimeout(async () => {
      setSearching(true)
      try {
        const response = await fetch(apiUrl(`/api/v1/customer360/search?q=${encodeURIComponent(searchQuery)}&limit=15`))
        if (response.ok) {
          const data = await response.json()
          setSearchResults(data)
        }
      } catch (error) {
        console.error('Search error:', error)
      } finally {
        setSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const selectCustomer = async (customer: CustomerSearchResult) => {
    setSelectedCustomer(customer)
    setSearchQuery('')
    setSearchResults([])
    setLoadingData(true)

    try {
      const endpoint = customer.entity_type === 'contact' 
        ? `/api/v1/customer360/contact/${customer.bitrix_id}`
        : `/api/v1/customer360/company/${customer.bitrix_id}`
      
      const response = await fetch(apiUrl(endpoint))
      if (response.ok) {
        const data = await response.json()
        setCustomerData(data)
      }
    } catch (error) {
      console.error('Failed to load customer data:', error)
    } finally {
      setLoadingData(false)
    }
  }

  const clearSelection = () => {
    setSelectedCustomer(null)
    setCustomerData(null)
    setActiveTab('overview')
    // Don't clear entity type and list - user might want to select another from same list
  }

  const clearAll = () => {
    setSelectedCustomer(null)
    setCustomerData(null)
    setSelectedEntityType(null)
    setEntityList([])
    setListSearch('')
    setActiveTab('overview')
  }

  const formatCurrency = (amount?: number, currency?: string) => {
    if (!amount) return '-'
    return new Intl.NumberFormat('tr-TR', {
      style: 'currency',
      currency: currency || 'TRY',
      minimumFractionDigits: 0
    }).format(amount)
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  }

  const getHealthColor = (score: number) => {
    if (score >= 70) return 'text-green-600 bg-green-100'
    if (score >= 40) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex flex-col gap-4">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Müşteri 360° Analizi
              </h1>
              <p className="text-muted-foreground mt-1">
                Müşteri ile ilgili tüm süreçleri tek ekranda görüntüleyin
              </p>
            </div>

            {/* Search Box */}
            <div className="relative max-w-xl">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Müşteri adı, telefon veya e-posta ile arayın..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-10"
                />
                {searching && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>

              {/* Search Results Dropdown */}
              {searchResults.length > 0 && (
                <Card className="absolute z-50 w-full mt-1 shadow-lg">
                  <ScrollArea className="max-h-80">
                    {searchResults.map((result) => (
                      <div
                        key={`${result.entity_type}-${result.bitrix_id}`}
                        className="p-3 hover:bg-muted cursor-pointer flex items-center gap-3 border-b last:border-0"
                        onClick={() => selectCustomer(result)}
                      >
                        <div className={cn(
                          "p-2 rounded-full",
                          result.entity_type === 'contact' ? 'bg-blue-100' : 'bg-purple-100'
                        )}>
                          {result.entity_type === 'contact' ? (
                            <User className="h-4 w-4 text-blue-600" />
                          ) : (
                            <Building2 className="h-4 w-4 text-purple-600" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium">{result.name}</p>
                          <div className="flex gap-3 text-sm text-muted-foreground">
                            {result.phone && <span>{result.phone}</span>}
                            {result.email && <span>{result.email}</span>}
                          </div>
                        </div>
                        <Badge variant="secondary">
                          {result.entity_type === 'contact' ? 'Kişi' : 'Şirket'}
                        </Badge>
                      </div>
                    ))}
                  </ScrollArea>
                </Card>
              )}
            </div>

            {/* Entity Type Selection */}
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">veya türe göre listele:</span>
              <div className="flex gap-2">
                <Button 
                  variant={selectedEntityType === 'contact' ? 'default' : 'outline'}
                  onClick={() => handleEntityTypeSelect('contact')}
                  className="gap-2"
                >
                  <User className="h-4 w-4" />
                  Kişiler
                </Button>
                <Button 
                  variant={selectedEntityType === 'company' ? 'default' : 'outline'}
                  onClick={() => handleEntityTypeSelect('company')}
                  className="gap-2"
                >
                  <Building2 className="h-4 w-4" />
                  Şirketler
                </Button>
                {selectedEntityType && (
                  <Button variant="ghost" size="icon" onClick={clearAll}>
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* Entity List - show when type is selected but no customer selected */}
          {selectedEntityType && !selectedCustomer && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    {selectedEntityType === 'contact' ? (
                      <><User className="h-5 w-5" /> Kişiler</>
                    ) : (
                      <><Building2 className="h-5 w-5" /> Şirketler</>
                    )}
                    <Badge variant="secondary">{listTotal} kayıt</Badge>
                  </CardTitle>
                  <div className="relative w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Listede ara..."
                      value={listSearch}
                      onChange={(e) => handleListSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {listLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <>
                    <div className="grid gap-2">
                      {entityList.map((item) => (
                        <div
                          key={item.bitrix_id}
                          className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted cursor-pointer transition-colors"
                          onClick={() => selectCustomer(item)}
                        >
                          <div className="flex items-center gap-3">
                            <div className={cn(
                              "p-2 rounded-full",
                              item.entity_type === 'contact' ? 'bg-blue-100' : 'bg-purple-100'
                            )}>
                              {item.entity_type === 'contact' ? (
                                <User className="h-4 w-4 text-blue-600" />
                              ) : (
                                <Building2 className="h-4 w-4 text-purple-600" />
                              )}
                            </div>
                            <div>
                              <p className="font-medium">{item.name || 'İsimsiz'}</p>
                              <div className="flex gap-3 text-sm text-muted-foreground">
                                {item.phone && (
                                  <span className="flex items-center gap-1">
                                    <Phone className="h-3 w-3" />
                                    {item.phone}
                                  </span>
                                )}
                                {item.email && (
                                  <span className="flex items-center gap-1">
                                    <Mail className="h-3 w-3" />
                                    {item.email}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="h-5 w-5 text-muted-foreground" />
                        </div>
                      ))}
                    </div>
                    
                    {/* Pagination */}
                    {listTotal > listLimit && (
                      <div className="flex items-center justify-between mt-4 pt-4 border-t">
                        <span className="text-sm text-muted-foreground">
                          {listOffset + 1} - {Math.min(listOffset + listLimit, listTotal)} / {listTotal}
                        </span>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={listOffset === 0}
                            onClick={() => loadEntityList(selectedEntityType, Math.max(0, listOffset - listLimit), listSearch)}
                          >
                            Önceki
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={listOffset + listLimit >= listTotal}
                            onClick={() => loadEntityList(selectedEntityType, listOffset + listLimit, listSearch)}
                          >
                            Sonraki
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Selected Customer View */}
          {selectedCustomer && (
            <div className="space-y-6">
              {/* Customer Header Card */}
              <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-0">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "p-4 rounded-full",
                        selectedCustomer.entity_type === 'contact' ? 'bg-blue-100' : 'bg-purple-100'
                      )}>
                        {selectedCustomer.entity_type === 'contact' ? (
                          <User className="h-8 w-8 text-blue-600" />
                        ) : (
                          <Building2 className="h-8 w-8 text-purple-600" />
                        )}
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold">
                          {customerData?.customer?.display_name || selectedCustomer.name}
                        </h2>
                        <div className="flex items-center gap-4 mt-1 text-muted-foreground">
                          <Badge variant="outline">
                            {selectedCustomer.entity_type === 'contact' ? 'Kişi' : 'Şirket'}
                          </Badge>
                          {customerData?.customer?.phone && (
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {customerData.customer.phone}
                            </span>
                          )}
                          {customerData?.customer?.email && (
                            <span className="flex items-center gap-1">
                              <Mail className="h-3 w-3" />
                              {customerData.customer.email}
                            </span>
                          )}
                        </div>
                        {customerData?.customer?.assigned_by_name && (
                          <p className="text-sm text-muted-foreground mt-1">
                            Sorumlu: <span className="font-medium">{customerData.customer.assigned_by_name}</span>
                          </p>
                        )}
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={clearSelection}>
                      <X className="h-5 w-5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {loadingData ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : customerData ? (
                <>
                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <Card>
                      <CardContent className="p-4 text-center">
                        <div className={cn("inline-flex p-2 rounded-full mb-2", getHealthColor(customerData.summary.health_score))}>
                          <Heart className="h-5 w-5" />
                        </div>
                        <p className="text-2xl font-bold">{customerData.summary.health_score}</p>
                        <p className="text-xs text-muted-foreground">{customerData.summary.health_label}</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4 text-center">
                        <div className="inline-flex p-2 rounded-full mb-2 bg-blue-100">
                          <Briefcase className="h-5 w-5 text-blue-600" />
                        </div>
                        <p className="text-2xl font-bold">{customerData.summary.total_deals}</p>
                        <p className="text-xs text-muted-foreground">Toplam Anlaşma</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4 text-center">
                        <div className="inline-flex p-2 rounded-full mb-2 bg-green-100">
                          <TrendingUp className="h-5 w-5 text-green-600" />
                        </div>
                        <p className="text-2xl font-bold">{customerData.summary.won_deals}</p>
                        <p className="text-xs text-muted-foreground">Kazanılan</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4 text-center">
                        <div className="inline-flex p-2 rounded-full mb-2 bg-yellow-100">
                          <DollarSign className="h-5 w-5 text-yellow-600" />
                        </div>
                        <p className="text-lg font-bold">{formatCurrency(customerData.summary.won_value)}</p>
                        <p className="text-xs text-muted-foreground">Toplam Değer</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4 text-center">
                        <div className="inline-flex p-2 rounded-full mb-2 bg-purple-100">
                          <CheckCircle2 className="h-5 w-5 text-purple-600" />
                        </div>
                        <p className="text-2xl font-bold">{customerData.summary.completed_tasks}/{customerData.summary.total_tasks}</p>
                        <p className="text-xs text-muted-foreground">Görevler</p>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4 text-center">
                        <div className="inline-flex p-2 rounded-full mb-2 bg-orange-100">
                          <Activity className="h-5 w-5 text-orange-600" />
                        </div>
                        <p className="text-2xl font-bold">{customerData.summary.total_activities}</p>
                        <p className="text-xs text-muted-foreground">Aktiviteler</p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Tabs */}
                  <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid grid-cols-5 w-full max-w-2xl">
                      <TabsTrigger value="overview">Özet</TabsTrigger>
                      <TabsTrigger value="deals">Anlaşmalar</TabsTrigger>
                      <TabsTrigger value="tasks">Görevler</TabsTrigger>
                      <TabsTrigger value="activities">Aktiviteler</TabsTrigger>
                      <TabsTrigger value="timeline">Zaman Çizelgesi</TabsTrigger>
                    </TabsList>

                    {/* Overview Tab */}
                    <TabsContent value="overview" className="space-y-4 mt-4">
                      <div className="grid md:grid-cols-2 gap-4">
                        {/* Recent Deals */}
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <Briefcase className="h-5 w-5" />
                              Son Anlaşmalar
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            {customerData.deals.slice(0, 5).map((deal) => (
                              <div key={deal.bitrix_id} className="flex items-center justify-between py-2 border-b last:border-0">
                                <div>
                                  <p className="font-medium">{deal.title}</p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <Badge 
                                      style={{ backgroundColor: deal.stage_color || '#999' }}
                                      className="text-white text-xs"
                                    >
                                      {deal.stage_name}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">
                                      {deal.responsible_name}
                                    </span>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <p className="font-semibold">{formatCurrency(deal.opportunity, deal.currency)}</p>
                                  <p className="text-xs text-muted-foreground">{formatDate(deal.created_date)}</p>
                                </div>
                              </div>
                            ))}
                            {customerData.deals.length === 0 && (
                              <p className="text-muted-foreground text-center py-4">Anlaşma bulunamadı</p>
                            )}
                          </CardContent>
                        </Card>

                        {/* Recent Tasks */}
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <CheckCircle2 className="h-5 w-5" />
                              Son Görevler
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            {customerData.tasks.slice(0, 5).map((task) => (
                              <div key={task.bitrix_id} className="flex items-center justify-between py-2 border-b last:border-0">
                                <div className="flex-1">
                                  <p className="font-medium line-clamp-1">{task.title}</p>
                                  <div className="flex items-center gap-2 mt-1">
                                    <Badge variant={task.status === 5 ? 'default' : 'secondary'}>
                                      {task.status_name}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">
                                      {task.responsible_name}
                                    </span>
                                  </div>
                                </div>
                                {task.deadline && (
                                  <div className="text-right">
                                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                      <Clock className="h-3 w-3" />
                                      {formatDate(task.deadline)}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                            {customerData.tasks.length === 0 && (
                              <p className="text-muted-foreground text-center py-4">Görev bulunamadı</p>
                            )}
                          </CardContent>
                        </Card>
                      </div>

                      {/* Task Comments */}
                      {customerData.task_comments.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                              <MessageSquare className="h-5 w-5" />
                              Görev Yorumları
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <ScrollArea className="h-48">
                              {customerData.task_comments.slice(0, 10).map((comment, idx) => (
                                <div key={idx} className="py-2 border-b last:border-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-medium text-sm">{comment.author_name}</span>
                                    <span className="text-xs text-muted-foreground">{formatDate(comment.post_date)}</span>
                                  </div>
                                  <p className="text-sm text-muted-foreground line-clamp-2">{comment.message}</p>
                                  <p className="text-xs text-blue-600 mt-1">📋 {comment.task_title}</p>
                                </div>
                              ))}
                            </ScrollArea>
                          </CardContent>
                        </Card>
                      )}
                    </TabsContent>

                    {/* Deals Tab */}
                    <TabsContent value="deals" className="mt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Tüm Anlaşmalar ({customerData.deals.length})</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            {customerData.deals.map((deal) => (
                              <div key={deal.bitrix_id} className="p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
                                <div className="flex items-start justify-between">
                                  <div>
                                    <h4 className="font-semibold">{deal.title}</h4>
                                    <div className="flex flex-wrap items-center gap-2 mt-2">
                                      <Badge 
                                        style={{ backgroundColor: deal.stage_color || '#999' }}
                                        className="text-white"
                                      >
                                        {deal.stage_name}
                                      </Badge>
                                      {deal.is_won && <Badge className="bg-green-500">Kazanıldı</Badge>}
                                      {deal.is_closed && !deal.is_won && <Badge variant="destructive">Kapatıldı</Badge>}
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <p className="text-xl font-bold">{formatCurrency(deal.opportunity, deal.currency)}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <User className="h-3 w-3" />
                                    {deal.responsible_name}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Calendar className="h-3 w-3" />
                                    Oluşturma: {formatDate(deal.created_date)}
                                  </span>
                                  {deal.close_date && (
                                    <span className="flex items-center gap-1">
                                      <Target className="h-3 w-3" />
                                      Kapanış: {formatDate(deal.close_date)}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                            {customerData.deals.length === 0 && (
                              <p className="text-muted-foreground text-center py-8">Bu müşteriye ait anlaşma bulunamadı</p>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    {/* Tasks Tab */}
                    <TabsContent value="tasks" className="mt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Tüm Görevler ({customerData.tasks.length})</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            {customerData.tasks.map((task) => (
                              <div key={task.bitrix_id} className="p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <h4 className="font-semibold">{task.title}</h4>
                                    <div className="flex flex-wrap items-center gap-2 mt-2">
                                      <Badge variant={task.status === 5 ? 'default' : task.status === 3 ? 'secondary' : 'outline'}>
                                        {task.status_name}
                                      </Badge>
                                      <Badge variant="outline">{task.priority_name}</Badge>
                                      {task.comments_count > 0 && (
                                        <Badge variant="secondary" className="flex items-center gap-1">
                                          <MessageSquare className="h-3 w-3" />
                                          {task.comments_count}
                                        </Badge>
                                      )}
                                    </div>
                                  </div>
                                  {task.deadline && (
                                    <div className="text-right">
                                      <p className="text-sm text-muted-foreground">Son Tarih</p>
                                      <p className="font-medium">{formatDate(task.deadline)}</p>
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <User className="h-3 w-3" />
                                    Sorumlu: {task.responsible_name}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Users className="h-3 w-3" />
                                    Oluşturan: {task.created_by_name}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Calendar className="h-3 w-3" />
                                    {formatDate(task.created_date)}
                                  </span>
                                </div>
                              </div>
                            ))}
                            {customerData.tasks.length === 0 && (
                              <p className="text-muted-foreground text-center py-8">Bu müşteriye ait görev bulunamadı</p>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    {/* Activities Tab */}
                    <TabsContent value="activities" className="mt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Tüm Aktiviteler ({customerData.activities.length})</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3">
                            {customerData.activities.map((activity) => (
                              <div key={activity.bitrix_id} className="p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
                                <div className="flex items-start gap-3">
                                  <div className={cn(
                                    "p-2 rounded-full",
                                    activity.type_name === 'Arama' ? 'bg-green-100' :
                                    activity.type_name === 'E-posta' ? 'bg-blue-100' :
                                    activity.type_name === 'Toplantı' ? 'bg-purple-100' :
                                    'bg-gray-100'
                                  )}>
                                    {activity.type_name === 'Arama' && <Phone className="h-4 w-4 text-green-600" />}
                                    {activity.type_name === 'E-posta' && <Mail className="h-4 w-4 text-blue-600" />}
                                    {activity.type_name === 'Toplantı' && <Users className="h-4 w-4 text-purple-600" />}
                                    {!['Arama', 'E-posta', 'Toplantı'].includes(activity.type_name) && <Activity className="h-4 w-4 text-gray-600" />}
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center justify-between">
                                      <h4 className="font-semibold">{activity.subject}</h4>
                                      <Badge variant="outline">{activity.type_name}</Badge>
                                    </div>
                                    {activity.description && (
                                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{activity.description}</p>
                                    )}
                                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                                      <span className="flex items-center gap-1">
                                        <User className="h-3 w-3" />
                                        {activity.responsible_name}
                                      </span>
                                      <span className="flex items-center gap-1">
                                        <Calendar className="h-3 w-3" />
                                        {formatDate(activity.created)}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                            {customerData.activities.length === 0 && (
                              <p className="text-muted-foreground text-center py-8">Bu müşteriye ait aktivite bulunamadı</p>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    {/* Timeline Tab */}
                    <TabsContent value="timeline" className="mt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Zaman Çizelgesi</CardTitle>
                          <CardDescription>Tüm etkileşimlerin kronolojik görünümü</CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="relative">
                            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />
                            <div className="space-y-4">
                              {customerData.timeline.map((event, idx) => (
                                <div key={idx} className="relative pl-10">
                                  <div 
                                    className="absolute left-0 p-2 rounded-full bg-white border-2"
                                    style={{ borderColor: event.color || '#999' }}
                                  >
                                    <span className="text-lg">{event.icon}</span>
                                  </div>
                                  <div className="p-3 rounded-lg border bg-card">
                                    <div className="flex items-center justify-between">
                                      <h4 className="font-medium">{event.title}</h4>
                                      <Badge variant="outline">{
                                        event.event_type === 'deal' ? 'Anlaşma' :
                                        event.event_type === 'task' ? 'Görev' :
                                        event.event_type === 'activity' ? 'Aktivite' :
                                        event.event_type === 'comment' ? 'Yorum' : event.event_type
                                      }</Badge>
                                    </div>
                                    {event.subtitle && (
                                      <p className="text-sm text-muted-foreground mt-1">{event.subtitle}</p>
                                    )}
                                    <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                                      {event.responsible && (
                                        <span className="flex items-center gap-1">
                                          <User className="h-3 w-3" />
                                          {event.responsible}
                                        </span>
                                      )}
                                      <span className="flex items-center gap-1">
                                        <Clock className="h-3 w-3" />
                                        {formatDate(event.event_date)}
                                      </span>
                                      {event.details?.amount && (
                                        <span className="font-medium text-green-600">{event.details.amount}</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                              {customerData.timeline.length === 0 && (
                                <p className="text-muted-foreground text-center py-8">Zaman çizelgesi boş</p>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>
                  </Tabs>
                </>
              ) : null}
            </div>
          )}

          {/* Empty State - only show when nothing is selected */}
          {!selectedCustomer && !selectedEntityType && (
            <Card className="border-dashed">
              <CardContent className="py-16 text-center">
                <div className="inline-flex p-4 rounded-full bg-muted mb-4">
                  <Search className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Müşteri Seçin</h3>
                <p className="text-muted-foreground max-w-md mx-auto">
                  Yukarıdaki arama kutusunu kullanarak bir kişi veya şirket arayın, 
                  ya da "Kişiler" veya "Şirketler" butonlarına tıklayarak listeden seçim yapın.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
