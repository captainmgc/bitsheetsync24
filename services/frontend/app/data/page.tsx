'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { apiUrl } from '@/lib/config'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  RowSelectionState,
  ColumnOrderState,
} from '@tanstack/react-table'
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
  Download,
  FileSpreadsheet,
  Loader2,
  Database,
  CheckSquare,
  Square,
  X,
  Calendar,
  Edit3,
  Eye,
  XCircle,
  RefreshCw,
  Wifi,
  WifiOff,
  Pause,
  Play
} from 'lucide-react'
import { LookupBadge, DealStageBadge, DealCategoryBadge } from '@/components/ui/LookupBadge'
import { useLookups, getLookupEntityType } from '@/hooks/useLookups'
import { ColumnManager } from '@/components/data/ColumnManager'
import { AdvancedFilter, FilterRule, SavedFilter } from '@/components/data/AdvancedFilter'
import { InlineEditCell } from '@/components/data/InlineEditCell'

interface TableData {
  [key: string]: any
}

interface View {
  id: number
  view_name: string
  table_name: string
}

// Storage keys
const STORAGE_KEY_PREFIX = 'bitsheet24_data_'
const getStorageKey = (tableName: string, type: string) => `${STORAGE_KEY_PREFIX}${tableName}_${type}`

// Filter data based on rules
function applyFilters(data: TableData[], filters: FilterRule[]): TableData[] {
  if (filters.length === 0) return data

  return data.filter(row => {
    return filters.every(filter => {
      const value = row[filter.field]
      const filterValue = filter.value?.toLowerCase() || ''
      const filterValue2 = filter.value2?.toLowerCase() || ''
      const rowValue = value != null ? String(value).toLowerCase() : ''

      switch (filter.operator) {
        case 'equals':
          return rowValue === filterValue
        case 'not_equals':
          return rowValue !== filterValue
        case 'contains':
          return rowValue.includes(filterValue)
        case 'not_contains':
          return !rowValue.includes(filterValue)
        case 'starts_with':
          return rowValue.startsWith(filterValue)
        case 'ends_with':
          return rowValue.endsWith(filterValue)
        case 'is_empty':
          return value == null || value === ''
        case 'is_not_empty':
          return value != null && value !== ''
        case 'greater_than':
          return Number(value) > Number(filter.value)
        case 'greater_equal':
          return Number(value) >= Number(filter.value)
        case 'less_than':
          return Number(value) < Number(filter.value)
        case 'less_equal':
          return Number(value) <= Number(filter.value)
        case 'between':
          const numVal = Number(value)
          return numVal >= Number(filter.value) && numVal <= Number(filter.value2)
        case 'after':
          return new Date(value) > new Date(filter.value)
        case 'before':
          return new Date(value) < new Date(filter.value)
        case 'today':
          const today = new Date().toISOString().split('T')[0]
          return value?.startsWith(today)
        case 'this_week': {
          const now = new Date()
          const startOfWeek = new Date(now.setDate(now.getDate() - now.getDay()))
          const endOfWeek = new Date(now.setDate(now.getDate() - now.getDay() + 6))
          const dateVal = new Date(value)
          return dateVal >= startOfWeek && dateVal <= endOfWeek
        }
        case 'this_month': {
          const now = new Date()
          const dateVal = new Date(value)
          return dateVal.getMonth() === now.getMonth() && dateVal.getFullYear() === now.getFullYear()
        }
        case 'is_true':
          return value === true || value === 'true' || value === '1' || value === 1
        case 'is_false':
          return value === false || value === 'false' || value === '0' || value === 0
        case 'in':
          const inValues = filter.value.split(',').map(v => v.trim().toLowerCase())
          return inValues.includes(rowValue)
        default:
          return true
      }
    })
  })
}

