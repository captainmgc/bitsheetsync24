'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Check, X, Loader2, RefreshCw, AlertCircle } from 'lucide-react'
import { apiUrl } from '@/lib/config'

interface InlineEditCellProps {
  value: any
  tableName: string
  recordId: number
  fieldName: string
  fieldType?: 'text' | 'number' | 'date' | 'boolean' | 'select'
  selectOptions?: { value: string; label: string }[]
  onUpdate?: (newValue: any, bitrixSynced: boolean) => void
  disabled?: boolean
  className?: string
}

export function InlineEditCell({
  value,
  tableName,
  recordId,
  fieldName,
  fieldType = 'text',
  selectOptions,
  onUpdate,
  disabled = false,
  className = ''
}: InlineEditCellProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState<any>(value)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastSyncStatus, setLastSyncStatus] = useState<{
    success: boolean
    bitrixSynced: boolean
    message: string
  } | null>(null)
  
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement | null>(null)

  // Update local value when prop changes
  useEffect(() => {
    setEditValue(value)
  }, [value])

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      if (inputRef.current instanceof HTMLInputElement) {
        inputRef.current.select()
      }
    }
  }, [isEditing])

  const handleDoubleClick = useCallback(() => {
    if (disabled) return
    setIsEditing(true)
    setError(null)
    setLastSyncStatus(null)
  }, [disabled])

  const handleCancel = useCallback(() => {
    setIsEditing(false)
    setEditValue(value)
    setError(null)
  }, [value])

  const handleSave = useCallback(async () => {
    // Don't save if value hasn't changed
    if (editValue === value) {
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    setError(null)

    try {
      const response = await fetch(apiUrl(`/api/data/${tableName}/${recordId}`), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field: fieldName,
          value: editValue,
          sync_to_bitrix: true
        })
      })

      const result = await response.json()

      if (response.ok && result.success) {
        setIsEditing(false)
        setLastSyncStatus({
          success: true,
          bitrixSynced: result.bitrix_synced,
          message: result.message
        })
        
        if (onUpdate) {
          onUpdate(editValue, result.bitrix_synced)
        }

        // Clear success status after 3 seconds
        setTimeout(() => {
          setLastSyncStatus(null)
        }, 3000)
      } else {
        setError(result.detail || result.message || 'Güncelleme başarısız')
      }
    } catch (err) {
      setError('Bağlantı hatası')
    } finally {
      setIsSaving(false)
    }
  }, [editValue, value, tableName, recordId, fieldName, onUpdate])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }, [handleSave, handleCancel])

  // Render display value
  const renderDisplayValue = () => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'boolean') return value ? 'Evet' : 'Hayır'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  // Render input based on field type
  const renderInput = () => {
    const baseClasses = "w-full px-2 py-1 text-sm border border-blue-400 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-800"

    switch (fieldType) {
      case 'number':
        return (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="number"
            value={editValue ?? ''}
            onChange={(e) => setEditValue(e.target.value ? Number(e.target.value) : null)}
            onKeyDown={handleKeyDown}
            className={baseClasses}
            disabled={isSaving}
          />
        )

      case 'date':
        return (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="datetime-local"
            value={editValue ? editValue.slice(0, 16) : ''}
            onChange={(e) => setEditValue(e.target.value ? new Date(e.target.value).toISOString() : null)}
            onKeyDown={handleKeyDown}
            className={baseClasses}
            disabled={isSaving}
          />
        )

      case 'boolean':
        return (
          <select
            ref={inputRef as React.RefObject<HTMLSelectElement>}
            value={editValue ? 'true' : 'false'}
            onChange={(e) => setEditValue(e.target.value === 'true')}
            onKeyDown={handleKeyDown}
            className={baseClasses}
            disabled={isSaving}
          >
            <option value="true">Evet</option>
            <option value="false">Hayır</option>
          </select>
        )

      case 'select':
        return (
          <select
            ref={inputRef as React.RefObject<HTMLSelectElement>}
            value={editValue ?? ''}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className={baseClasses}
            disabled={isSaving}
          >
            <option value="">Seçiniz...</option>
            {selectOptions?.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        )

      default:
        return (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="text"
            value={editValue ?? ''}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className={baseClasses}
            disabled={isSaving}
          />
        )
    }
  }

  // Editing mode
  if (isEditing) {
    return (
      <div className="flex items-center gap-1 min-w-[150px]">
        <div className="flex-1">
          {renderInput()}
        </div>
        <div className="flex items-center gap-0.5">
          {isSaving ? (
            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
          ) : (
            <>
              <button
                onClick={handleSave}
                className="p-1 text-green-600 hover:bg-green-100 dark:hover:bg-green-900 rounded"
                title="Kaydet (Enter)"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                onClick={handleCancel}
                className="p-1 text-red-600 hover:bg-red-100 dark:hover:bg-red-900 rounded"
                title="İptal (Esc)"
              >
                <X className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  // Display mode
  return (
    <div
      onDoubleClick={handleDoubleClick}
      className={`group relative cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 px-1 py-0.5 rounded transition-colors ${className}`}
      title={disabled ? 'Düzenleme devre dışı' : 'Düzenlemek için çift tıklayın'}
    >
      <span className="inline-flex items-center gap-1">
        {renderDisplayValue()}
        
        {/* Sync status indicator */}
        {lastSyncStatus && (
          <span
            className={`inline-flex items-center ${
              lastSyncStatus.bitrixSynced
                ? 'text-green-600'
                : 'text-yellow-600'
            }`}
            title={lastSyncStatus.message}
          >
            {lastSyncStatus.bitrixSynced ? (
              <RefreshCw className="w-3 h-3" />
            ) : (
              <AlertCircle className="w-3 h-3" />
            )}
          </span>
        )}
        
        {/* Error indicator */}
        {error && (
          <span className="text-red-600" title={error}>
            <AlertCircle className="w-3 h-3" />
          </span>
        )}
      </span>
      
      {/* Edit hint on hover */}
      {!disabled && (
        <span className="absolute right-0 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-xs text-blue-500 transition-opacity">
          ✏️
        </span>
      )}
    </div>
  )
}
