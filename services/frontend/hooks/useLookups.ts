/**
 * useLookups Hook
 * Bitrix24 ID -> Name çözümlemesi için hook
 * Tüm lookup değerlerini cache'ler ve ID'leri isimlere çevirir
 */
'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { apiUrl } from '@/lib/config'

interface LookupValue {
  id: string
  name: string
  color?: string
  semantics?: string
  category_id?: string
  sort?: number
}

interface DealCategory {
  id: string
  name: string
  sort: number
  is_locked: boolean
}

interface LookupCache {
  lookups: Record<string, LookupValue[]>
  deal_categories: DealCategory[]
  total_count: number
  entity_types: string[]
}

interface ResolvedValue {
  id: string
  name: string
  color?: string
  semantics?: string
  resolved: boolean
}

// Global cache - tüm hook instance'ları arasında paylaşılır
let globalCache: LookupCache | null = null
let cachePromise: Promise<LookupCache> | null = null

export function useLookups() {
  const [cache, setCache] = useState<LookupCache | null>(globalCache)
  const [loading, setLoading] = useState(!globalCache)
  const [error, setError] = useState<string | null>(null)

  // Tüm lookup'ları yükle
  useEffect(() => {
    if (globalCache) {
      setCache(globalCache)
      setLoading(false)
      return
    }

    // Zaten bir istek varsa bekle
    if (cachePromise) {
      cachePromise.then(data => {
        setCache(data)
        setLoading(false)
      }).catch(err => {
        setError(err.message)
        setLoading(false)
      })
      return
    }

    // Yeni istek başlat
    setLoading(true)
    cachePromise = fetch(apiUrl('/api/lookups/all'))
      .then(res => {
        if (!res.ok) throw new Error('Lookup verileri yüklenemedi')
        return res.json()
      })
      .then((data: LookupCache) => {
        globalCache = data
        setCache(data)
        setLoading(false)
        return data
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
        cachePromise = null
        throw err
      })
  }, [])

  // ID'yi isme çevir
  const resolve = useCallback((entityType: string, statusId: string): ResolvedValue => {
    if (!cache || !statusId) {
      return { id: statusId || '', name: statusId || '', resolved: false }
    }

    // Deal stage için özel handling
    let lookupEntityType = entityType.toUpperCase()
    
    // STAGE_ID için category'ye göre doğru entity_type'ı bul
    if (entityType === 'STAGE_ID' && statusId.includes(':')) {
      const prefix = statusId.split(':')[0]
      if (prefix.startsWith('C')) {
        const categoryId = prefix.substring(1)
        lookupEntityType = `DEAL_STAGE_${categoryId}`
      }
    }

    const values = cache.lookups[lookupEntityType] || []
    const found = values.find(v => v.id === statusId)

    if (found) {
      return {
        id: statusId,
        name: found.name,
        color: found.color,
        semantics: found.semantics,
        resolved: true
      }
    }

    return { id: statusId, name: statusId, resolved: false }
  }, [cache])

  // Birden fazla ID'yi toplu çöz
  const resolveMany = useCallback((items: Array<{entityType: string, statusId: string}>): ResolvedValue[] => {
    return items.map(item => resolve(item.entityType, item.statusId))
  }, [resolve])

  // Entity type için tüm değerleri getir
  const getValues = useCallback((entityType: string): LookupValue[] => {
    if (!cache) return []
    return cache.lookups[entityType.toUpperCase()] || []
  }, [cache])

  // Deal kategorilerini getir
  const getDealCategories = useCallback((): DealCategory[] => {
    if (!cache) return []
    return cache.deal_categories
  }, [cache])

  // Deal stage'lerini kategoriyle birlikte getir
  const getDealStages = useCallback((categoryId?: string): LookupValue[] => {
    if (!cache) return []
    
    if (categoryId) {
      const entityType = categoryId === '0' ? 'DEAL_STAGE' : `DEAL_STAGE_${categoryId}`
      return cache.lookups[entityType] || []
    }

    // Tüm deal stage'leri birleştir
    const allStages: LookupValue[] = []
    for (const [key, values] of Object.entries(cache.lookups)) {
      if (key.startsWith('DEAL_STAGE')) {
        allStages.push(...values)
      }
    }
    return allStages
  }, [cache])

  // Cache'i yenile
  const refresh = useCallback(async () => {
    setLoading(true)
    globalCache = null
    cachePromise = null

    try {
      const res = await fetch(apiUrl('/api/lookups/all'))
      if (!res.ok) throw new Error('Lookup verileri yüklenemedi')
      const data: LookupCache = await res.json()
      globalCache = data
      setCache(data)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    cache,
    loading,
    error,
    resolve,
    resolveMany,
    getValues,
    getDealCategories,
    getDealStages,
    refresh
  }
}

/**
 * Field name -> Entity type mapping
 * Hangi field hangi lookup entity type'ını kullanıyor
 */
export const FIELD_LOOKUP_MAP: Record<string, Record<string, string>> = {
  leads: {
    STATUS_ID: 'STATUS',
    SOURCE_ID: 'SOURCE',
  },
  deals: {
    STAGE_ID: 'DEAL_STAGE', // Özel: kategori prefix'i ile birlikte kullanılır
    CATEGORY_ID: 'DEAL_CATEGORY',
    TYPE_ID: 'DEAL_TYPE',
    SOURCE_ID: 'SOURCE',
  },
  contacts: {
    TYPE_ID: 'CONTACT_TYPE',
    SOURCE_ID: 'SOURCE',
    HONORIFIC: 'HONORIFIC',
  },
  companies: {
    COMPANY_TYPE: 'COMPANY_TYPE',
    INDUSTRY: 'INDUSTRY',
    EMPLOYEES: 'EMPLOYEES',
  }
}

/**
 * Helper: Field için lookup entity type'ını bul
 */
export function getLookupEntityType(tableName: string, fieldName: string): string | null {
  const tableMap = FIELD_LOOKUP_MAP[tableName.toLowerCase()]
  if (!tableMap) return null
  return tableMap[fieldName.toUpperCase()] || null
}
