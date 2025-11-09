'use client'

import { useState, useEffect, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
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
} from '@tanstack/react-table'
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Search,
  Download,
  FileSpreadsheet,
  Loader2,
  Database,
  CheckSquare,
  Square
} from 'lucide-react'

interface TableData {
  [key: string]: any
}

interface View {
  id: number
  view_name: string
  table_name: string
}

export default function DataViewerPage() {
  const { data: session } = useSession()
  const [selectedTable, setSelectedTable] = useState<string>('contacts')
  const [selectedView, setSelectedView] = useState<number | null>(null)
  const [availableViews, setAvailableViews] = useState<View[]>([])
  const [data, setData] = useState<TableData[]>([])
  const [loading, setLoading] = useState(false)
  const [totalRecords, setTotalRecords] = useState(0)
  
  // Table state
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [globalFilter, setGlobalFilter] = useState('')
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 20,
  })

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

  // Fetch views when table changes
  useEffect(() => {
    fetchViews()
    setSelectedView(null) // Reset view when table changes
  }, [selectedTable])

  // Fetch data when table, pagination, or view changes
  useEffect(() => {
    fetchData()
  }, [selectedTable, pagination.pageIndex, pagination.pageSize, selectedView])

  const fetchViews = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/views/${selectedTable}`)
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
      let url = `http://localhost:8000/api/data/${selectedTable}?limit=${pagination.pageSize}&offset=${offset}`
      
      // Add view_id if selected
      if (selectedView) {
        url += `&view_id=${selectedView}`
      }
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error('Failed to fetch data')
      }
      
      const result = await response.json()
      setData(result.data || [])
      setTotalRecords(result.total || 0)
    } catch (error) {
      console.error('Error fetching data:', error)
      setData([])
      setTotalRecords(0)
    } finally {
      setLoading(false)
    }
  }

  // Generate columns dynamically from data
  const columns = useMemo<ColumnDef<TableData>[]>(() => {
    if (data.length === 0) return []

    // Get keys from first row
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
    }

    // Create data columns
    const dataColumns: ColumnDef<TableData>[] = keys.map((key) => ({
      accessorKey: key,
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
      cell: ({ getValue }) => {
        const value = getValue()
        if (value === null || value === undefined) return '-'
        if (typeof value === 'object') return JSON.stringify(value)
        return String(value)
      },
    }))

    return [selectColumn, ...dataColumns]
  }, [data, selectedTable, selectedView])

  // Create table instance
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
      pagination,
    },
    manualPagination: true,
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
      // Convert selected rows to CSV format
      const keys = Object.keys(selectedRows[0])
      const csvHeader = keys.join(',')
      const csvRows = selectedRows.map(row => 
        keys.map(key => {
          const value = row[key]
          // Handle special characters and quotes in CSV
          if (value === null || value === undefined) return ''
          const stringValue = String(value)
          if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
            return `"${stringValue.replace(/"/g, '""')}"`
          }
          return stringValue
        }).join(',')
      )
      const csvContent = [csvHeader, ...csvRows].join('\n')
      
      // Create download
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

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-green-600 rounded-xl p-6 text-white shadow-lg">
            <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
              <Database className="w-8 h-8" />
              Veri Görüntüleme
            </h1>
            <p className="text-blue-100">
              Bitrix24 verilerinizi görüntüleyin, filtreleyin ve dışa aktarın
            </p>
          </div>

          {/* Controls */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
              {/* Table Selector */}
              <div className="flex-1 max-w-xs">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Tablo Seçin
                </label>
                <select
                  value={selectedTable}
                  onChange={(e) => {
                    setSelectedTable(e.target.value)
                    setRowSelection({})
                    setPagination({ pageIndex: 0, pageSize: 20 })
                    setSorting([])
                    setColumnFilters([])
                    setColumnVisibility({})
                    setGlobalFilter('')
                  }}
                  className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {tables.map((table) => (
                    <option key={table.name} value={table.name}>
                      {table.displayName}
                    </option>
                  ))}
                </select>
              </div>

              {/* View Selector */}
              {availableViews.length > 0 && (
                <div className="flex-1 max-w-xs">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    View Seçin
                  </label>
                  <select
                    value={selectedView || ''}
                    onChange={(e) => {
                      setSelectedView(e.target.value ? parseInt(e.target.value) : null)
                      setPagination({ pageIndex: 0, pageSize: 20 })
                      setRowSelection({})
                      setSorting([])
                      setColumnFilters([])
                      setGlobalFilter('')
                    }}
                    className="w-full px-4 py-2 border border-purple-300 dark:border-purple-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="">Tüm Kayıtlar</option>
                    {availableViews.map((view) => (
                      <option key={view.id} value={view.id}>
                        {view.view_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Search */}
              <div className="flex-1 max-w-md">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Arama
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input
                    type="text"
                    value={globalFilter ?? ''}
                    onChange={(e) => setGlobalFilter(e.target.value)}
                    placeholder="Tabloda ara..."
                    className="w-full pl-10 pr-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Export Selected Button */}
              {selectedCount > 0 && (
                <div className="flex items-end">
                  <button
                    onClick={handleExportSelected}
                    className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:shadow-lg transition-all flex items-center gap-2"
                  >
                    <FileSpreadsheet className="w-5 h-5" />
                    Seçili {selectedCount} Satırı Aktar
                  </button>
                </div>
              )}
            </div>

            {/* Info Bar */}
            <div className="mt-4 flex items-center justify-between text-sm text-slate-600 dark:text-slate-400">
              <div>
                Toplam <strong>{totalRecords.toLocaleString('tr-TR')}</strong> kayıt
                {selectedCount > 0 && (
                  <span className="ml-2">
                    • <strong>{selectedCount}</strong> satır seçili
                  </span>
                )}
              </div>
              <div>
                Sayfa {pagination.pageIndex + 1} / {Math.ceil(totalRecords / pagination.pageSize)}
              </div>
            </div>
          </div>

          {/* Table */}
          <div 
            key={`${selectedTable}-${selectedView || 'all'}`}
            className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden"
          >
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                <span className="ml-3 text-slate-600 dark:text-slate-400">Yükleniyor...</span>
              </div>
            ) : data.length === 0 ? (
              <div className="text-center py-20">
                <Database className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <div className="text-slate-600 dark:text-slate-400">
                  Bu tabloda veri bulunamadı.
                </div>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
                      {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id}>
                          {headerGroup.headers.map((header) => (
                            <th
                              key={header.id}
                              className="px-4 py-3 text-left text-xs font-medium text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                            >
                              {header.isPlaceholder
                                ? null
                                : flexRender(
                                    header.column.columnDef.header,
                                    header.getContext()
                                  )}
                            </th>
                          ))}
                        </tr>
                      ))}
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                      {table.getRowModel().rows.map((row) => (
                        <tr
                          key={row.id}
                          className={`hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors ${
                            row.getIsSelected() ? 'bg-blue-50 dark:bg-blue-950' : ''
                          }`}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <td
                              key={cell.id}
                              className="px-4 py-3 text-sm text-slate-900 dark:text-slate-100 whitespace-nowrap"
                            >
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="bg-slate-50 dark:bg-slate-900 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-700 dark:text-slate-300">
                        Sayfa başına:
                      </span>
                      <select
                        value={pagination.pageSize}
                        onChange={(e) => {
                          setPagination({
                            pageIndex: 0,
                            pageSize: Number(e.target.value),
                          })
                        }}
                        className="px-3 py-1 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                      >
                        {[10, 20, 50, 100].map((size) => (
                          <option key={size} value={size}>
                            {size}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => table.previousPage()}
                        disabled={!table.getCanPreviousPage()}
                        className="px-3 py-1 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                      >
                        <ChevronLeft className="w-5 h-5" />
                      </button>
                      
                      <span className="text-sm text-slate-700 dark:text-slate-300 px-4">
                        {pagination.pageIndex + 1} / {table.getPageCount()}
                      </span>
                      
                      <button
                        onClick={() => table.nextPage()}
                        disabled={!table.getCanNextPage()}
                        className="px-3 py-1 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                      >
                        <ChevronRight className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
