/**
 * LookupBadge Component
 * Bitrix24 ID'lerini isme çevirip badge olarak gösterir
 * Renk bilgisi varsa arka plan rengi olarak kullanır
 */
'use client'

import { useLookups } from '@/hooks/useLookups'
import { cn } from '@/lib/utils'

interface LookupBadgeProps {
  entityType: string
  statusId: string
  className?: string
  showId?: boolean
  fallback?: string
}

export function LookupBadge({ 
  entityType, 
  statusId, 
  className,
  showId = false,
  fallback
}: LookupBadgeProps) {
  const { resolve, loading } = useLookups()
  
  if (!statusId) {
    return <span className={cn("text-slate-400", className)}>-</span>
  }

  if (loading) {
    return (
      <span className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 animate-pulse",
        className
      )}>
        ...
      </span>
    )
  }

  const resolved = resolve(entityType, statusId)
  
  // Renk varsa kullan
  const bgColor = resolved.color && resolved.color !== '#' ? resolved.color : undefined
  const textColor = bgColor ? getContrastColor(bgColor) : undefined
  
  // Semantics'e göre stil
  const semanticsStyles = getSemanticStyles(resolved.semantics)

  return (
    <span 
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        !bgColor && semanticsStyles.bg,
        !bgColor && semanticsStyles.text,
        className
      )}
      style={bgColor ? { backgroundColor: bgColor, color: textColor } : undefined}
      title={showId ? `ID: ${statusId}` : undefined}
    >
      {resolved.name || fallback || statusId}
    </span>
  )
}

/**
 * LookupText Component
 * Badge olmadan sadece metin olarak gösterir
 */
export function LookupText({ 
  entityType, 
  statusId, 
  className,
  fallback
}: Omit<LookupBadgeProps, 'showId'>) {
  const { resolve, loading } = useLookups()
  
  if (!statusId) {
    return <span className={cn("text-slate-400", className)}>-</span>
  }

  if (loading) {
    return <span className={cn("text-slate-400 animate-pulse", className)}>...</span>
  }

  const resolved = resolve(entityType, statusId)
  
  return (
    <span 
      className={cn(className)}
      style={resolved.color && resolved.color !== '#' ? { color: resolved.color } : undefined}
    >
      {resolved.name || fallback || statusId}
    </span>
  )
}

/**
 * DealStageBadge Component
 * Deal stage için özel component - category_id'ye göre doğru entity_type'ı otomatik seçer
 */
interface DealStageBadgeProps {
  stageId: string
  categoryId?: string
  className?: string
}

export function DealStageBadge({ stageId, categoryId, className }: DealStageBadgeProps) {
  const { cache, loading } = useLookups()
  
  if (!stageId) {
    return <span className={cn("text-slate-400", className)}>-</span>
  }

  if (loading || !cache) {
    return (
      <span className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 animate-pulse",
        className
      )}>
        ...
      </span>
    )
  }

  // Stage ID'den category'yi çıkar (örn: C24:LOSE -> 24)
  let entityType = 'DEAL_STAGE'
  if (stageId.includes(':')) {
    const prefix = stageId.split(':')[0]
    if (prefix.startsWith('C')) {
      const catId = prefix.substring(1)
      entityType = `DEAL_STAGE_${catId}`
    }
  } else if (categoryId) {
    entityType = categoryId === '0' ? 'DEAL_STAGE' : `DEAL_STAGE_${categoryId}`
  }

  const values = cache.lookups[entityType] || []
  const found = values.find(v => v.id === stageId)

  if (!found) {
    return (
      <span className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600",
        className
      )}>
        {stageId}
      </span>
    )
  }

  const bgColor = found.color && found.color !== '#' ? found.color : '#6b7280'
  const textColor = getContrastColor(bgColor)

  return (
    <span 
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        className
      )}
      style={{ backgroundColor: bgColor, color: textColor }}
    >
      {found.name}
    </span>
  )
}

/**
 * DealCategoryBadge Component
 * Deal category (pipeline) için badge
 */
interface DealCategoryBadgeProps {
  categoryId: string
  className?: string
}

export function DealCategoryBadge({ categoryId, className }: DealCategoryBadgeProps) {
  const { getDealCategories, loading } = useLookups()
  
  if (!categoryId || categoryId === '0') {
    return (
      <span className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600",
        className
      )}>
        Varsayılan
      </span>
    )
  }

  if (loading) {
    return (
      <span className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 animate-pulse",
        className
      )}>
        ...
      </span>
    )
  }

  const categories = getDealCategories()
  const found = categories.find(c => c.id === categoryId)

  return (
    <span className={cn(
      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800",
      className
    )}>
      {found?.name || `Kategori ${categoryId}`}
    </span>
  )
}

// Helper: Arka plan rengine göre kontrast metin rengi seç
function getContrastColor(hexColor: string): string {
  if (!hexColor || hexColor === '#') return '#000000'
  
  const hex = hexColor.replace('#', '')
  const r = parseInt(hex.substr(0, 2), 16)
  const g = parseInt(hex.substr(2, 2), 16)
  const b = parseInt(hex.substr(4, 2), 16)
  
  // Luminance hesapla
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  
  return luminance > 0.5 ? '#000000' : '#ffffff'
}

// Helper: Semantics'e göre stil
function getSemanticStyles(semantics?: string): { bg: string, text: string } {
  switch (semantics) {
    case 'S': // Success
      return { bg: 'bg-green-100', text: 'text-green-800' }
    case 'F': // Failure
      return { bg: 'bg-red-100', text: 'text-red-800' }
    case 'process':
      return { bg: 'bg-blue-100', text: 'text-blue-800' }
    default:
      return { bg: 'bg-slate-100', text: 'text-slate-700' }
  }
}
