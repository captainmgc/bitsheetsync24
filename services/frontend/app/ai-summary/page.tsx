'use client'

import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { apiUrl } from '@/lib/config'
import { 
  Sparkles, 
  Send, 
  History, 
  Search, 
  Building2, 
  User, 
  Phone,
  Mail,
  Calendar,
  TrendingUp,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Filter,
  Loader2,
  Copy,
  ExternalLink
} from 'lucide-react'

// Types
interface Deal {
  id: number
  title: string
  stage_id: string | null
  stage_name: string | null
  opportunity: string | null
  currency: string | null
  contact_name: string | null
  company_name: string | null
  assigned_by_name: string | null
  date_create: string | null
  date_modify: string | null
  has_summary: boolean
  last_summary_at: string | null
}

interface DealDetails {
  deal: any
  contact: any
  company: any
  responsible_name: string | null
  all_contact_deals: any[]
  stats: {
    activities_count: number
    tasks_count: number
    task_comments_count: number
    total_deals_count: number
  }
  recent_activities: any[]
  recent_tasks: any[]
}

interface AIProvider {
  provider: string
  api_key_configured: boolean
  available_models: string[]
  default_model: string
}

interface Summary {
  id: number
  deal_id: number
  deal_title: string
  summary: string
  summary_preview?: string
  provider: string
  model: string
  created_at: string
  written_to_bitrix: boolean
}

interface Stage {
  stage_id: string
  stage_name: string
  deal_count: number
}

interface Category {
  category_id: string
  category_name: string
  deal_count: number
}

