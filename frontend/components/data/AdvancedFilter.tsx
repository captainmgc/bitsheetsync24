'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import {
  Filter,
  X,
  Plus,
  Trash2,
  Save,
  Calendar,
  Hash,
  Type,
  Search,
  ChevronDown,
  SlidersHorizontal,
  Check
} from 'lucide-react'

export interface FilterRule {
  id: string
  field: string
  operator: string
  value: string
  value2?: string // For range filters
}

export interface SavedFilter {
  id: string
  name: string
  tableName: string
  rules: FilterRule[]
  createdAt: string
}

interface AdvancedFilterProps {
  columns: string[]
  data: Record<string, any>[]
  filters: FilterRule[]
  onFiltersChange: (filters: FilterRule[]) => void
  savedFilters: SavedFilter[]
  onSaveFilter: (name: string, rules: FilterRule[]) => void
  onDeleteSavedFilter: (id: string) => void
  onLoadSavedFilter: (filter: SavedFilter) => void
  tableName: string
}

// Detect column type from data
function detectColumnType(data: Record<string, any>[], column: string): 'text' | 'number' | 'date' | 'boolean' {
  const sampleValues = data.slice(0, 100).map(row => row[column]).filter(v => v != null && v !== '')
  
  if (sampleValues.length === 0) return 'text'
  
  // Check for boolean
  const booleanCount = sampleValues.filter(v => 
    typeof v === 'boolean' || v === 'true' || v === 'false' || v === '0' || v === '1'
  ).length
  if (booleanCount > sampleValues.length * 0.8) return 'boolean'
  
  // Check for date
  const datePattern = /^\d{4}-\d{2}-\d{2}|^\d{2}[\/.-]\d{2}[\/.-]\d{4}/
  const dateCount = sampleValues.filter(v => 
    typeof v === 'string' && datePattern.test(v)
  ).length
  if (dateCount > sampleValues.length * 0.8) return 'date'
  
  // Check for number
  const numberCount = sampleValues.filter(v => 
    typeof v === 'number' || (!isNaN(Number(v)) && v !== '')
  ).length
  if (numberCount > sampleValues.length * 0.8) return 'number'
  
  return 'text'
}

// Get unique values for multi-select
function getUniqueValues(data: Record<string, any>[], column: string, limit = 100): string[] {
  const values = new Set<string>()
  for (const row of data) {
    if (values.size >= limit) break
    const val = row[column]
    if (val != null && val !== '') {
      values.add(String(val))
    }
  }
  return Array.from(values).sort()
}

// Operators by type
const operatorsByType = {
  text: [
    { value: 'equals', label: 'Eşittir' },
    { value: 'not_equals', label: 'Eşit Değil' },
    { value: 'contains', label: 'İçerir' },
    { value: 'not_contains', label: 'İçermez' },
    { value: 'starts_with', label: 'İle Başlar' },
    { value: 'ends_with', label: 'İle Biter' },
    { value: 'is_empty', label: 'Boş' },
    { value: 'is_not_empty', label: 'Boş Değil' },
    { value: 'in', label: 'Listede (çoklu)' },
  ],
  number: [
    { value: 'equals', label: 'Eşittir' },
    { value: 'not_equals', label: 'Eşit Değil' },
    { value: 'greater_than', label: 'Büyüktür' },
    { value: 'greater_equal', label: 'Büyük veya Eşit' },
    { value: 'less_than', label: 'Küçüktür' },
    { value: 'less_equal', label: 'Küçük veya Eşit' },
    { value: 'between', label: 'Arasında' },
    { value: 'is_empty', label: 'Boş' },
    { value: 'is_not_empty', label: 'Boş Değil' },
  ],
  date: [
    { value: 'equals', label: 'Eşittir' },
    { value: 'not_equals', label: 'Eşit Değil' },
    { value: 'after', label: 'Sonra' },
    { value: 'before', label: 'Önce' },
    { value: 'between', label: 'Arasında' },
    { value: 'is_empty', label: 'Boş' },
    { value: 'is_not_empty', label: 'Boş Değil' },
    { value: 'today', label: 'Bugün' },
    { value: 'this_week', label: 'Bu Hafta' },
    { value: 'this_month', label: 'Bu Ay' },
  ],
  boolean: [
    { value: 'is_true', label: 'Doğru' },
    { value: 'is_false', label: 'Yanlış' },
    { value: 'is_empty', label: 'Boş' },
  ],
}

