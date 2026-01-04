'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { apiUrl } from '@/lib/config'
import { 
  Check, 
  ChevronRight, 
  Database, 
  Calendar,
  FileSpreadsheet,
  Loader2,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'

type WizardStep = 1 | 2 | 3 | 4 | 5

interface SelectedTable {
  name: string
  displayName: string
  recordCount: number
  selected: boolean
  selectedView?: string  // NEW: Selected view ID
  availableViews?: Array<{id: number, view_name: string}>  // NEW: Available views
}

interface Relationship {
  from: string
  to: string
  type: 'one-to-many' | 'many-to-one'
  field: string
}

export default function ExportPage() {
  const { data: session } = useSession()
  const [currentStep, setCurrentStep] = useState<WizardStep>(1)
  const [selectedTables, setSelectedTables] = useState<SelectedTable[]>([
    { name: 'contacts', displayName: 'Müşteriler', recordCount: 0, selected: false },
    { name: 'companies', displayName: 'Şirketler', recordCount: 0, selected: false },
    { name: 'deals', displayName: 'Anlaşmalar', recordCount: 0, selected: false },
    { name: 'activities', displayName: 'Aktiviteler', recordCount: 0, selected: false },
    { name: 'tasks', displayName: 'Görevler', recordCount: 0, selected: false },
    { name: 'task_comments', displayName: 'Görev Yorumları', recordCount: 0, selected: false },
    { name: 'leads', displayName: 'Potansiyel Müşteriler', recordCount: 0, selected: false },
  ])
  const [dateRange, setDateRange] = useState({
    from: '',
    to: ''
  })
  const [sheetMode, setSheetMode] = useState<'new' | 'existing'>('new')
  const [sheetName, setSheetName] = useState('')
  const [existingSheetId, setExistingSheetId] = useState('')
  const [exporting, setExporting] = useState(false)
  const [exportStatus, setExportStatus] = useState<{
    status: 'idle' | 'running' | 'success' | 'error'
    message: string
    sheetUrl?: string
    syncConfigId?: number
  }>({ status: 'idle', message: '' })
  
  // Sync options
  const [enableSync, setEnableSync] = useState(false)
  const [bidirectional, setBidirectional] = useState(false)
  const [syncInterval, setSyncInterval] = useState(5)

  // Fetch table counts on mount
  useEffect(() => {
    fetch(apiUrl('/api/tables/'))
      .then(res => res.json())
      .then(data => {
        setSelectedTables(prev =>
          prev.map(t => {
            const tableData = data.find((d: any) => d.name === t.name)
            return tableData
              ? { ...t, recordCount: tableData.record_count }
              : t
          })
        )
      })
      .catch(err => console.error('Failed to fetch table counts:', err))
  }, [])

  // Fetch views when a table is selected
  const fetchViewsForTable = async (tableName: string) => {
    try {
      const response = await fetch(apiUrl(`/api/views/${tableName}`))
      const result = await response.json()
      
      setSelectedTables(prev =>
        prev.map(t =>
          t.name === tableName
            ? { ...t, availableViews: result.views || [] }
            : t
        )
      )
    } catch (error) {
      console.error(`Failed to fetch views for ${tableName}:`, error)
    }
  }

  // Otomatik ilişkiler
  const relationships: Relationship[] = [
    { from: 'contacts', to: 'companies', type: 'many-to-one', field: 'company_id' },
    { from: 'deals', to: 'contacts', type: 'many-to-one', field: 'contact_id' },
    { from: 'deals', to: 'companies', type: 'many-to-one', field: 'company_id' },
    { from: 'activities', to: 'contacts', type: 'many-to-one', field: 'owner_id' },
    { from: 'tasks', to: 'contacts', type: 'many-to-one', field: 'responsible_id' },
    { from: 'task_comments', to: 'tasks', type: 'many-to-one', field: 'task_id' },
  ]

  const steps = [
    { number: 1, title: 'Tablo Seçimi', description: 'Hangi tablolar aktarılacak?' },
    { number: 2, title: 'İlişkiler', description: 'Otomatik tespit edilen ilişkiler' },
    { number: 3, title: 'Tarih Filtresi', description: 'Veri aralığı seçin (opsiyonel)' },
    { number: 4, title: 'Hedef Sheet', description: 'Google Sheets seçimi' },
    { number: 5, title: 'Export', description: 'Aktarım işlemi' },
  ]

  const toggleTable = (tableName: string) => {
    setSelectedTables(prev =>
      prev.map(t => {
        if (t.name === tableName) {
          const newSelected = !t.selected
          // Fetch views when table is selected
          if (newSelected && !t.availableViews) {
            fetchViewsForTable(tableName)
          }
          return { ...t, selected: newSelected }
        }
        return t
      })
    )
  }

  const setTableView = (tableName: string, viewId: string) => {
    setSelectedTables(prev =>
      prev.map(t =>
        t.name === tableName ? { ...t, selectedView: viewId } : t
      )
    )
  }

  const canProceed = () => {
    if (currentStep === 1) {
      return selectedTables.some(t => t.selected)
    }
    if (currentStep === 4) {
      return sheetMode === 'new' ? sheetName.trim() !== '' : existingSheetId.trim() !== ''
    }
    return true
  }

  const handleExport = async () => {
    setExporting(true)
    setExportStatus({ status: 'running', message: 'Export başlatılıyor...' })

    try {
      // Build table_views object from selected views
      const tableViews: { [key: string]: number } = {}
      selectedTables.forEach(t => {
        if (t.selected && t.selectedView) {
          tableViews[t.name] = parseInt(t.selectedView)
        }
      })

      const payload = {
        tables: selectedTables.filter(t => t.selected).map(t => t.name),
        dateRange: dateRange.from && dateRange.to ? dateRange : null,
        sheetMode,
        sheetName: sheetMode === 'new' ? sheetName : undefined,
        sheetId: sheetMode === 'existing' ? existingSheetId : undefined,
        accessToken: session?.accessToken,
        tableViews: Object.keys(tableViews).length > 0 ? tableViews : undefined,
        // Sync options
        enableSync,
        bidirectional,
        syncIntervalMinutes: syncInterval
      }

      // Check if we have an access token
      if (!session?.accessToken) {
        throw new Error('AUTH_REQUIRED')
      }

      const response = await fetch(apiUrl('/api/v1/exports/sheets'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const errorDetail = errorData.detail || 'Export failed'
        
        // Check for authentication errors
        if (response.status === 401 || errorDetail.toLowerCase().includes('token')) {
          throw new Error('AUTH_EXPIRED')
        }
        throw new Error(errorDetail)
      }

      const result = await response.json()
      
      let successMessage = `✅ ${result.total_rows} kayıt başarıyla aktarıldı!`
      if (result.sync_config_id) {
        successMessage += bidirectional 
          ? ' 🔄 Çift yönlü senkronizasyon etkinleştirildi.'
          : ' ⬆️ Artırımlı güncelleme etkinleştirildi.'
      }
      
      setExportStatus({
        status: 'success',
        message: successMessage,
        sheetUrl: result.sheet_url,
        syncConfigId: result.sync_config_id
      })
    } catch (error: any) {
      let errorMessage = '❌ Export sırasında hata oluştu. Lütfen tekrar deneyin.'
      
      if (error.message === 'AUTH_REQUIRED' || error.message === 'AUTH_EXPIRED') {
        errorMessage = '🔐 Google oturumunuz sona ermiş. Lütfen çıkış yapıp tekrar giriş yapın.'
      } else if (error.message) {
        errorMessage = `❌ ${error.message}`
      }
      
      setExportStatus({
        status: 'error',
        message: errorMessage
      })
    } finally {
      setExporting(false)
    }
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl p-6 text-white shadow-lg">
            <h1 className="text-2xl font-bold mb-2">📤 Google Sheets Export Wizard</h1>
            <p className="text-purple-100">
              Bitrix24 verilerinizi Google E-Tablolar'a kolayca aktarın
            </p>
          </div>

          {/* Progress Steps */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <div className="flex items-center justify-between">
              {steps.map((step, idx) => (
                <div key={step.number} className="flex items-center flex-1">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                        currentStep >= step.number
                          ? 'bg-gradient-to-br from-purple-500 to-pink-500 text-white'
                          : 'bg-slate-200 dark:bg-slate-700 text-slate-500'
                      }`}
                    >
                      {currentStep > step.number ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        step.number
                      )}
                    </div>
                    <div className="mt-2 text-center">
                      <div className="text-xs font-medium text-slate-900 dark:text-white">
                        {step.title}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {step.description}
                      </div>
                    </div>
                  </div>
                  {idx < steps.length - 1 && (
                    <div
                      className={`flex-1 h-1 mx-2 transition-all ${
                        currentStep > step.number
                          ? 'bg-gradient-to-r from-purple-500 to-pink-500'
                          : 'bg-slate-200 dark:bg-slate-700'
                      }`}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Step Content */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 min-h-[400px]">
            {/* Step 1: Table Selection */}
            {currentStep === 1 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Database className="w-6 h-6 text-purple-500" />
                  Hangi tabloları aktarmak istiyorsunuz?
                </h2>
                <p className="text-slate-600 dark:text-slate-400">
                  Aşağıdaki tablolardan birini veya birkaçını seçin:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedTables.map((table) => (
                    <div key={table.name} className="space-y-2">
                      <button
                        onClick={() => toggleTable(table.name)}
                        className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                          table.selected
                            ? 'border-purple-500 bg-purple-50 dark:bg-purple-950'
                            : 'border-slate-200 dark:border-slate-700 hover:border-purple-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-slate-900 dark:text-white">
                              {table.displayName}
                            </div>
                            <div className="text-sm text-slate-500 dark:text-slate-400">
                              {table.recordCount.toLocaleString('tr-TR')} kayıt
                            </div>
                          </div>
                          <div
                            className={`w-6 h-6 rounded-full flex items-center justify-center ${
                              table.selected
                                ? 'bg-purple-500 text-white'
                                : 'bg-slate-200 dark:bg-slate-700'
                            }`}
                          >
                            {table.selected && <Check className="w-4 h-4" />}
                          </div>
                        </div>
                      </button>
                      
                      {/* View Selection */}
                      {table.selected && table.availableViews && table.availableViews.length > 0 && (
                        <div className="ml-4 pl-4 border-l-2 border-purple-300">
                          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                            View Seçin
                          </label>
                          <select
                            value={table.selectedView || ''}
                            onChange={(e) => setTableView(table.name, e.target.value)}
                            className="w-full px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                          >
                            <option value="">Tüm Kayıtlar</option>
                            {table.availableViews.map((view) => (
                              <option key={view.id} value={view.id}>
                                {view.view_name}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Step 2: Relationships */}
            {currentStep === 2 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  🔗 Otomatik Tespit Edilen İlişkiler
                </h2>
                <p className="text-slate-600 dark:text-slate-400">
                  Seçtiğiniz tablolar arasındaki ilişkiler otomatik olarak korunacak:
                </p>
                <div className="space-y-3">
                  {relationships
                    .filter(
                      (rel) =>
                        selectedTables.find((t) => t.name === rel.from)?.selected &&
                        selectedTables.find((t) => t.name === rel.to)?.selected
                    )
                    .map((rel, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg"
                      >
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                        <div>
                          <div className="font-medium text-slate-900 dark:text-white">
                            {selectedTables.find((t) => t.name === rel.from)?.displayName}
                            <ChevronRight className="inline w-4 h-4 mx-2" />
                            {selectedTables.find((t) => t.name === rel.to)?.displayName}
                          </div>
                          <div className="text-sm text-slate-600 dark:text-slate-400">
                            Alan: <code className="px-1 bg-slate-200 dark:bg-slate-700 rounded">{rel.field}</code>
                          </div>
                        </div>
                      </div>
                    ))}
                  {relationships.filter(
                    (rel) =>
                      selectedTables.find((t) => t.name === rel.from)?.selected &&
                      selectedTables.find((t) => t.name === rel.to)?.selected
                  ).length === 0 && (
                    <div className="text-center py-8 text-slate-500">
                      Seçtiğiniz tablolar arasında tespit edilen ilişki yok.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Step 3: Date Filter */}
            {currentStep === 3 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Calendar className="w-6 h-6 text-purple-500" />
                  Tarih Aralığı Filtresi (Opsiyonel)
                </h2>
                <p className="text-slate-600 dark:text-slate-400">
                  Belirli bir tarih aralığındaki kayıtları filtreleyebilirsiniz:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Başlangıç Tarihi
                    </label>
                    <input
                      type="date"
                      value={dateRange.from}
                      onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
                      className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Bitiş Tarihi
                    </label>
                    <input
                      type="date"
                      value={dateRange.to}
                      onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
                      className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    />
                  </div>
                </div>
                <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5" />
                    <div className="text-sm text-slate-700 dark:text-slate-300">
                      <strong>Not:</strong> Tarih aralığı seçmezseniz, tüm kayıtlar aktarılacaktır.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Sheet Selection */}
            {currentStep === 4 && (
              <div className="space-y-4">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileSpreadsheet className="w-6 h-6 text-purple-500" />
                  Hedef Google Sheets
                </h2>
                <div className="space-y-3">
                  <button
                    onClick={() => setSheetMode('new')}
                    className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                      sheetMode === 'new'
                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-950'
                        : 'border-slate-200 dark:border-slate-700'
                    }`}
                  >
                    <div className="font-medium text-slate-900 dark:text-white">
                      🆕 Yeni E-Tablo Oluştur
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      Yeni bir Google Sheets belgesi oluşturulacak
                    </div>
                  </button>
                  
                  {sheetMode === 'new' && (
                    <div className="ml-4 mt-2">
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        E-Tablo Adı
                      </label>
                      <input
                        type="text"
                        value={sheetName}
                        onChange={(e) => setSheetName(e.target.value)}
                        placeholder="Örn: Bitrix24 Export - 2025-01"
                        className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                      />
                    </div>
                  )}

                  <button
                    onClick={() => setSheetMode('existing')}
                    className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                      sheetMode === 'existing'
                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-950'
                        : 'border-slate-200 dark:border-slate-700'
                    }`}
                  >
                    <div className="font-medium text-slate-900 dark:text-white">
                      📋 Mevcut E-Tabloya Ekle
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400">
                      Var olan bir Google Sheets belgesine eklenecek
                    </div>
                  </button>

                  {sheetMode === 'existing' && (
                    <div className="ml-4 mt-2">
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Google Sheets ID
                      </label>
                      <input
                        type="text"
                        value={existingSheetId}
                        onChange={(e) => setExistingSheetId(e.target.value)}
                        placeholder="URL'den ID'yi yapıştırın"
                        className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white font-mono text-sm"
                      />
                      <div className="mt-2 text-xs text-slate-500">
                        Örn: https://docs.google.com/spreadsheets/d/<strong>1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms</strong>/edit
                      </div>
                    </div>
                  )}
                </div>

                {/* Sync Options */}
                <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                    🔄 Senkronizasyon Seçenekleri
                  </h3>
                  
                  <div className="space-y-4">
                    {/* Enable Sync Toggle */}
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={enableSync}
                        onChange={(e) => setEnableSync(e.target.checked)}
                        className="w-5 h-5 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                      />
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white">
                          Artırımlı Güncelleme
                        </div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          Bitrix24'te yapılan değişiklikler otomatik olarak E-Tabloya aktarılır
                        </div>
                      </div>
                    </label>

                    {enableSync && (
                      <>
                        {/* Bidirectional Sync */}
                        <label className="flex items-center gap-3 cursor-pointer ml-8">
                          <input
                            type="checkbox"
                            checked={bidirectional}
                            onChange={(e) => setBidirectional(e.target.checked)}
                            className="w-5 h-5 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                          />
                          <div>
                            <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                              Çift Yönlü Senkronizasyon
                              <span className="text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 px-2 py-0.5 rounded">
                                BETA
                              </span>
                            </div>
                            <div className="text-sm text-slate-500 dark:text-slate-400">
                              E-Tabloda yapılan değişiklikler Bitrix24'e aktarılır
                            </div>
                          </div>
                        </label>

                        {/* Sync Interval */}
                        <div className="ml-8">
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            Güncelleme Aralığı
                          </label>
                          <select
                            value={syncInterval}
                            onChange={(e) => setSyncInterval(parseInt(e.target.value))}
                            className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                          >
                            <option value={5}>Her 5 dakika</option>
                            <option value={15}>Her 15 dakika</option>
                            <option value={30}>Her 30 dakika</option>
                            <option value={60}>Her 1 saat</option>
                            <option value={360}>Her 6 saat</option>
                            <option value={1440}>Günde bir</option>
                          </select>
                        </div>

                        {bidirectional && (
                          <div className="ml-8 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                            <div className="flex items-start gap-2">
                              <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
                              <div className="text-sm text-slate-700 dark:text-slate-300">
                                <strong>Dikkat:</strong> E-Tabloda yapılan değişiklikler Bitrix24'e aktarılacaktır. 
                                ID kolonunu değiştirmemeye dikkat edin.
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Step 5: Export */}
            {currentStep === 5 && (
              <div className="space-y-6">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  🚀 Export Hazır!
                </h2>
                
                {exportStatus.status === 'idle' && (
                  <>
                    <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 space-y-2">
                      <div className="font-medium text-slate-900 dark:text-white">
                        Özet:
                      </div>
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        • Seçilen tablolar: <strong>{selectedTables.filter(t => t.selected).map(t => t.displayName).join(', ')}</strong>
                      </div>
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        • Tarih aralığı: {dateRange.from && dateRange.to ? `${dateRange.from} - ${dateRange.to}` : 'Tüm kayıtlar'}
                      </div>
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        • Hedef: {sheetMode === 'new' ? `Yeni e-tablo (${sheetName})` : `Mevcut e-tablo (${existingSheetId})`}
                      </div>
                      {enableSync && (
                        <div className="text-sm text-slate-600 dark:text-slate-400">
                          • Senkronizasyon: <strong>{bidirectional ? '🔄 Çift Yönlü' : '⬆️ Artırımlı Güncelleme'}</strong> (Her {syncInterval} dk)
                        </div>
                      )}
                    </div>
                    
                    <button
                      onClick={handleExport}
                      disabled={exporting}
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-lg font-medium hover:shadow-lg transition-all disabled:opacity-50"
                    >
                      Export'u Başlat
                    </button>
                  </>
                )}

                {exportStatus.status === 'running' && (
                  <div className="text-center py-12">
                    <Loader2 className="w-12 h-12 text-purple-500 animate-spin mx-auto mb-4" />
                    <div className="text-lg font-medium text-slate-900 dark:text-white">
                      {exportStatus.message}
                    </div>
                    <div className="text-sm text-slate-500 mt-2">
                      Bu işlem birkaç dakika sürebilir...
                    </div>
                  </div>
                )}

                {exportStatus.status === 'success' && (
                  <div className="text-center py-12">
                    <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
                    <div className="text-lg font-medium text-slate-900 dark:text-white mb-4">
                      {exportStatus.message}
                    </div>
                    {exportStatus.sheetUrl && (
                      <a
                        href={exportStatus.sheetUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 bg-green-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-700 transition-all"
                      >
                        <FileSpreadsheet className="w-5 h-5" />
                        Google Sheets'i Aç
                      </a>
                    )}
                  </div>
                )}

                {exportStatus.status === 'error' && (
                  <div className="text-center py-12">
                    <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                    <div className="text-lg font-medium text-slate-900 dark:text-white mb-4">
                      {exportStatus.message}
                    </div>
                    <button
                      onClick={() => setExportStatus({ status: 'idle', message: '' })}
                      className="bg-purple-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-purple-700"
                    >
                      Tekrar Dene
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setCurrentStep((prev) => Math.max(1, prev - 1) as WizardStep)}
              disabled={currentStep === 1}
              className="px-6 py-2 border border-slate-300 dark:border-slate-600 rounded-lg font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ← Geri
            </button>
            
            {currentStep < 5 && (
              <button
                onClick={() => setCurrentStep((prev) => Math.min(5, prev + 1) as WizardStep)}
                disabled={!canProceed()}
                className="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                İleri →
              </button>
            )}
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
