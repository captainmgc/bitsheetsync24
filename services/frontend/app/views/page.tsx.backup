'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { apiUrl } from '@/lib/config'
import {
  Eye,
  Plus,
  Edit,
  Trash2,
  Save,
  X,
  Filter,
  SortAsc,
  Star,
  Database
} from 'lucide-react'

interface View {
  id: number
  view_name: string
  table_name: string
  filters: any
  sort_config: any
  columns_visible: string[]
  is_default: boolean
  created_at: string
  updated_at: string
}

interface FilterRule {
  field: string
  operator: string
  value: string
}

export default function ViewManagementPage() {
  const { data: session } = useSession()
  const [views, setViews] = useState<View[]>([])
  const [loading, setLoading] = useState(true)
  const [editingView, setEditingView] = useState<View | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedTable, setSelectedTable] = useState('')
  
  // Form state
  const [formData, setFormData] = useState({
    view_name: '',
    table_name: '',
    filters: {} as any,
    sort_config: {} as any,
    columns_visible: [] as string[],
    is_default: false
  })
  
  const [filterRules, setFilterRules] = useState<FilterRule[]>([
    { field: '', operator: '=', value: '' }
  ])

  const tables = [
    { name: 'contacts', displayName: 'Müşteriler' },
    { name: 'companies', displayName: 'Şirketler' },
    { name: 'deals', displayName: 'Anlaşmalar' },
    { name: 'activities', displayName: 'Aktiviteler' },
    { name: 'tasks', displayName: 'Görevler' },
    { name: 'task_comments', displayName: 'Görev Yorumları' },
    { name: 'leads', displayName: 'Potansiyel Müşteriler' },
  ]

  const operators = [
    { value: '=', label: 'Eşittir' },
    { value: '!=', label: 'Eşit Değil' },
    { value: '>', label: 'Büyüktür' },
    { value: '<', label: 'Küçüktür' },
    { value: '>=', label: 'Büyük veya Eşit' },
    { value: '<=', label: 'Küçük veya Eşit' },
    { value: 'LIKE', label: 'İçerir' },
    { value: 'NOT LIKE', label: 'İçermez' },
  ]

  useEffect(() => {
    fetchAllViews()
  }, [])

  const fetchAllViews = async () => {
    setLoading(true)
    try {
      const response = await fetch(apiUrl('/api/views/'))
      const result = await response.json()
      setViews(result.views || [])
    } catch (error) {
      console.error('Failed to fetch views:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateView = async () => {
    try {
      // Build filters object from rules
      const filters: any = {}
      filterRules.forEach(rule => {
        if (rule.field && rule.value) {
          filters[rule.field] = { operator: rule.operator, value: rule.value }
        }
      })

      const response = await fetch(apiUrl(`/api/views/${formData.table_name}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          filters
        })
      })

      if (!response.ok) {
        throw new Error('Failed to create view')
      }

      await fetchAllViews()
      resetForm()
      setShowCreateForm(false)
      alert('View başarıyla oluşturuldu!')
    } catch (error) {
      console.error('Error creating view:', error)
      alert('View oluşturulurken hata oluştu!')
    }
  }

  const handleUpdateView = async (viewId: number) => {
    try {
      if (!editingView) return

      const response = await fetch(
        apiUrl(`/api/views/${editingView.table_name}/${viewId}`),
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        }
      )

      if (!response.ok) {
        throw new Error('Failed to update view')
      }

      await fetchAllViews()
      setEditingView(null)
      resetForm()
      alert('View başarıyla güncellendi!')
    } catch (error) {
      console.error('Error updating view:', error)
      alert('View güncellenirken hata oluştu!')
    }
  }

  const handleDeleteView = async (tableName: string, viewId: number) => {
    if (!confirm('Bu view\'ı silmek istediğinize emin misiniz?')) {
      return
    }

    try {
      const response = await fetch(
        apiUrl(`/api/views/${tableName}/${viewId}`),
        { method: 'DELETE' }
      )

      if (!response.ok) {
        throw new Error('Failed to delete view')
      }

      await fetchAllViews()
      alert('View başarıyla silindi!')
    } catch (error) {
      console.error('Error deleting view:', error)
      alert('View silinirken hata oluştu!')
    }
  }

  const startEdit = (view: View) => {
    setEditingView(view)
    setFormData({
      view_name: view.view_name,
      table_name: view.table_name,
      filters: view.filters || {},
      sort_config: view.sort_config || {},
      columns_visible: view.columns_visible || [],
      is_default: view.is_default
    })
    
    // Convert filters to rules
    const rules: FilterRule[] = []
    if (view.filters && typeof view.filters === 'object') {
      Object.entries(view.filters).forEach(([field, config]: [string, any]) => {
        rules.push({
          field,
          operator: config.operator || '=',
          value: config.value || ''
        })
      })
    }
    setFilterRules(rules.length > 0 ? rules : [{ field: '', operator: '=', value: '' }])
  }

  const resetForm = () => {
    setFormData({
      view_name: '',
      table_name: '',
      filters: {},
      sort_config: {},
      columns_visible: [],
      is_default: false
    })
    setFilterRules([{ field: '', operator: '=', value: '' }])
  }

  const addFilterRule = () => {
    setFilterRules([...filterRules, { field: '', operator: '=', value: '' }])
  }

  const removeFilterRule = (index: number) => {
    setFilterRules(filterRules.filter((_, i) => i !== index))
  }

  const updateFilterRule = (index: number, key: keyof FilterRule, value: string) => {
    const updated = [...filterRules]
    updated[index][key] = value
    setFilterRules(updated)
  }

  const getTableDisplayName = (tableName: string) => {
    return tables.find(t => t.name === tableName)?.displayName || tableName
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 text-white shadow-lg">
            <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
              <Eye className="w-8 h-8" />
              View Yönetimi
            </h1>
            <p className="text-indigo-100">
              View'ları yönetin, filtreler oluşturun ve veri görünümlerini özelleştirin
            </p>
          </div>

          {/* Create Button */}
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              Kayıtlı View'lar
            </h2>
            <button
              onClick={() => {
                setShowCreateForm(true)
                setEditingView(null)
                resetForm()
              }}
              className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:shadow-lg transition-all flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Yeni View Oluştur
            </button>
          </div>

          {/* Create/Edit Form */}
          {(showCreateForm || editingView) && (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  {editingView ? 'View Düzenle' : 'Yeni View Oluştur'}
                </h3>
                <button
                  onClick={() => {
                    setShowCreateForm(false)
                    setEditingView(null)
                    resetForm()
                  }}
                  className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Table Selection */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    <Database className="w-4 h-4 inline mr-2" />
                    Tablo
                  </label>
                  <select
                    value={formData.table_name}
                    onChange={(e) => setFormData({ ...formData, table_name: e.target.value })}
                    disabled={!!editingView}
                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white disabled:opacity-50"
                  >
                    <option value="">Tablo Seçin</option>
                    {tables.map(table => (
                      <option key={table.name} value={table.name}>
                        {table.displayName}
                      </option>
                    ))}
                  </select>
                </div>

                {/* View Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    View Adı
                  </label>
                  <input
                    type="text"
                    value={formData.view_name}
                    onChange={(e) => setFormData({ ...formData, view_name: e.target.value })}
                    placeholder="Örn: Aktif Müşteriler"
                    className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                  />
                </div>

                {/* Filter Rules */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    <Filter className="w-4 h-4 inline mr-2" />
                    Filtre Kuralları
                  </label>
                  <div className="space-y-2">
                    {filterRules.map((rule, index) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="text"
                          value={rule.field}
                          onChange={(e) => updateFilterRule(index, 'field', e.target.value)}
                          placeholder="Alan adı (örn: status)"
                          className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
                        />
                        <select
                          value={rule.operator}
                          onChange={(e) => updateFilterRule(index, 'operator', e.target.value)}
                          className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
                        >
                          {operators.map(op => (
                            <option key={op.value} value={op.value}>
                              {op.label}
                            </option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={rule.value}
                          onChange={(e) => updateFilterRule(index, 'value', e.target.value)}
                          placeholder="Değer"
                          className="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-sm"
                        />
                        {filterRules.length > 1 && (
                          <button
                            onClick={() => removeFilterRule(index)}
                            className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      onClick={addFilterRule}
                      className="text-sm text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Filtre Ekle
                    </button>
                  </div>
                </div>

                {/* Sort Config */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      <SortAsc className="w-4 h-4 inline mr-2" />
                      Sıralama Alanı
                    </label>
                    <input
                      type="text"
                      value={formData.sort_config?.column || ''}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        sort_config: { ...(formData.sort_config || {}), column: e.target.value }
                      })}
                      placeholder="Örn: created_at"
                      className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Sıralama Yönü
                    </label>
                    <select
                      value={formData.sort_config?.order || 'asc'}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        sort_config: { ...(formData.sort_config || {}), order: e.target.value }
                      })}
                      className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    >
                      <option value="asc">Artan (A-Z)</option>
                      <option value="desc">Azalan (Z-A)</option>
                    </select>
                  </div>
                </div>

                {/* Default View */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_default"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500"
                  />
                  <label htmlFor="is_default" className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-1">
                    <Star className="w-4 h-4 text-yellow-500" />
                    Varsayılan view olarak ayarla
                  </label>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-4">
                  <button
                    onClick={() => editingView ? handleUpdateView(editingView.id) : handleCreateView()}
                    disabled={!formData.view_name || !formData.table_name}
                    className="flex-1 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    <Save className="w-5 h-5" />
                    {editingView ? 'Güncelle' : 'Oluştur'}
                  </button>
                  <button
                    onClick={() => {
                      setShowCreateForm(false)
                      setEditingView(null)
                      resetForm()
                    }}
                    className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                  >
                    İptal
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Views List */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                      View Adı
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                      Tablo
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                      Filtreler
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                      Sıralama
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                      Varsayılan
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                      İşlemler
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                        Yükleniyor...
                      </td>
                    </tr>
                  ) : views.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                        Henüz view oluşturulmamış.
                      </td>
                    </tr>
                  ) : (
                    views.map((view) => (
                      <tr key={view.id} className="hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <Eye className="w-4 h-4 text-slate-400" />
                            <span className="text-sm font-medium text-slate-900 dark:text-white">
                              {view.view_name}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                          {getTableDisplayName(view.table_name)}
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">
                          {Object.keys(view.filters || {}).length > 0 ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
                              <Filter className="w-3 h-3" />
                              {Object.keys(view.filters).length} filtre
                            </span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                          {view.sort_config?.column ? (
                            <span className="inline-flex items-center gap-1">
                              <SortAsc className="w-3 h-3" />
                              {view.sort_config.column} ({view.sort_config.order})
                            </span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {view.is_default && (
                            <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => startEdit(view)}
                              className="p-2 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950 rounded-lg transition-colors"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteView(view.table_name, view.id)}
                              className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