export default function DataViewerPage() {
  const { data: session } = useSession()
  const { resolve, loading: lookupsLoading } = useLookups()
  const [selectedTable, setSelectedTable] = useState<string>('contacts')
  const [selectedView, setSelectedView] = useState<number | null>(null)
  const [availableViews, setAvailableViews] = useState<View[]>([])
  const [data, setData] = useState<TableData[]>([])
  const [loading, setLoading] = useState(false)
  const [totalRecords, setTotalRecords] = useState(0)
  
  // Table state
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    original_data: false,
    data: false,
    source_hash: false,
    fetched_at: false,
  })
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [globalFilter, setGlobalFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('') // Debounced search term for API
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 20,
  })

  // Advanced filter state
  const [advancedFilters, setAdvancedFilters] = useState<FilterRule[]>([])
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([])

  // Date filter state
  const [dateFilterColumn, setDateFilterColumn] = useState<string>('')
  const [dateFilterStart, setDateFilterStart] = useState<string>('')
  const [dateFilterEnd, setDateFilterEnd] = useState<string>('')

  // Page jump state
  const [pageJumpValue, setPageJumpValue] = useState<string>('')

  // Inline edit state
  const [editableMode, setEditableMode] = useState<boolean>(false)

  // Row detail modal state
  const [detailModalOpen, setDetailModalOpen] = useState<boolean>(false)
  const [selectedRowData, setSelectedRowData] = useState<TableData | null>(null)

  // Live update state
  const [liveUpdateEnabled, setLiveUpdateEnabled] = useState<boolean>(false)
  const [liveUpdateInterval, setLiveUpdateInterval] = useState<number>(10) // seconds
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null)
  const [isLiveRefreshing, setIsLiveRefreshing] = useState<boolean>(false)
  const liveUpdateTimerRef = useRef<NodeJS.Timeout | null>(null)
  const [newRecordsCount, setNewRecordsCount] = useState<number>(0)

  // Non-editable fields (protected)
  const nonEditableFields = useMemo(() => new Set([
    'id', 'ID', 'created_at', 'updated_at', 'synced_at', 'source_hash', 
    'original_data', 'data', 'fetched_at', 'DATE_CREATE', 'DATE_MODIFY',
    'CREATED_BY_ID', 'MODIFY_BY_ID', 'CREATED_BY', 'MODIFIED_BY'
  ]), [])

  // Tables that support Bitrix24 sync
  const syncableTables = useMemo(() => new Set([
    'contacts', 'companies', 'deals', 'leads', 'activities', 'tasks'
  ]), [])
  // Available tables
  const tables = [
    { name: 'contacts', displayName: 'Müşteriler' },
    { name: 'companies', displayName: 'Şirketler' },
    { name: 'deals', displayName: 'Anlaşmalar' },
    { name: 'activities', displayName: 'Aktiviteler' },
    { name: 'tasks', displayName: 'Görevler' },
    { name: 'task_comments', displayName: 'Görev Yorumları' },
    { name: 'leads', displayName: 'Potansiyel Müşteriler' },
  ]

  // Load saved settings from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return
    
    // Load column visibility
    const savedVisibility = localStorage.getItem(getStorageKey(selectedTable, 'visibility'))
    if (savedVisibility) {
      try {
        setColumnVisibility(JSON.parse(savedVisibility))
      } catch (e) {}
    }

    // Load column order
    const savedOrder = localStorage.getItem(getStorageKey(selectedTable, 'order'))
    if (savedOrder) {
      try {
        setColumnOrder(JSON.parse(savedOrder))
      } catch (e) {}
    }

    // Load saved filters (global)
    const savedFiltersList = localStorage.getItem(`${STORAGE_KEY_PREFIX}saved_filters`)
    if (savedFiltersList) {
      try {
        setSavedFilters(JSON.parse(savedFiltersList))
      } catch (e) {}
    }
  }, [selectedTable])

  // Fetch views when table changes
  useEffect(() => {
    fetchViews()
    setSelectedView(null)
    setAdvancedFilters([])
    setGlobalFilter('') // Clear search when table changes
    setSearchTerm('') // Clear debounced search term too
  }, [selectedTable])

  // Debounce search input - wait 500ms before triggering API call
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      setSearchTerm(globalFilter)
      // Reset to first page when search changes
      if (globalFilter !== searchTerm) {
        setPagination(prev => ({ ...prev, pageIndex: 0 }))
      }
    }, 500)
    
    return () => clearTimeout(debounceTimer)
  }, [globalFilter])

  // Fetch data when table, pagination, view, or search changes
  // Fetch data when table, pagination, view, search, or sorting changes
  useEffect(() => {
    fetchData()
  }, [selectedTable, pagination.pageIndex, pagination.pageSize, selectedView, searchTerm, sorting])

  // Live update effect
  useEffect(() => {
    if (liveUpdateEnabled) {
      // Clear any existing timer
      if (liveUpdateTimerRef.current) {
        clearInterval(liveUpdateTimerRef.current)
      }
      
      // Set up new timer
      liveUpdateTimerRef.current = setInterval(() => {
        fetchDataSilent()
      }, liveUpdateInterval * 1000)
      
      return () => {
        if (liveUpdateTimerRef.current) {
          clearInterval(liveUpdateTimerRef.current)
        }
      }
    } else {
      // Clear timer when disabled
      if (liveUpdateTimerRef.current) {
        clearInterval(liveUpdateTimerRef.current)
        liveUpdateTimerRef.current = null
      }
    }
  }, [liveUpdateEnabled, liveUpdateInterval, selectedTable, pagination.pageIndex, pagination.pageSize, selectedView, searchTerm, sorting])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (liveUpdateTimerRef.current) {
        clearInterval(liveUpdateTimerRef.current)
      }
    }
  }, [])

  const fetchViews = async () => {
    try {
      const response = await fetch(apiUrl(`/api/views/${selectedTable}`))
      if (response.ok) {
        const result = await response.json()
        setAvailableViews(result.views || [])
      }
    } catch (error) {
      console.error('Error fetching views:', error)
      setAvailableViews([])
    }
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const offset = pagination.pageIndex * pagination.pageSize
      let url = apiUrl(`/api/data/${selectedTable}?limit=${pagination.pageSize}&offset=${offset}`)
      
      if (selectedView) {
        url += `&view_id=${selectedView}`
      }
      
      // Add search parameter for server-side search
      if (searchTerm && searchTerm.trim()) {
        url += `&search=${encodeURIComponent(searchTerm.trim())}`
      }
      
      // Add sorting parameters for server-side sorting
      if (sorting.length > 0) {
        const sortColumn = sorting[0].id
        const sortOrder = sorting[0].desc ? 'desc' : 'asc'
        url += `&sort_by=${encodeURIComponent(sortColumn)}&sort_order=${sortOrder}`
      }
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error('Failed to fetch data')
      }
      
      const result = await response.json()
      setData(result.data || [])
      setTotalRecords(result.total || 0)
      setLastUpdateTime(new Date())
      setNewRecordsCount(0)
    } catch (error) {
      console.error('Error fetching data:', error)
      setData([])
      setTotalRecords(0)
    } finally {
      setLoading(false)
    }
  }

  // Silent fetch for live updates (doesn't show loading spinner)
  const fetchDataSilent = async () => {
    setIsLiveRefreshing(true)
    try {
      const offset = pagination.pageIndex * pagination.pageSize
      let url = apiUrl(`/api/data/${selectedTable}?limit=${pagination.pageSize}&offset=${offset}`)
      
      if (selectedView) {
        url += `&view_id=${selectedView}`
      }
      
      if (searchTerm && searchTerm.trim()) {
        url += `&search=${encodeURIComponent(searchTerm.trim())}`
      }
      
      if (sorting.length > 0) {
        const sortColumn = sorting[0].id
        const sortOrder = sorting[0].desc ? 'desc' : 'asc'
        url += `&sort_by=${encodeURIComponent(sortColumn)}&sort_order=${sortOrder}`
      }
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error('Failed to fetch data')
      }
      
      const result = await response.json()
      const newData = result.data || []
      const newTotal = result.total || 0
      
      // Check for new records
      if (newTotal > totalRecords) {
        setNewRecordsCount(newTotal - totalRecords)
      }
      
      // Update data
      setData(newData)
      setTotalRecords(newTotal)
      setLastUpdateTime(new Date())
    } catch (error) {
      console.error('Error fetching data (silent):', error)
    } finally {
      setIsLiveRefreshing(false)
    }
  }

  // Manual refresh
  const handleManualRefresh = useCallback(() => {
    fetchData()
  }, [selectedTable, pagination, selectedView, searchTerm, sorting])

  // Apply advanced filters to data
  const filteredData = useMemo(() => {
    let result = applyFilters(data, advancedFilters)
    
    // Apply date range filter
    if (dateFilterColumn && (dateFilterStart || dateFilterEnd)) {
      result = result.filter(row => {
        const dateValue = row[dateFilterColumn]
        if (!dateValue) return false
        
        const rowDate = new Date(dateValue)
        if (isNaN(rowDate.getTime())) return false
        
        if (dateFilterStart) {
          const startDate = new Date(dateFilterStart)
          startDate.setHours(0, 0, 0, 0)
          if (rowDate < startDate) return false
        }
        
        if (dateFilterEnd) {
          const endDate = new Date(dateFilterEnd)
          endDate.setHours(23, 59, 59, 999)
          if (rowDate > endDate) return false
        }
        
        return true
      })
    }
    
    return result
  }, [data, advancedFilters, dateFilterColumn, dateFilterStart, dateFilterEnd])

  // Clear date filter
  const clearDateFilter = useCallback(() => {
    setDateFilterColumn('')
    setDateFilterStart('')
    setDateFilterEnd('')
  }, [])

  // Handle page jump
  const handlePageJump = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const pageNum = parseInt(pageJumpValue)
    const maxPage = Math.ceil(totalRecords / pagination.pageSize)
    
    if (pageNum >= 1 && pageNum <= maxPage) {
      setPagination(prev => ({ ...prev, pageIndex: pageNum - 1 }))
      setPageJumpValue('')
    }
  }, [pageJumpValue, totalRecords, pagination.pageSize])

  // Get column names for filter
  const columnNames = useMemo(() => {
    if (data.length === 0) return []
    return Object.keys(data[0]).filter(key => 
      !['original_data', 'data', 'source_hash', 'fetched_at'].includes(key)
    )
  }, [data])

  // Known date columns for each table (Bitrix24 field names)
  const knownDateColumnsByTable: Record<string, string[]> = useMemo(() => ({
    contacts: ['DATE_CREATE', 'DATE_MODIFY', 'BIRTHDATE', 'created_at', 'updated_at', 'synced_at'],
    companies: ['DATE_CREATE', 'DATE_MODIFY', 'created_at', 'updated_at', 'synced_at'],
    deals: ['DATE_CREATE', 'DATE_MODIFY', 'BEGINDATE', 'CLOSEDATE', 'created_at', 'updated_at', 'synced_at'],
    activities: ['DATE_CREATE', 'DATE_MODIFY', 'START_TIME', 'END_TIME', 'DEADLINE', 'CREATED', 'LAST_UPDATED', 'created_at', 'updated_at', 'synced_at'],
    tasks: ['DATE_CREATE', 'DATE_MODIFY', 'CREATED_DATE', 'CHANGED_DATE', 'DEADLINE', 'START_DATE_PLAN', 'END_DATE_PLAN', 'CLOSED_DATE', 'created_at', 'updated_at', 'synced_at'],
    task_comments: ['POST_DATE', 'created_at', 'updated_at', 'synced_at'],
    leads: ['DATE_CREATE', 'DATE_MODIFY', 'DATE_CLOSED', 'created_at', 'updated_at', 'synced_at'],
  }), [])

  // Detect date columns for date filter dropdown
  const dateColumns = useMemo(() => {
    const knownColumns = knownDateColumnsByTable[selectedTable] || []
    const availableColumns = columnNames.filter(col => knownColumns.includes(col))
    
    // If no known columns found, fall back to detection
    if (availableColumns.length === 0 && data.length > 0) {
      const datePattern = /date|tarih|created|updated|modified|time|zaman|deadline|closed|begin|end|start/i
      return columnNames.filter(col => {
        // Check column name
        if (datePattern.test(col)) return true
        // Check sample values for date format
        const sampleValues = data.slice(0, 10).map(row => row[col]).filter(v => v != null)
        const dateFormatPattern = /^\d{4}-\d{2}-\d{2}|^\d{2}[\/.-]\d{2}[\/.-]\d{4}/
        const dateCount = sampleValues.filter(v => typeof v === 'string' && dateFormatPattern.test(v)).length
        return dateCount > sampleValues.length * 0.5
      })
    }
    
    return availableColumns
  }, [data, columnNames, selectedTable, knownDateColumnsByTable])

  // Date preset options
  const datePresets = useMemo(() => [
    { label: 'Bugün', getValue: () => {
      const today = new Date()
      const dateStr = today.toISOString().split('T')[0]
      return { start: dateStr, end: dateStr }
    }},
    { label: 'Dün', getValue: () => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      const dateStr = yesterday.toISOString().split('T')[0]
      return { start: dateStr, end: dateStr }
    }},
    { label: 'Bu Hafta', getValue: () => {
      const now = new Date()
      const dayOfWeek = now.getDay()
      const startOfWeek = new Date(now)
      startOfWeek.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1)) // Monday
      const endOfWeek = new Date(startOfWeek)
      endOfWeek.setDate(startOfWeek.getDate() + 6) // Sunday
      return { start: startOfWeek.toISOString().split('T')[0], end: endOfWeek.toISOString().split('T')[0] }
    }},
    { label: 'Geçen Hafta', getValue: () => {
      const now = new Date()
      const dayOfWeek = now.getDay()
      const startOfThisWeek = new Date(now)
      startOfThisWeek.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))
      const startOfLastWeek = new Date(startOfThisWeek)
      startOfLastWeek.setDate(startOfThisWeek.getDate() - 7)
      const endOfLastWeek = new Date(startOfLastWeek)
      endOfLastWeek.setDate(startOfLastWeek.getDate() + 6)
      return { start: startOfLastWeek.toISOString().split('T')[0], end: endOfLastWeek.toISOString().split('T')[0] }
    }},
    { label: 'Bu Ay', getValue: () => {
      const now = new Date()
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
      const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      return { start: startOfMonth.toISOString().split('T')[0], end: endOfMonth.toISOString().split('T')[0] }
    }},
    { label: 'Geçen Ay', getValue: () => {
      const now = new Date()
      const startOfLastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const endOfLastMonth = new Date(now.getFullYear(), now.getMonth(), 0)
      return { start: startOfLastMonth.toISOString().split('T')[0], end: endOfLastMonth.toISOString().split('T')[0] }
    }},
    { label: 'Son 7 Gün', getValue: () => {
      const now = new Date()
      const weekAgo = new Date(now)
      weekAgo.setDate(now.getDate() - 7)
      return { start: weekAgo.toISOString().split('T')[0], end: now.toISOString().split('T')[0] }
    }},
    { label: 'Son 30 Gün', getValue: () => {
      const now = new Date()
      const monthAgo = new Date(now)
      monthAgo.setDate(now.getDate() - 30)
      return { start: monthAgo.toISOString().split('T')[0], end: now.toISOString().split('T')[0] }
    }},
    { label: 'Son 90 Gün', getValue: () => {
      const now = new Date()
      const threeMonthsAgo = new Date(now)
      threeMonthsAgo.setDate(now.getDate() - 90)
      return { start: threeMonthsAgo.toISOString().split('T')[0], end: now.toISOString().split('T')[0] }
    }},
    { label: 'Bu Yıl', getValue: () => {
      const now = new Date()
      const startOfYear = new Date(now.getFullYear(), 0, 1)
      return { start: startOfYear.toISOString().split('T')[0], end: now.toISOString().split('T')[0] }
    }},
  ], [])

  // Apply date preset
  const applyDatePreset = useCallback((preset: typeof datePresets[0]) => {
    const { start, end } = preset.getValue()
    setDateFilterStart(start)
    setDateFilterEnd(end)
    // Auto-select first date column if none selected
    if (!dateFilterColumn && dateColumns.length > 0) {
      // Prefer DATE_CREATE or created_at
      const preferredCol = dateColumns.find(c => c === 'DATE_CREATE' || c === 'created_at') || dateColumns[0]
      setDateFilterColumn(preferredCol)
    }
  }, [dateFilterColumn, dateColumns])

  // Save column layout
  const handleSaveLayout = useCallback(() => {
    if (typeof window === 'undefined') return
    localStorage.setItem(getStorageKey(selectedTable, 'visibility'), JSON.stringify(columnVisibility))
    localStorage.setItem(getStorageKey(selectedTable, 'order'), JSON.stringify(columnOrder))
    alert('Kolon düzeni kaydedildi!')
  }, [selectedTable, columnVisibility, columnOrder])

  // Reset column layout
  const handleResetLayout = useCallback(() => {
    if (typeof window === 'undefined') return
    localStorage.removeItem(getStorageKey(selectedTable, 'visibility'))
    localStorage.removeItem(getStorageKey(selectedTable, 'order'))
    setColumnVisibility({
      original_data: false,
      data: false,
      source_hash: false,
      fetched_at: false,
    })
    setColumnOrder([])
    alert('Kolon düzeni sıfırlandı!')
  }, [selectedTable])

  // Save filter
  const handleSaveFilter = useCallback((name: string, rules: FilterRule[]) => {
    const newFilter: SavedFilter = {
      id: Date.now().toString(),
      name,
      tableName: selectedTable,
      rules,
      createdAt: new Date().toISOString()
    }
    const updated = [...savedFilters, newFilter]
    setSavedFilters(updated)
    if (typeof window !== 'undefined') {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}saved_filters`, JSON.stringify(updated))
    }
    alert('Filtre kaydedildi!')
  }, [savedFilters, selectedTable])

  // Delete saved filter
  const handleDeleteSavedFilter = useCallback((id: string) => {
    const updated = savedFilters.filter(f => f.id !== id)
    setSavedFilters(updated)
    if (typeof window !== 'undefined') {
      localStorage.setItem(`${STORAGE_KEY_PREFIX}saved_filters`, JSON.stringify(updated))
    }
  }, [savedFilters])

  // Load saved filter
  const handleLoadSavedFilter = useCallback((filter: SavedFilter) => {
    setAdvancedFilters(filter.rules)
  }, [])

  // Generate columns dynamically from data
  const columns = useMemo<ColumnDef<TableData>[]>(() => {
    if (data.length === 0) return []

    const keys = Object.keys(data[0])

    // Create checkbox column for row selection
    const selectColumn: ColumnDef<TableData> = {
      id: 'select',
      header: ({ table }) => (
        <button
          onClick={table.getToggleAllRowsSelectedHandler()}
          className="flex items-center justify-center w-full"
        >
          {table.getIsAllRowsSelected() ? (
            <CheckSquare className="w-4 h-4 text-blue-600" />
          ) : (
            <Square className="w-4 h-4 text-slate-400" />
          )}
        </button>
      ),
      cell: ({ row }) => (
        <button
          onClick={row.getToggleSelectedHandler()}
          className="flex items-center justify-center w-full"
        >
          {row.getIsSelected() ? (
            <CheckSquare className="w-4 h-4 text-blue-600" />
          ) : (
            <Square className="w-4 h-4 text-slate-400" />
          )}
        </button>
      ),
      enableSorting: false,
      enableHiding: false,
      size: 40,
    }

    // Create data columns
    const dataColumns: ColumnDef<TableData>[] = keys.map((key) => ({
      accessorKey: key,
      id: key,
      header: ({ column }) => {
        return (
          <button
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="flex items-center gap-2 font-medium hover:text-blue-600 transition-colors"
          >
            {key}
            {column.getIsSorted() === 'asc' ? (
              <ChevronUp className="w-4 h-4" />
            ) : column.getIsSorted() === 'desc' ? (
              <ChevronDown className="w-4 h-4" />
            ) : null}
          </button>
        )
      },
      cell: ({ getValue, row }) => {
        const value = getValue()
        const recordId = row.original.id || row.original.ID
        
        // Check if this field is editable
        const isEditable = editableMode && 
                          recordId && 
                          !nonEditableFields.has(key) &&
                          syncableTables.has(selectedTable)
        
        // Special rendering for lookup fields (not editable as inline)
        const lookupEntityType = getLookupEntityType(selectedTable, key)
        
        if (key.toUpperCase() === 'STAGE_ID' && selectedTable === 'deals') {
          const categoryId = row.original['CATEGORY_ID']
          return <DealStageBadge stageId={String(value)} categoryId={String(categoryId || '')} />
        }
        
        if (key.toUpperCase() === 'CATEGORY_ID' && selectedTable === 'deals') {
          return <DealCategoryBadge categoryId={String(value)} />
        }
        
        if (lookupEntityType) {
          return <LookupBadge entityType={lookupEntityType} statusId={String(value)} />
        }
        
        // Inline editable cell
        if (isEditable) {
          // Determine field type
          let fieldType: 'text' | 'number' | 'date' | 'boolean' = 'text'
          
          if (typeof value === 'number') {
            fieldType = 'number'
          } else if (typeof value === 'boolean') {
            fieldType = 'boolean'
          } else if (key.toLowerCase().includes('date') || key.toLowerCase().includes('time')) {
            fieldType = 'date'
          }
          
          return (
            <InlineEditCell
              value={value}
              tableName={selectedTable}
              recordId={recordId}
              fieldName={key}
              fieldType={fieldType}
              onUpdate={(newValue, bitrixSynced) => {
                // Update the local data
                const newData = [...data]
                const rowIndex = newData.findIndex(r => (r.id || r.ID) === recordId)
                if (rowIndex >= 0) {
                  newData[rowIndex] = { ...newData[rowIndex], [key]: newValue }
                  setData(newData)
                }
              }}
            />
          )
        }
        
        // Default rendering
        if (value === null || value === undefined) return '-'
        if (typeof value === 'object') return JSON.stringify(value)
        return String(value)
      },
      enableResizing: true,
      size: 150,
      minSize: 50,
      maxSize: 500,
    }))

    return [selectColumn, ...dataColumns]
  }, [data, selectedTable, selectedView, editableMode, nonEditableFields, syncableTables])

  // Open row detail modal
  const handleOpenDetail = useCallback((rowData: TableData) => {
    setSelectedRowData(rowData)
    setDetailModalOpen(true)
  }, [])

  // Create table instance
  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: (updater) => {
      // Update sorting state and reset to first page
      setSorting(updater)
      setPagination(prev => ({ ...prev, pageIndex: 0 }))
    },
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onColumnOrderChange: setColumnOrder,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    columnResizeMode: 'onChange',
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      columnOrder,
      rowSelection,
      globalFilter,
      pagination,
    },
    manualPagination: true,
    manualSorting: true, // Server-side sorting
    pageCount: Math.ceil(totalRecords / pagination.pageSize),
  })

  // Export selected rows
  const handleExportSelected = async () => {
    const selectedRows = table.getSelectedRowModel().rows.map(row => row.original)
    
    if (selectedRows.length === 0) {
      alert('Lütfen en az bir satır seçin!')
      return
    }

    try {
      const keys = Object.keys(selectedRows[0])
      const csvHeader = keys.join(',')
      const csvRows = selectedRows.map(row => 
        keys.map(key => {
          const value = row[key]
          if (value === null || value === undefined) return ''
          const stringValue = String(value)
          if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
            return `"${stringValue.replace(/"/g, '""')}"`
          }
          return stringValue
        }).join(',')
      )
      const csvContent = [csvHeader, ...csvRows].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `${selectedTable}_export_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      alert(`${selectedRows.length} satır başarıyla export edildi!`)
    } catch (error) {
      console.error('Export error:', error)
      alert('Export sırasında bir hata oluştu!')
    }
  }

  const selectedCount = Object.keys(rowSelection).length
  const displayedTable = tables.find(t => t.name === selectedTable)

  // Clear single advanced filter
  const clearAdvancedFilter = (filterId: string) => {
    setAdvancedFilters(advancedFilters.filter(f => f.id !== filterId))
  }

  return (
    <ProtectedRoute>
      <DashboardLayout noPadding fullWidth>
        <div className="flex flex-col h-[calc(100vh-73px)]">
          {/* Compact Toolbar - Spreadsheet Style */}
          <div className="flex-shrink-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-4 py-2">
            <div className="flex flex-wrap items-center gap-3">
              {/* Table Selector - Compact */}
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-500" />
                <select
                  value={selectedTable}
                  onChange={(e) => {
                    setSelectedTable(e.target.value)
                    setRowSelection({})
                    setPagination({ pageIndex: 0, pageSize: 50 })
                    setSorting([])
                    setColumnFilters([])
                    setAdvancedFilters([])
                    setGlobalFilter('')
                    setDateFilterColumn('')
                    setDateFilterStart('')
                    setDateFilterEnd('')
                    setPageJumpValue('')
                  }}
                  className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                >
                  {tables.map((table) => (
                    <option key={table.name} value={table.name}>
                      {table.displayName}
                    </option>
                  ))}
                </select>
              </div>

              {/* View Selector - Compact */}
              {availableViews.length > 0 && (
                <select
                  value={selectedView || ''}
                  onChange={(e) => {
                    setSelectedView(e.target.value ? parseInt(e.target.value) : null)
                    setPagination({ pageIndex: 0, pageSize: 50 })
                    setRowSelection({})
                    setSorting([])
                    setColumnFilters([])
                    setAdvancedFilters([])
                    setGlobalFilter('')
                    setDateFilterColumn('')
                    setDateFilterStart('')
                    setDateFilterEnd('')
                    setPageJumpValue('')
                  }}
                  className="px-3 py-1.5 text-sm border border-purple-300 dark:border-purple-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">Tüm Kayıtlar</option>
                  {availableViews.map((view) => (
                    <option key={view.id} value={view.id}>
                      {view.view_name}
                    </option>
                  ))}
                </select>
              )}

              {/* Divider */}
              <div className="h-6 w-px bg-slate-300 dark:bg-slate-600" />

              {/* Search - Server-side across all data */}
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={globalFilter ?? ''}
                  onChange={(e) => setGlobalFilter(e.target.value)}
                  placeholder="Tüm tabloda ara..."
                  className="w-52 pl-8 pr-8 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
                {globalFilter && (
                  <button
                    onClick={() => setGlobalFilter('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
                {globalFilter && globalFilter !== searchTerm && (
                  <div className="absolute right-8 top-1/2 -translate-y-1/2">
                    <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
                  </div>
                )}
              </div>

              {/* Column Manager */}
              <ColumnManager
                columns={table.getAllColumns()}
                columnVisibility={columnVisibility}
                onColumnVisibilityChange={setColumnVisibility}
                columnOrder={columnOrder}
                onColumnOrderChange={setColumnOrder}
                onSaveLayout={handleSaveLayout}
                onResetLayout={handleResetLayout}
                tableName={selectedTable}
              />

              {/* Divider */}
              <div className="h-6 w-px bg-slate-300 dark:bg-slate-600" />

              {/* Live Update Controls */}
              <div className="flex items-center gap-2">
                {/* Manual Refresh */}
                <button
                  onClick={handleManualRefresh}
                  disabled={loading || isLiveRefreshing}
                  className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 disabled:opacity-50 transition-colors"
                  title="Yenile"
                >
                  <RefreshCw className={`w-4 h-4 ${(loading || isLiveRefreshing) ? 'animate-spin' : ''}`} />
                </button>

                {/* Live Update Toggle */}
                <button
                  onClick={() => setLiveUpdateEnabled(!liveUpdateEnabled)}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-all ${
                    liveUpdateEnabled
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-600'
                  }`}
                  title={liveUpdateEnabled ? 'Canlı güncellemeyi durdur' : 'Canlı güncellemeyi başlat'}
                >
                  {liveUpdateEnabled ? (
                    <>
                      <Wifi className="w-3.5 h-3.5" />
                      <span>Canlı</span>
                      {isLiveRefreshing && <Loader2 className="w-3 h-3 animate-spin" />}
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-3.5 h-3.5" />
                      <span>Kapalı</span>
                    </>
                  )}
                </button>

                {/* Interval Selector (only when live update is enabled) */}
                {liveUpdateEnabled && (
                  <select
                    value={liveUpdateInterval}
                    onChange={(e) => setLiveUpdateInterval(parseInt(e.target.value))}
                    className="px-2 py-1 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    title="Güncelleme aralığı"
                  >
                    <option value={5}>5 sn</option>
                    <option value={10}>10 sn</option>
                    <option value={30}>30 sn</option>
                    <option value={60}>1 dk</option>
                  </select>
                )}

                {/* Last Update Time */}
                {lastUpdateTime && (
                  <span className="text-xs text-slate-500 dark:text-slate-400" title="Son güncelleme">
                    {lastUpdateTime.toLocaleTimeString('tr-TR')}
                  </span>
                )}

                {/* New Records Badge */}
                {newRecordsCount > 0 && (
                  <button
                    onClick={() => {
                      setPagination(prev => ({ ...prev, pageIndex: 0 }))
                      setNewRecordsCount(0)
                    }}
                    className="flex items-center gap-1 px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full animate-pulse"
                    title="Yeni kayıtları görmek için tıklayın"
                  >
                    +{newRecordsCount} yeni
                  </button>
                )}
              </div>

              {/* Spacer */}
              <div className="flex-1" />

              {/* Edit Mode Toggle - Compact */}
              {syncableTables.has(selectedTable) && (
                <button
                  onClick={() => setEditableMode(!editableMode)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-all flex items-center gap-1.5 ${
                    editableMode
                      ? 'bg-green-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
                  }`}
                >
                  <Edit3 className="w-4 h-4" />
                  {editableMode ? 'Düzenleme Açık' : 'Düzenle'}
                </button>
              )}

              {/* View Detail Button - Compact */}
              {selectedCount === 1 && (
                <button
                  onClick={() => {
                    const selectedRows = table.getSelectedRowModel().rows
                    if (selectedRows.length === 1) {
                      handleOpenDetail(selectedRows[0].original)
                    }
                  }}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 flex items-center gap-1.5"
                >
                  <Eye className="w-4 h-4" />
                  Detay
                </button>
              )}

              {/* Export Button - Compact */}
              {selectedCount > 0 && (
                <button
                  onClick={handleExportSelected}
                  className="px-3 py-1.5 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700 flex items-center gap-1.5"
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  {selectedCount} Satır
                </button>
              )}
            </div>

            {/* Active Filters Row - Only show when filters active */}
            {(advancedFilters.length > 0 || (dateFilterColumn && (dateFilterStart || dateFilterEnd))) && (
              <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                <span className="text-xs text-slate-500">Filtreler:</span>
                {dateFilterColumn && (dateFilterStart || dateFilterEnd) && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 rounded text-xs">
                    <Calendar className="w-3 h-3" />
                    {dateFilterColumn}: {dateFilterStart || '∞'} - {dateFilterEnd || '∞'}
                    <button onClick={clearDateFilter} className="ml-0.5 hover:bg-orange-200 rounded">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                {advancedFilters.map(filter => (
                  <span key={filter.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded text-xs">
                    {filter.field} {filter.operator} {filter.value && `"${filter.value}"`}
                    <button onClick={() => clearAdvancedFilter(filter.id)} className="ml-0.5 hover:bg-purple-200 rounded">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                <button
                  onClick={() => { setAdvancedFilters([]); clearDateFilter(); }}
                  className="text-xs text-red-600 hover:text-red-700 ml-1"
                >
                  Temizle
                </button>
              </div>
            )}

            {/* Edit Mode Info - Compact */}
            {editableMode && (
              <div className="flex items-center gap-2 mt-2 px-2 py-1 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded text-green-700 dark:text-green-400 text-xs">
                <Edit3 className="w-3.5 h-3.5" />
                <span>Çift tıklayarak hücreleri düzenleyebilirsiniz. Değişiklikler Bitrix24'e senkronize edilir.</span>
              </div>
            )}
          </div>

          {/* Status Bar - Spreadsheet Style */}
          <div className="flex-shrink-0 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 px-4 py-1.5 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
            <div className="flex items-center gap-4">
              <span>
                <strong>{totalRecords.toLocaleString('tr-TR')}</strong> kayıt
                {searchTerm && (
                  <span className="text-blue-600 ml-1">(arama sonucu)</span>
                )}
              </span>
              {(advancedFilters.length > 0 || (dateFilterColumn && (dateFilterStart || dateFilterEnd))) && (
                <span className="text-purple-600">
                  <strong>{filteredData.length}</strong> filtrelenmiş
                </span>
              )}
              {selectedCount > 0 && (
                <span className="text-blue-600">
                  <strong>{selectedCount}</strong> seçili
                </span>
              )}
              {searchTerm && (
                <span className="inline-flex items-center gap-1 text-blue-600">
                  <Search className="w-3 h-3" />
                  "{searchTerm}"
                </span>
              )}
              {sorting.length > 0 && (
                <span className="inline-flex items-center gap-1 text-green-600">
                  {sorting[0].desc ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
                  {sorting[0].id}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span>Sayfa {pagination.pageIndex + 1} / {Math.ceil(totalRecords / pagination.pageSize) || 1}</span>
            </div>
          </div>

          {/* Table Area - Full Height Spreadsheet */}
          <div className="flex-1 overflow-hidden bg-white dark:bg-slate-800">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                <span className="ml-3 text-slate-600 dark:text-slate-400">Yükleniyor...</span>
              </div>
            ) : data.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <Database className="w-16 h-16 mb-4" />
                <span>Bu tabloda veri bulunamadı.</span>
              </div>
            ) : (
              <div className="h-full overflow-auto">
                <table className="w-full border-collapse" style={{ tableLayout: 'fixed' }}>
                  <thead className="bg-slate-100 dark:bg-slate-900 sticky top-0 z-10">
                    {table.getHeaderGroups().map((headerGroup) => (
                      <tr key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <th
                            key={header.id}
                            style={{ width: header.getSize() }}
                            className="px-2 py-1.5 text-left text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider border-b border-r border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 group relative select-none"
                          >
                            {header.isPlaceholder
                              ? null
                              : flexRender(header.column.columnDef.header, header.getContext())}
                            {/* Resize Handle */}
                            {header.column.getCanResize() && (
                              <div
                                onMouseDown={header.getResizeHandler()}
                                onTouchStart={header.getResizeHandler()}
                                className={`absolute right-0 top-0 h-full w-1 cursor-col-resize select-none touch-none hover:bg-blue-500 ${
                                  header.column.getIsResizing() ? 'bg-blue-500' : 'bg-transparent'
                                }`}
                              />
                            )}
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                  <tbody>
                    {table.getRowModel().rows.map((row, rowIndex) => (
                      <tr
                        key={row.id}
                        onDoubleClick={() => {
                          if (!editableMode) {
                            handleOpenDetail(row.original)
                          }
                        }}
                        className={`
                          ${rowIndex % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-850'}
                          ${row.getIsSelected() ? '!bg-blue-50 dark:!bg-blue-950' : ''}
                          hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-colors
                          ${!editableMode ? 'cursor-pointer' : ''}
                        `}
                      >
                        {row.getVisibleCells().map((cell) => (
                          <td
                            key={cell.id}
                            style={{ width: cell.column.getSize() }}
                            className="px-2 py-1 text-sm text-slate-900 dark:text-slate-100 border-b border-r border-slate-100 dark:border-slate-700 overflow-hidden text-ellipsis whitespace-nowrap"
                          >
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Bottom Pagination Bar - Spreadsheet Style */}
          <div className="flex-shrink-0 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700 px-4 py-2">
            <div className="flex items-center justify-between">
              {/* Page Size */}
              <div className="flex items-center gap-2 text-sm">
                <span className="text-slate-600 dark:text-slate-400">Göster:</span>
                <select
                  value={pagination.pageSize}
                  onChange={(e) => setPagination({ pageIndex: 0, pageSize: Number(e.target.value) })}
                  className="px-2 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-sm"
                >
                  {[20, 50, 100, 200, 500].map((size) => (
                    <option key={size} value={size}>{size}</option>
                  ))}
                </select>
              </div>

              {/* Navigation */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPagination(prev => ({ ...prev, pageIndex: 0 }))}
                  disabled={pagination.pageIndex === 0}
                  className="p-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700"
                  title="İlk Sayfa"
                >
                  <ChevronsLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                  className="p-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700"
                  title="Önceki"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {/* Page Jump */}
                <form onSubmit={handlePageJump} className="flex items-center gap-1 mx-2">
                  <input
                    type="number"
                    min={1}
                    max={table.getPageCount()}
                    value={pageJumpValue}
                    onChange={(e) => setPageJumpValue(e.target.value)}
                    placeholder={String(pagination.pageIndex + 1)}
                    className="w-14 px-2 py-1 text-center border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-sm"
                  />
                  <span className="text-sm text-slate-600 dark:text-slate-400">/ {table.getPageCount()}</span>
                  <button
                    type="submit"
                    disabled={!pageJumpValue}
                    className="px-2 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
                  >
                    Git
                  </button>
                </form>

                <button
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                  className="p-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700"
                  title="Sonraki"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPagination(prev => ({ ...prev, pageIndex: table.getPageCount() - 1 }))}
                  disabled={pagination.pageIndex >= table.getPageCount() - 1}
                  className="p-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700"
                  title="Son Sayfa"
                >
                  <ChevronsRight className="w-4 h-4" />
                </button>
              </div>

              {/* Quick Page Buttons */}
              <div className="flex items-center gap-0.5">
                {(() => {
                  const currentPage = pagination.pageIndex
                  const totalPages = table.getPageCount()
                  const pages: number[] = []
                  
                  if (totalPages <= 7) {
                    for (let i = 0; i < totalPages; i++) pages.push(i)
                  } else {
                    pages.push(0)
                    if (currentPage > 3) pages.push(-1) // ellipsis
                    for (let i = Math.max(1, currentPage - 1); i <= Math.min(totalPages - 2, currentPage + 1); i++) {
                      pages.push(i)
                    }
                    if (currentPage < totalPages - 4) pages.push(-2) // ellipsis
                    pages.push(totalPages - 1)
                  }
                  
                  return pages.map((pageIdx, i) => {
                    if (pageIdx < 0) {
                      return <span key={`ellipsis-${i}`} className="px-1 text-slate-400">...</span>
                    }
                    return (
                      <button
                        key={pageIdx}
                        onClick={() => setPagination(prev => ({ ...prev, pageIndex: pageIdx }))}
                        className={`min-w-[28px] px-1.5 py-1 text-xs rounded transition-colors ${
                          pageIdx === currentPage
                            ? 'bg-blue-600 text-white font-medium'
                            : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        {pageIdx + 1}
                      </button>
                    )
                  })
                })()}
              </div>
            </div>
          </div>
        </div>

        {/* Row Detail Modal */}
        {detailModalOpen && selectedRowData && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col m-4">
              {/* Modal Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-blue-600 to-green-600">
                <div className="flex items-center gap-3 text-white">
                  <Eye className="w-6 h-6" />
                  <div>
                    <h2 className="text-lg font-bold">Kayıt Detayı</h2>
                    <p className="text-sm text-blue-100">
                      {displayedTable?.displayName} - ID: {selectedRowData.id || selectedRowData.ID}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setDetailModalOpen(false)
                    setSelectedRowData(null)
                  }}
                  className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition-colors"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-auto p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(selectedRowData)
                    .filter(([key]) => !['original_data', 'data', 'source_hash'].includes(key))
                    .map(([key, value]) => {
                      const lookupEntityType = getLookupEntityType(selectedTable, key)
                      
                      return (
                        <div
                          key={key}
                          className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 border border-slate-200 dark:border-slate-700"
                        >
                          <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                            {key}
                          </div>
                          <div className="text-sm text-slate-900 dark:text-white break-words">
                            {/* Special rendering for lookup fields */}
                            {key.toUpperCase() === 'STAGE_ID' && selectedTable === 'deals' ? (
                              <DealStageBadge 
                                stageId={String(value)} 
                                categoryId={String(selectedRowData['CATEGORY_ID'] || '')} 
                              />
                            ) : key.toUpperCase() === 'CATEGORY_ID' && selectedTable === 'deals' ? (
                              <DealCategoryBadge categoryId={String(value)} />
                            ) : lookupEntityType ? (
                              <LookupBadge entityType={lookupEntityType} statusId={String(value)} />
                            ) : value === null || value === undefined ? (
                              <span className="text-slate-400 italic">-</span>
                            ) : typeof value === 'object' ? (
                              <pre className="text-xs bg-slate-100 dark:bg-slate-800 p-2 rounded overflow-auto max-h-40">
                                {JSON.stringify(value, null, 2)}
                              </pre>
                            ) : typeof value === 'boolean' ? (
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                value 
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              }`}>
                                {value ? 'Evet' : 'Hayır'}
                              </span>
                            ) : String(value).length > 100 ? (
                              <div className="max-h-40 overflow-auto text-sm">{String(value)}</div>
                            ) : (
                              String(value)
                            )}
                          </div>
                        </div>
                      )
                    })}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  {Object.keys(selectedRowData).filter(k => !['original_data', 'data', 'source_hash'].includes(k)).length} alan
                </div>
                <div className="flex items-center gap-2">
                  {editableMode && syncableTables.has(selectedTable) && (
                    <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                      <Edit3 className="w-3 h-3" />
                      Düzenleme modu aktif - tabloda değişiklik yapabilirsiniz
                    </span>
                  )}
                  <button
                    onClick={() => {
                      setDetailModalOpen(false)
                      setSelectedRowData(null)
                    }}
                    className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
                  >
                    Kapat
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </DashboardLayout>
    </ProtectedRoute>
  )
}
