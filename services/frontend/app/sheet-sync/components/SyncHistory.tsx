/**
 * Sync History Component
 * Displays sync operation logs and status indicators
 */

'use client';

import { useEffect, useState } from 'react';
import { useSheetSync } from '@/hooks/useSheetSync';

interface SyncHistoryProps {
  configId: number;
  onLoadHistory: (configId: number, statusFilter?: string, limit?: number) => Promise<void>;
}

type StatusFilter = 'all' | 'pending' | 'syncing' | 'completed' | 'failed' | 'retrying';

const STATUS_CONFIG = {
  pending: { label: 'Bekliyor', icon: '⏳', bgColor: 'bg-amber-100', textColor: 'text-amber-800' },
  syncing: { label: 'Senkronize Ediliyor', icon: '🔄', bgColor: 'bg-blue-100', textColor: 'text-blue-800' },
  completed: { label: 'Tamamlandı', icon: '✓', bgColor: 'bg-green-100', textColor: 'text-green-800' },
  failed: { label: 'Başarısız', icon: '✗', bgColor: 'bg-red-100', textColor: 'text-red-800' },
  retrying: { label: 'Yeniden Deneniyor', icon: '🔁', bgColor: 'bg-orange-100', textColor: 'text-orange-800' },
};

export default function SyncHistory({ configId, onLoadHistory }: SyncHistoryProps) {
  const { syncLogs, isLoading, retryFailedSyncs } = useSheetSync();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Load history on mount and when filter changes
  useEffect(() => {
    const filter = statusFilter === 'all' ? undefined : statusFilter;
    onLoadHistory(configId, filter, 50);
  }, [configId, statusFilter, onLoadHistory]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      onLoadHistory(configId, filter, 50);
    }, 10000);

    return () => clearInterval(interval);
  }, [configId, statusFilter, autoRefresh, onLoadHistory]);

  const handleRetry = async () => {
    if (!confirm('Tüm başarısız senkronizasyonları yeniden denemek istiyor musunuz?')) return;
    await retryFailedSyncs(configId);
  };

  const failedCount = syncLogs.filter((log) => log.status === 'failed').length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Senkronizasyon Geçmişi</h3>
          <p className="text-sm text-slate-600 mt-1">
            {syncLogs.length} senkronizasyon işlemi • {failedCount} başarısız
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
              autoRefresh
                ? 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                : 'bg-slate-100 text-slate-800 hover:bg-slate-200'
            }`}
            title={autoRefresh ? 'Otomatik yenilemeyi durdurmak için tıklayın' : 'Otomatik yenilemeyi başlatmak için tıklayın'}
          >
            {autoRefresh ? '🔄 Otomatik Yenile' : '⏸ Otomatik Yenile'}
          </button>

          {failedCount > 0 && (
            <button
              onClick={handleRetry}
              className="px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition"
            >
              🔁 {failedCount} Başarısızı Yeniden Dene
            </button>
          )}
        </div>
      </div>

      {/* Status Filters */}
      <div className="mb-6 flex flex-wrap gap-2">
        {['all', 'pending', 'syncing', 'completed', 'failed', 'retrying'].map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status as StatusFilter)}
            className={`px-3 py-2 text-sm font-medium rounded-lg transition ${
              statusFilter === status
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
            }`}
          >
            {status === 'all' ? 'Tümü' : STATUS_CONFIG[status as keyof typeof STATUS_CONFIG]?.label}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
        </div>
      )}

      {/* Logs Table */}
      {!isLoading && syncLogs.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                    Durum
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                    Kayıt / Satır
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                    Değişiklikler
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                    Zaman
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                    Detaylar
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {syncLogs.map((log) => {
                  const config = STATUS_CONFIG[log.status as keyof typeof STATUS_CONFIG];
                  const changeCount = Object.keys(log.changes || {}).length;

                  return (
                    <tr key={log.id} className="hover:bg-slate-50 transition">
                      {/* Status */}
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${
                            config?.bgColor
                          } ${config?.textColor}`}
                        >
                          {config?.icon} {config?.label}
                        </span>
                      </td>

                      {/* Entity / Row */}
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">#{log.entity_id}</div>
                        <div className="text-xs text-slate-600">Satır {log.row_id}</div>
                      </td>

                      {/* Changes Count */}
                      <td className="px-4 py-3">
                        <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
                          {changeCount} alan
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td className="px-4 py-3 text-sm text-slate-900">
                        <div>{new Date(log.created_at).toLocaleDateString()}</div>
                        <div className="text-xs text-slate-600">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </div>
                      </td>

                      {/* Details */}
                      <td className="px-4 py-3">
                        {log.error ? (
                          <details className="cursor-pointer">
                            <summary className="text-red-600 text-sm font-medium hover:text-red-700">
                              Hatayı Gör
                            </summary>
                            <pre className="mt-2 p-2 bg-red-50 rounded text-xs text-red-800 overflow-x-auto">
                              {log.error}
                            </pre>
                          </details>
                        ) : (
                          <details className="cursor-pointer">
                            <summary className="text-blue-600 text-sm font-medium hover:text-blue-700">
                              Değişiklikleri Gör
                            </summary>
                            <pre className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-800 overflow-x-auto">
                              {JSON.stringify(log.changes, null, 2)}
                            </pre>
                          </details>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && syncLogs.length === 0 && (
        <div className="text-center py-12">
          <svg
            className="w-12 h-12 text-slate-300 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-slate-600 font-medium">
            {statusFilter === 'all'
              ? 'Henüz senkronizasyon işlemi yok'
              : `${STATUS_CONFIG[statusFilter as keyof typeof STATUS_CONFIG]?.label} işlem yok`}
          </p>
          <p className="text-sm text-slate-600 mt-1">
            Google Sheet'inizdeki değişiklikler burada görünecek
          </p>
        </div>
      )}

      {/* Stats Summary */}
      {syncLogs.length > 0 && (
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Tamamlanan', count: syncLogs.filter((l) => l.status === 'completed').length },
            { label: 'Başarısız', count: syncLogs.filter((l) => l.status === 'failed').length },
            { label: 'Bekleyen', count: syncLogs.filter((l) => l.status === 'pending').length },
            { label: 'Yeniden Denenen', count: syncLogs.filter((l) => l.status === 'retrying').length },
          ].map((stat) => (
            <div key={stat.label} className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-center">
              <div className="text-2xl font-bold text-slate-900">{stat.count}</div>
              <div className="text-sm text-slate-600">{stat.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