export function AdvancedFilter({
  columns,
  data,
  filters,
  onFiltersChange,
  savedFilters,
  onSaveFilter,
  onDeleteSavedFilter,
  onLoadSavedFilter,
  tableName
}: AdvancedFilterProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [filterName, setFilterName] = useState('')
  const [showSavedFilters, setShowSavedFilters] = useState(false)
  const [multiSelectOpen, setMultiSelectOpen] = useState<string | null>(null)
  const [selectedMultiValues, setSelectedMultiValues] = useState<Record<string, string[]>>({})
  const panelRef = useRef<HTMLDivElement>(null)

  // Column types cache
  const columnTypes = useMemo(() => {
    const types: Record<string, 'text' | 'number' | 'date' | 'boolean'> = {}
    columns.forEach(col => {
      types[col] = detectColumnType(data, col)
    })
    return types
  }, [columns, data])

  // Unique values for multi-select
  const uniqueValues = useMemo(() => {
    const values: Record<string, string[]> = {}
    columns.forEach(col => {
      values[col] = getUniqueValues(data, col)
    })
    return values
  }, [columns, data])

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setMultiSelectOpen(null)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const addFilter = () => {
    const newFilter: FilterRule = {
      id: Date.now().toString(),
      field: columns[0] || '',
      operator: 'contains',
      value: ''
    }
    onFiltersChange([...filters, newFilter])
  }

  const updateFilter = (id: string, updates: Partial<FilterRule>) => {
    onFiltersChange(
      filters.map(f => f.id === id ? { ...f, ...updates } : f)
    )
  }

  const removeFilter = (id: string) => {
    onFiltersChange(filters.filter(f => f.id !== id))
  }

  const clearAllFilters = () => {
    onFiltersChange([])
    setSelectedMultiValues({})
  }

  const handleSaveFilter = () => {
    if (filterName.trim() && filters.length > 0) {
      onSaveFilter(filterName.trim(), filters)
      setFilterName('')
      setSaveModalOpen(false)
    }
  }

  const handleMultiSelectToggle = (filterId: string, value: string) => {
    const current = selectedMultiValues[filterId] || []
    const newValues = current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value]
    
    setSelectedMultiValues({ ...selectedMultiValues, [filterId]: newValues })
    updateFilter(filterId, { value: newValues.join(',') })
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'number': return <Hash className="w-3.5 h-3.5" />
      case 'date': return <Calendar className="w-3.5 h-3.5" />
      default: return <Type className="w-3.5 h-3.5" />
    }
  }

  const activeFilterCount = filters.filter(f => f.value || ['is_empty', 'is_not_empty', 'is_true', 'is_false', 'today', 'this_week', 'this_month'].includes(f.operator)).length

  return (
    <div className="relative" ref={panelRef}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-all ${
          isOpen || activeFilterCount > 0
            ? 'bg-purple-600 text-white'
            : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
        }`}
      >
        <SlidersHorizontal className="w-5 h-5" />
        <span className="hidden sm:inline">Filtreler</span>
        {activeFilterCount > 0 && (
          <span className="bg-white/20 dark:bg-purple-400 text-white px-2 py-0.5 rounded-full text-xs">
            {activeFilterCount}
          </span>
        )}
      </button>

      {/* Panel */}
      {isOpen && (
        <div className="absolute left-0 top-full mt-2 w-[480px] bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-purple-500 to-pink-500">
            <div className="flex items-center justify-between text-white">
              <h3 className="font-semibold flex items-center gap-2">
                <Filter className="w-5 h-5" />
                Gelişmiş Filtreler
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowSavedFilters(!showSavedFilters)}
                  className={`p-1.5 rounded hover:bg-white/20 transition-colors ${showSavedFilters ? 'bg-white/20' : ''}`}
                  title="Kayıtlı Filtreler"
                >
                  <Save className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 hover:bg-white/20 rounded"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* Saved Filters Dropdown */}
          {showSavedFilters && savedFilters.length > 0 && (
            <div className="p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
              <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Kayıtlı Filtreler</div>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {savedFilters
                  .filter(sf => sf.tableName === tableName)
                  .map(sf => (
                    <div
                      key={sf.id}
                      className="flex items-center justify-between p-2 bg-white dark:bg-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                      <button
                        onClick={() => {
                          onLoadSavedFilter(sf)
                          setShowSavedFilters(false)
                        }}
                        className="flex-1 text-left text-sm text-slate-700 dark:text-slate-300"
                      >
                        {sf.name}
                        <span className="text-xs text-slate-400 ml-2">({sf.rules.length} kural)</span>
                      </button>
                      <button
                        onClick={() => onDeleteSavedFilter(sf.id)}
                        className="p-1 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Filter Rules */}
          <div className="max-h-80 overflow-y-auto p-4 space-y-3">
            {filters.length === 0 ? (
              <div className="text-center py-8 text-slate-400 dark:text-slate-500">
                <Filter className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Henüz filtre eklenmedi</p>
                <p className="text-xs">Veri filtrelemek için yeni bir kural ekleyin</p>
              </div>
            ) : (
              filters.map((filter, index) => {
                const type = columnTypes[filter.field] || 'text'
                const operators = operatorsByType[type]
                const needsValue = !['is_empty', 'is_not_empty', 'is_true', 'is_false', 'today', 'this_week', 'this_month'].includes(filter.operator)
                const needsSecondValue = filter.operator === 'between'
                const isMultiSelect = filter.operator === 'in'

                return (
                  <div
                    key={filter.id}
                    className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700"
                  >
                    {index > 0 && (
                      <div className="text-xs text-purple-600 dark:text-purple-400 font-medium mb-2">
                        VE
                      </div>
                    )}
                    
                    <div className="flex flex-wrap gap-2 items-start">
                      {/* Field Selector */}
                      <div className="flex-1 min-w-[120px]">
                        <select
                          value={filter.field}
                          onChange={(e) => {
                            const newType = columnTypes[e.target.value] || 'text'
                            updateFilter(filter.id, {
                              field: e.target.value,
                              operator: operatorsByType[newType][0].value,
                              value: ''
                            })
                          }}
                          className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                        >
                          {columns.map(col => (
                            <option key={col} value={col}>
                              {col}
                            </option>
                          ))}
                        </select>
                        <div className="flex items-center gap-1 mt-1 text-xs text-slate-400">
                          {getTypeIcon(type)}
                          <span>{type === 'text' ? 'Metin' : type === 'number' ? 'Sayı' : type === 'date' ? 'Tarih' : 'Boolean'}</span>
                        </div>
                      </div>

                      {/* Operator Selector */}
                      <div className="w-36">
                        <select
                          value={filter.operator}
                          onChange={(e) => updateFilter(filter.id, { operator: e.target.value, value: '', value2: '' })}
                          className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                        >
                          {operators.map(op => (
                            <option key={op.value} value={op.value}>
                              {op.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Value Input */}
                      {needsValue && !isMultiSelect && (
                        <div className={`flex-1 min-w-[100px] ${needsSecondValue ? 'flex gap-2' : ''}`}>
                          <input
                            type={type === 'date' ? 'date' : type === 'number' ? 'number' : 'text'}
                            value={filter.value}
                            onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
                            placeholder={type === 'date' ? '' : 'Değer...'}
                            className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                          />
                          {needsSecondValue && (
                            <>
                              <span className="self-center text-slate-400">-</span>
                              <input
                                type={type === 'date' ? 'date' : type === 'number' ? 'number' : 'text'}
                                value={filter.value2 || ''}
                                onChange={(e) => updateFilter(filter.id, { value2: e.target.value })}
                                placeholder={type === 'date' ? '' : 'Değer...'}
                                className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                              />
                            </>
                          )}
                        </div>
                      )}

                      {/* Multi-Select */}
                      {isMultiSelect && (
                        <div className="flex-1 min-w-[150px] relative">
                          <button
                            onClick={() => setMultiSelectOpen(multiSelectOpen === filter.id ? null : filter.id)}
                            className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-left flex items-center justify-between"
                          >
                            <span className="truncate">
                              {(selectedMultiValues[filter.id] || filter.value.split(',').filter(Boolean)).length > 0
                                ? `${(selectedMultiValues[filter.id] || filter.value.split(',').filter(Boolean)).length} seçili`
                                : 'Seçin...'}
                            </span>
                            <ChevronDown className="w-4 h-4 flex-shrink-0" />
                          </button>
                          
                          {multiSelectOpen === filter.id && (
                            <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
                              {uniqueValues[filter.field]?.map(val => {
                                const isSelected = (selectedMultiValues[filter.id] || filter.value.split(',').filter(Boolean)).includes(val)
                                return (
                                  <button
                                    key={val}
                                    onClick={() => handleMultiSelectToggle(filter.id, val)}
                                    className="w-full px-3 py-2 text-sm text-left hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
                                  >
                                    <div className={`w-4 h-4 rounded border ${isSelected ? 'bg-purple-600 border-purple-600' : 'border-slate-300 dark:border-slate-600'} flex items-center justify-center`}>
                                      {isSelected && <Check className="w-3 h-3 text-white" />}
                                    </div>
                                    <span className="truncate">{val}</span>
                                  </button>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Remove Button */}
                      <button
                        onClick={() => removeFilter(filter.id)}
                        className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex items-center justify-between gap-2">
            <button
              onClick={addFilter}
              className="px-4 py-2 text-sm bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Kural Ekle
            </button>
            
            <div className="flex gap-2">
              {filters.length > 0 && (
                <>
                  <button
                    onClick={clearAllFilters}
                    className="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
                  >
                    Temizle
                  </button>
                  <button
                    onClick={() => setSaveModalOpen(true)}
                    className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    Kaydet
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Save Filter Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSaveModalOpen(false)}>
          <div
            className="bg-white dark:bg-slate-800 rounded-xl p-6 w-96 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Filtreyi Kaydet</h3>
            <input
              type="text"
              value={filterName}
              onChange={(e) => setFilterName(e.target.value)}
              placeholder="Filtre adı..."
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500 mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setSaveModalOpen(false)}
                className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                İptal
              </button>
              <button
                onClick={handleSaveFilter}
                disabled={!filterName.trim()}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
              >
                Kaydet
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdvancedFilter
