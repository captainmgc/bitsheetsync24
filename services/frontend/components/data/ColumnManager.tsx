'use client'

import { useState, useRef, useEffect } from 'react'
import { Column } from '@tanstack/react-table'
import {
  Eye,
  EyeOff,
  GripVertical,
  Settings2,
  X,
  Save,
  RotateCcw,
  Columns3
} from 'lucide-react'

interface ColumnManagerProps<T> {
  columns: Column<T, unknown>[]
  columnVisibility: Record<string, boolean>
  onColumnVisibilityChange: (visibility: Record<string, boolean>) => void
  columnOrder: string[]
  onColumnOrderChange: (order: string[]) => void
  onSaveLayout: () => void
  onResetLayout: () => void
  tableName: string
}

export function ColumnManager<T>({
  columns,
  columnVisibility,
  onColumnVisibilityChange,
  columnOrder,
  onColumnOrderChange,
  onSaveLayout,
  onResetLayout,
  tableName
}: ColumnManagerProps<T>) {
  const [isOpen, setIsOpen] = useState(false)
  const [draggedItem, setDraggedItem] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Filter columns that can be hidden (exclude 'select' column)
  const manageableColumns = columns.filter(col => col.id !== 'select')
  
  // Sort columns by order
  const orderedColumns = [...manageableColumns].sort((a, b) => {
    const aIndex = columnOrder.indexOf(a.id)
    const bIndex = columnOrder.indexOf(b.id)
    if (aIndex === -1 && bIndex === -1) return 0
    if (aIndex === -1) return 1
    if (bIndex === -1) return -1
    return aIndex - bIndex
  })

  // Filter by search
  const filteredColumns = orderedColumns.filter(col =>
    col.id.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleDragStart = (e: React.DragEvent, columnId: string) => {
    setDraggedItem(columnId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e: React.DragEvent, targetColumnId: string) => {
    e.preventDefault()
    if (!draggedItem || draggedItem === targetColumnId) return

    const currentOrder = columnOrder.length > 0 
      ? [...columnOrder] 
      : manageableColumns.map(col => col.id)
    
    const draggedIndex = currentOrder.indexOf(draggedItem)
    const targetIndex = currentOrder.indexOf(targetColumnId)

    if (draggedIndex === -1 || targetIndex === -1) return

    // Remove dragged item and insert at target position
    currentOrder.splice(draggedIndex, 1)
    currentOrder.splice(targetIndex, 0, draggedItem)

    onColumnOrderChange(currentOrder)
    setDraggedItem(null)
  }

  const handleDragEnd = () => {
    setDraggedItem(null)
  }

  const toggleColumn = (columnId: string) => {
    const newVisibility = {
      ...columnVisibility,
      [columnId]: columnVisibility[columnId] === false ? true : false
    }
    onColumnVisibilityChange(newVisibility)
  }

  const showAllColumns = () => {
    const newVisibility: Record<string, boolean> = {}
    manageableColumns.forEach(col => {
      newVisibility[col.id] = true
    })
    onColumnVisibilityChange(newVisibility)
  }

  const hideAllColumns = () => {
    const newVisibility: Record<string, boolean> = {}
    manageableColumns.forEach(col => {
      // Keep at least ID column visible
      newVisibility[col.id] = col.id.toLowerCase() === 'id'
    })
    onColumnVisibilityChange(newVisibility)
  }

  const visibleCount = manageableColumns.filter(
    col => columnVisibility[col.id] !== false
  ).length

  return (
    <div className="relative" ref={panelRef}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-all ${
          isOpen
            ? 'bg-blue-600 text-white'
            : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
        }`}
      >
        <Columns3 className="w-5 h-5" />
        <span className="hidden sm:inline">Kolonlar</span>
        <span className="text-xs bg-white/20 dark:bg-slate-600 px-2 py-0.5 rounded-full">
          {visibleCount}/{manageableColumns.length}
        </span>
      </button>

      {/* Panel */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-gradient-to-r from-blue-500 to-purple-500">
            <div className="flex items-center justify-between text-white">
              <h3 className="font-semibold flex items-center gap-2">
                <Settings2 className="w-5 h-5" />
                Kolon Yönetimi
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-white/20 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="p-3 border-b border-slate-200 dark:border-slate-700">
            <input
              type="text"
              placeholder="Kolon ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Quick Actions */}
          <div className="p-3 border-b border-slate-200 dark:border-slate-700 flex gap-2">
            <button
              onClick={showAllColumns}
              className="flex-1 px-3 py-1.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors flex items-center justify-center gap-1"
            >
              <Eye className="w-3.5 h-3.5" />
              Tümünü Göster
            </button>
            <button
              onClick={hideAllColumns}
              className="flex-1 px-3 py-1.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors flex items-center justify-center gap-1"
            >
              <EyeOff className="w-3.5 h-3.5" />
              Tümünü Gizle
            </button>
          </div>

          {/* Column List */}
          <div className="max-h-64 overflow-y-auto">
            {filteredColumns.map((column) => {
              const isVisible = columnVisibility[column.id] !== false
              const isDragging = draggedItem === column.id

              return (
                <div
                  key={column.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, column.id)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, column.id)}
                  onDragEnd={handleDragEnd}
                  className={`flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-move border-b border-slate-100 dark:border-slate-700/50 transition-all ${
                    isDragging ? 'opacity-50 bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <GripVertical className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  
                  <button
                    onClick={() => toggleColumn(column.id)}
                    className={`p-1 rounded transition-colors ${
                      isVisible
                        ? 'text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30'
                        : 'text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    {isVisible ? (
                      <Eye className="w-4 h-4" />
                    ) : (
                      <EyeOff className="w-4 h-4" />
                    )}
                  </button>
                  
                  <span className={`flex-1 text-sm truncate ${
                    isVisible 
                      ? 'text-slate-700 dark:text-slate-300' 
                      : 'text-slate-400 dark:text-slate-500 line-through'
                  }`}>
                    {column.id}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Footer Actions */}
          <div className="p-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex gap-2">
            <button
              onClick={onResetLayout}
              className="flex-1 px-3 py-2 text-sm bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors flex items-center justify-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Sıfırla
            </button>
            <button
              onClick={() => {
                onSaveLayout()
                setIsOpen(false)
              }}
              className="flex-1 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              Kaydet
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ColumnManager
