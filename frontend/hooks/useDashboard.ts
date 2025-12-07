"use client";

import { useState, useCallback } from 'react';
import { apiUrl } from '@/lib/config';

// Types
export interface EntityStats {
  deals: number;
  contacts: number;
  companies: number;
  tasks: number;
  activities: number;
  last_updated: string;
}

export interface StageStats {
  stage_id: string;
  stage_name: string;
  count: number;
  total_amount: number;
  percentage: number;
}

export interface DealsByStage {
  stages: StageStats[];
  total_deals: number;
  total_amount: number;
}

export interface RecentActivity {
  id: number;
  type: string;
  entity_type: string | null;
  config_name: string | null;
  direction: string | null;
  status: string | null;
  message: string | null;
  timestamp: string;
  details: Record<string, unknown> | null;
}

export interface SyncStatus {
  overall_status: string;
  active_configs: number;
  total_configs: number;
  last_sync: string | null;
  errors_last_24h: number;
  success_rate: number;
  configs: Array<{
    id: number;
    name: string;
    status: string;
    last_sync: string | null;
    direction: string | null;
    error_count: number;
  }>;
}

export interface TrendDataPoint {
  date: string;
  sync_count: number;
  success_count: number;
  error_count: number;
}

export interface DashboardError {
  message: string;
  code?: string;
}

export function useDashboard(userId?: string) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<DashboardError | null>(null);
  
  // Stats state
  const [entityStats, setEntityStats] = useState<EntityStats | null>(null);
  const [dealsByStage, setDealsByStage] = useState<DealsByStage | null>(null);
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [trends, setTrends] = useState<TrendDataPoint[]>([]);

  const handleError = (err: unknown) => {
    const message = err instanceof Error ? err.message : 'Beklenmeyen bir hata oluştu';
    setError({ message });
    console.error('Dashboard error:', err);
  };

  // Fetch entity stats summary
  const fetchEntityStats = useCallback(async () => {
    if (!userId) return null;
    
    try {
      const response = await fetch(
        apiUrl(`/api/v1/dashboard/stats/summary?user_id=${userId}`)
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const data: EntityStats = await response.json();
      setEntityStats(data);
      return data;
    } catch (err) {
      handleError(err);
      return null;
    }
  }, [userId]);

  // Fetch deals by stage (sales funnel)
  const fetchDealsByStage = useCallback(async () => {
    if (!userId) return null;
    
    try {
      const response = await fetch(
        apiUrl(`/api/v1/dashboard/stats/deals-by-stage?user_id=${userId}`)
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const data: DealsByStage = await response.json();
      setDealsByStage(data);
      return data;
    } catch (err) {
      handleError(err);
      return null;
    }
  }, [userId]);

  // Fetch recent activities
  const fetchRecentActivities = useCallback(async (limit: number = 20) => {
    if (!userId) return [];
    
    try {
      const response = await fetch(
        apiUrl(`/api/v1/dashboard/activities/recent?user_id=${userId}&limit=${limit}`)
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const data: RecentActivity[] = await response.json();
      setRecentActivities(data);
      return data;
    } catch (err) {
      handleError(err);
      return [];
    }
  }, [userId]);

  // Fetch sync status
  const fetchSyncStatus = useCallback(async () => {
    if (!userId) return null;
    
    try {
      const response = await fetch(
        apiUrl(`/api/v1/dashboard/sync/status?user_id=${userId}`)
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const data: SyncStatus = await response.json();
      setSyncStatus(data);
      return data;
    } catch (err) {
      handleError(err);
      return null;
    }
  }, [userId]);

  // Fetch trends
  const fetchTrends = useCallback(async (days: number = 7) => {
    if (!userId) return [];
    
    try {
      const response = await fetch(
        apiUrl(`/api/v1/dashboard/stats/trends?user_id=${userId}&days=${days}`)
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      const data: TrendDataPoint[] = await response.json();
      setTrends(data);
      return data;
    } catch (err) {
      handleError(err);
      return [];
    }
  }, [userId]);

  // Fetch all dashboard data
  const fetchAllData = useCallback(async () => {
    if (!userId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchEntityStats(),
        fetchDealsByStage(),
        fetchRecentActivities(),
        fetchSyncStatus(),
        fetchTrends()
      ]);
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [userId, fetchEntityStats, fetchDealsByStage, fetchRecentActivities, fetchSyncStatus, fetchTrends]);

  // Refresh specific data
  const refresh = useCallback(async (type?: 'stats' | 'funnel' | 'activities' | 'sync' | 'trends') => {
    setIsLoading(true);
    setError(null);
    
    try {
      switch (type) {
        case 'stats':
          await fetchEntityStats();
          break;
        case 'funnel':
          await fetchDealsByStage();
          break;
        case 'activities':
          await fetchRecentActivities();
          break;
        case 'sync':
          await fetchSyncStatus();
          break;
        case 'trends':
          await fetchTrends();
          break;
        default:
          await fetchAllData();
      }
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, [fetchEntityStats, fetchDealsByStage, fetchRecentActivities, fetchSyncStatus, fetchTrends, fetchAllData]);

  return {
    // State
    isLoading,
    error,
    entityStats,
    dealsByStage,
    recentActivities,
    syncStatus,
    trends,
    
    // Actions
    fetchEntityStats,
    fetchDealsByStage,
    fetchRecentActivities,
    fetchSyncStatus,
    fetchTrends,
    fetchAllData,
    refresh,
    
    // Utilities
    clearError: () => setError(null),
  };
}

export default useDashboard;