export default function AISummaryPage() {
  // State
  const [deals, setDeals] = useState<Deal[]>([])
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null)
  const [dealDetails, setDealDetails] = useState<DealDetails | null>(null)
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [stages, setStages] = useState<Stage[]>([])
  const [summaryHistory, setSummaryHistory] = useState<Summary[]>([])
  const [generatedSummary, setGeneratedSummary] = useState<Summary | null>(null)
  
  // UI State
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [writingToBitrix, setWritingToBitrix] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedStage, setSelectedStage] = useState<string>('')
  const [dealStatus, setDealStatus] = useState<string>('active') // active, won, lost, all
  const [selectedProvider, setSelectedProvider] = useState<string>('openrouter')
  const [selectedModel, setSelectedModel] = useState<string>('x-ai/grok-4.1-fast:free')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [activeTab, setActiveTab] = useState<'generate' | 'history'>('generate')
  const [error, setError] = useState<string | null>(null)

  // Load initial data
  useEffect(() => {
    Promise.all([
      fetchDeals(),
      fetchProviders(),
      fetchCategories(),
      fetchStages(),
      fetchHistory()
    ]).finally(() => setLoading(false))
  }, [])

  // Fetch deals when filters change
  useEffect(() => {
    fetchDeals()
  }, [page, searchTerm, selectedCategory, selectedStage, dealStatus])

  // Fetch categories and stages when status changes
  useEffect(() => {
    fetchCategories()
    fetchStages()
  }, [dealStatus])

  // Fetch stages when category changes
  useEffect(() => {
    fetchStages()
    setSelectedStage('') // Reset stage when category changes
  }, [selectedCategory])

  // Fetch deal details when selection changes
  useEffect(() => {
    if (selectedDeal) {
      fetchDealDetails(selectedDeal.id)
    }
  }, [selectedDeal])

  // API Calls
  async function fetchDeals() {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '15',
        status: dealStatus,
        ...(searchTerm && { search: searchTerm }),
        ...(selectedCategory && { category_id: selectedCategory }),
        ...(selectedStage && { stage_id: selectedStage })
      })
      
      const res = await fetch(apiUrl(`/api/v1/ai-summary/deals?${params}`))
      const data = await res.json()
      setDeals(data.items || [])
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch deals:', err)
      setError('Anlaşmalar yüklenemedi')
    }
  }

  async function fetchDealDetails(dealId: number) {
    try {
      const res = await fetch(apiUrl(`/api/v1/ai-summary/deals/${dealId}`))
      const data = await res.json()
      setDealDetails(data)
    } catch (err) {
      console.error('Failed to fetch deal details:', err)
    }
  }

  async function fetchProviders() {
    try {
      const res = await fetch(apiUrl('/api/v1/ai-summary/providers'))
      const data = await res.json()
      setProviders(data)
      
      // Set default provider
      const defaultProvider = data.find((p: AIProvider) => p.api_key_configured)
      if (defaultProvider) {
        setSelectedProvider(defaultProvider.provider)
        setSelectedModel(defaultProvider.default_model)
      }
    } catch (err) {
      console.error('Failed to fetch providers:', err)
    }
  }

  async function fetchCategories() {
    try {
      const res = await fetch(apiUrl(`/api/v1/ai-summary/categories?status=${dealStatus}`))
      const data = await res.json()
      setCategories(data)
    } catch (err) {
      console.error('Failed to fetch categories:', err)
    }
  }

  async function fetchStages() {
    try {
      const params = new URLSearchParams({
        status: dealStatus,
        ...(selectedCategory && { category_id: selectedCategory })
      })
      const res = await fetch(apiUrl(`/api/v1/ai-summary/stages?${params}`))
      const data = await res.json()
      setStages(data)
    } catch (err) {
      console.error('Failed to fetch stages:', err)
    }
  }

  async function fetchHistory() {
    try {
      const res = await fetch(apiUrl('/api/v1/ai-summary/history?page_size=50'))
      const data = await res.json()
      setSummaryHistory(data.items || [])
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }

  async function generateSummary() {
    if (!selectedDeal) return
    
    setGenerating(true)
    setError(null)
    
    try {
      const res = await fetch(apiUrl('/api/v1/ai-summary/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_id: selectedDeal.id,
          provider: selectedProvider,
          model: selectedModel,
          write_to_bitrix: false
        })
      })
      
      if (!res.ok) {
        throw new Error('Özet oluşturulamadı')
      }
      
      const data = await res.json()
      setGeneratedSummary(data)
      fetchHistory()
    } catch (err: any) {
      setError(err.message || 'Özet oluşturulurken hata oluştu')
    } finally {
      setGenerating(false)
    }
  }

  async function writeToBitrix(summaryId: number, mode: 'timeline' | 'comments' = 'timeline') {
    setWritingToBitrix(true)
    setError(null)
    
    try {
      const res = await fetch(apiUrl('/api/v1/ai-summary/write-to-bitrix'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          summary_id: summaryId,
          write_mode: mode
        })
      })
      
      const data = await res.json()
      
      if (data.success) {
        if (generatedSummary?.id === summaryId) {
          setGeneratedSummary({ ...generatedSummary, written_to_bitrix: true })
        }
        fetchHistory()
      } else {
        setError(data.error || 'Bitrix24\'e yazılamadı')
      }
    } catch (err: any) {
      setError(err.message || 'Bitrix24\'e yazılırken hata oluştu')
    } finally {
      setWritingToBitrix(false)
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return '-'
    try {
      return new Date(dateStr).toLocaleDateString('tr-TR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  function getStageName(stageId: string | null, stageName?: string | null) {
    // Eğer backend'den stage_name geldiyse onu kullan
    if (stageName) return stageName
    if (!stageId) return 'Belirsiz'
    // Fallback: basit aşama eşleme
    const stageMap: Record<string, string> = {
      'NEW': 'Yeni',
      'PREPARATION': 'Hazırlık',
      'PREPAYMENT_INVOICE': 'Ön Ödeme Faturası',
      'EXECUTING': 'Yürütülüyor',
      'FINAL_INVOICE': 'Son Fatura',
      'WON': 'Kazanıldı',
      'LOSE': 'Kaybedildi',
    }
    return stageMap[stageId] || stageId
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
                <Sparkles className="w-7 h-7 text-purple-500" />
                AI Müşteri Özeti
              </h1>
              <p className="text-slate-600 mt-1">
                Yapay zeka ile müşteri süreçlerini analiz edin ve özetleyin
              </p>
            </div>
            
            {/* Tab Switcher */}
            <div className="flex bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('generate')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'generate' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles className="w-4 h-4 inline mr-2" />
                Özet Oluştur
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'history' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <History className="w-4 h-4 inline mr-2" />
                Geçmiş ({summaryHistory.length})
              </button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {error}
              <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">
                ✕
              </button>
            </div>
          )}

          {activeTab === 'generate' ? (
            <div className="grid grid-cols-12 gap-6">
              {/* Deal Selection */}
              <div className="col-span-4">
                <Card className="h-full">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Anlaşma Seçin</CardTitle>
                    <CardDescription>Özet oluşturmak istediğiniz anlaşmayı seçin</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Search & Filter */}
                    <div className="space-y-2">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                          type="text"
                          placeholder="Anlaşma ara..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        />
                      </div>
                      {/* Status Filter */}
                      <select
                        value={dealStatus}
                        onChange={(e) => { setDealStatus(e.target.value); setPage(1); setSelectedCategory(''); setSelectedStage(''); }}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500 bg-purple-50 font-medium"
                      >
                        <option value="active">🟢 Aktif Anlaşmalar</option>
                        <option value="won">🏆 Kazanılan Anlaşmalar</option>
                        <option value="lost">❌ Kaybedilen Anlaşmalar</option>
                        <option value="all">📋 Tüm Anlaşmalar</option>
                      </select>
                      {/* Category Filter */}
                      <select
                        value={selectedCategory}
                        onChange={(e) => { setSelectedCategory(e.target.value); setPage(1); }}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-blue-50 font-medium"
                      >
                        <option value="">📂 Tüm Kategoriler</option>
                        {categories.map(cat => (
                          <option key={cat.category_id} value={cat.category_id}>
                            {cat.category_name} ({cat.deal_count})
                          </option>
                        ))}
                      </select>
                      {/* Stage Filter */}
                      <select
                        value={selectedStage}
                        onChange={(e) => setSelectedStage(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-purple-500"
                      >
                        <option value="">Tüm Aşamalar</option>
                        {stages.map(stage => (
                          <option key={stage.stage_id} value={stage.stage_id}>
                            {getStageName(stage.stage_id, stage.stage_name)} ({stage.deal_count})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Deal List */}
                    <div className="space-y-2 max-h-[500px] overflow-y-auto">
                      {deals.map(deal => (
                        <button
                          key={deal.id}
                          onClick={() => setSelectedDeal(deal)}
                          className={`w-full text-left p-3 rounded-lg border transition-all ${
                            selectedDeal?.id === deal.id
                              ? 'border-purple-500 bg-purple-50'
                              : 'border-slate-200 hover:border-purple-300 hover:bg-slate-50'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-slate-900 truncate">
                                {deal.title || `Anlaşma #${deal.id}`}
                              </div>
                              <div className="text-sm text-slate-500 mt-1">
                                {deal.contact_name || deal.company_name || 'Müşteri belirtilmemiş'}
                              </div>
                              <div className="flex items-center gap-2 mt-2">
                                <Badge variant="outline" className="text-xs">
                                  {getStageName(deal.stage_id, deal.stage_name)}
                                </Badge>
                                {deal.has_summary && (
                                  <Badge className="bg-green-100 text-green-700 text-xs">
                                    <CheckCircle2 className="w-3 h-3 mr-1" />
                                    Özet Var
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                          </div>
                        </button>
                      ))}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between pt-4 border-t">
                        <button
                          onClick={() => setPage(p => Math.max(1, p - 1))}
                          disabled={page === 1}
                          className="px-3 py-1 text-sm border rounded-md disabled:opacity-50"
                        >
                          Önceki
                        </button>
                        <span className="text-sm text-slate-600">
                          {page} / {totalPages}
                        </span>
                        <button
                          onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                          disabled={page === totalPages}
                          className="px-3 py-1 text-sm border rounded-md disabled:opacity-50"
                        >
                          Sonraki
                        </button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Deal Details & Generate */}
              <div className="col-span-8 space-y-6">
                {selectedDeal ? (
                  <>
                    {/* Deal Info */}
                    <Card>
                      <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                          <CardTitle>{selectedDeal.title || `Anlaşma #${selectedDeal.id}`}</CardTitle>
                          <Badge className="bg-purple-100 text-purple-700">
                            {getStageName(selectedDeal.stage_id, selectedDeal.stage_name)}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-3 gap-4">
                          {/* Contact */}
                          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                            <User className="w-8 h-8 text-blue-500" />
                            <div>
                              <div className="text-sm text-slate-500">Müşteri</div>
                              <div className="font-medium">{selectedDeal.contact_name || '-'}</div>
                            </div>
                          </div>
                          
                          {/* Company */}
                          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                            <Building2 className="w-8 h-8 text-purple-500" />
                            <div>
                              <div className="text-sm text-slate-500">Firma</div>
                              <div className="font-medium">{selectedDeal.company_name || '-'}</div>
                            </div>
                          </div>
                          
                          {/* Amount */}
                          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                            <TrendingUp className="w-8 h-8 text-green-500" />
                            <div>
                              <div className="text-sm text-slate-500">Tutar</div>
                              <div className="font-medium">
                                {selectedDeal.opportunity 
                                  ? `${Number(selectedDeal.opportunity).toLocaleString('tr-TR')} ${selectedDeal.currency || 'TRY'}`
                                  : '-'
                                }
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Stats */}
                        {dealDetails && (
                          <div className="mt-4 pt-4 border-t">
                            {/* Contact Type Badge */}
                            {dealDetails.contact?.type_name && (
                              <div className="mb-4 flex items-center gap-2">
                                <span className="text-sm text-slate-500">Kişi Türü:</span>
                                <Badge className="bg-indigo-100 text-indigo-700">
                                  {dealDetails.contact.type_name}
                                </Badge>
                              </div>
                            )}
                            
                            <div className="grid grid-cols-4 gap-4">
                              <div className="text-center">
                                <div className="text-2xl font-bold text-indigo-600">
                                  {dealDetails.stats.total_deals_count || 1}
                                </div>
                                <div className="text-sm text-slate-500">Toplam Anlaşma</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">
                                  {dealDetails.stats.activities_count}
                                </div>
                                <div className="text-sm text-slate-500">Aktivite</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-purple-600">
                                  {dealDetails.stats.tasks_count}
                                </div>
                                <div className="text-sm text-slate-500">Görev</div>
                              </div>
                              <div className="text-center">
                                <div className="text-2xl font-bold text-green-600">
                                  {dealDetails.stats.task_comments_count}
                                </div>
                                <div className="text-sm text-slate-500">Yorum</div>
                              </div>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    {/* AI Provider Selection */}
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">AI Ayarları</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                              AI Sağlayıcı
                            </label>
                            <select
                              value={selectedProvider}
                              onChange={(e) => {
                                setSelectedProvider(e.target.value)
                                const provider = providers.find(p => p.provider === e.target.value)
                                if (provider) {
                                  setSelectedModel(provider.default_model)
                                }
                              }}
                              className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                            >
                              {providers.map(p => (
                                <option 
                                  key={p.provider} 
                                  value={p.provider}
                                  disabled={!p.api_key_configured}
                                >
                                  {p.provider.toUpperCase()} 
                                  {!p.api_key_configured && ' (API Key Gerekli)'}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                              Model
                            </label>
                            <select
                              value={selectedModel}
                              onChange={(e) => setSelectedModel(e.target.value)}
                              className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                            >
                              {providers
                                .find(p => p.provider === selectedProvider)
                                ?.available_models.map(model => (
                                  <option key={model} value={model}>
                                    {model}
                                  </option>
                                ))
                              }
                            </select>
                          </div>
                        </div>

                        <Button
                          onClick={generateSummary}
                          disabled={generating}
                          className="w-full mt-4 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
                        >
                          {generating ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Özet Oluşturuluyor...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-4 h-4 mr-2" />
                              AI ile Özet Oluştur
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </Card>

                    {/* Generated Summary */}
                    {generatedSummary && (
                      <Card className="border-green-200 bg-green-50/50">
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg flex items-center gap-2">
                              <CheckCircle2 className="w-5 h-5 text-green-500" />
                              Oluşturulan Özet
                            </CardTitle>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline">
                                {generatedSummary.provider} / {generatedSummary.model}
                              </Badge>
                              {generatedSummary.written_to_bitrix && (
                                <Badge className="bg-blue-100 text-blue-700">
                                  <CheckCircle2 className="w-3 h-3 mr-1" />
                                  Bitrix24'e Yazıldı
                                </Badge>
                              )}
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="bg-white p-6 rounded-lg border max-h-[600px] overflow-y-auto">
                            <div className="prose prose-slate prose-headings:text-slate-800 prose-h2:text-lg prose-h2:font-bold prose-h2:border-b prose-h2:pb-2 prose-h2:mb-4 prose-h3:text-base prose-h3:font-semibold prose-table:text-sm prose-td:px-2 prose-td:py-1 prose-th:px-2 prose-th:py-1 prose-th:bg-slate-100 prose-strong:text-slate-800 prose-ul:my-2 prose-li:my-0.5 max-w-none">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {generatedSummary.summary}
                              </ReactMarkdown>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 mt-4">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => copyToClipboard(generatedSummary.summary)}
                            >
                              <Copy className="w-4 h-4 mr-2" />
                              Kopyala
                            </Button>
                            
                            {!generatedSummary.written_to_bitrix && (
                              <>
                                <Button
                                  size="sm"
                                  onClick={() => writeToBitrix(generatedSummary.id, 'timeline')}
                                  disabled={writingToBitrix}
                                  className="bg-blue-500 hover:bg-blue-600"
                                >
                                  {writingToBitrix ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                  ) : (
                                    <Send className="w-4 h-4 mr-2" />
                                  )}
                                  Timeline'a Yaz
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => writeToBitrix(generatedSummary.id, 'comments')}
                                  disabled={writingToBitrix}
                                >
                                  <Send className="w-4 h-4 mr-2" />
                                  Notlara Ekle
                                </Button>
                              </>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </>
                ) : (
                  <Card className="h-[400px] flex items-center justify-center">
                    <div className="text-center text-slate-500">
                      <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>Özet oluşturmak için sol taraftan bir anlaşma seçin</p>
                    </div>
                  </Card>
                )}
              </div>
            </div>
          ) : (
            /* History Tab */
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Özet Geçmişi</CardTitle>
                  <Button variant="outline" size="sm" onClick={fetchHistory}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Yenile
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {summaryHistory.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Henüz özet oluşturulmamış</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {summaryHistory.map(summary => (
                      <div
                        key={summary.id}
                        className="p-4 border rounded-lg hover:bg-slate-50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{summary.deal_title}</span>
                              <Badge variant="outline" className="text-xs">
                                {summary.provider}
                              </Badge>
                              {summary.written_to_bitrix && (
                                <Badge className="bg-green-100 text-green-700 text-xs">
                                  <CheckCircle2 className="w-3 h-3 mr-1" />
                                  Bitrix24
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-slate-600 mt-2 line-clamp-2">
                              {summary.summary_preview || summary.summary?.substring(0, 200)}...
                            </p>
                            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {formatDate(summary.created_at)}
                              </span>
                              <span>Model: {summary.model}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 ml-4">
                            {!summary.written_to_bitrix && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => writeToBitrix(summary.id, 'timeline')}
                              >
                                <Send className="w-4 h-4" />
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                // View full summary
                                setGeneratedSummary(summary as any)
                                setActiveTab('generate')
                              }}
                            >
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
