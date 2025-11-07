/**
 * Sheet Selector Component
 * Displays available sheets and allows selection
 */

'use client';

import { useState, useMemo } from 'react';
import { SyncConfig } from '@/hooks/useSheetSync';

interface SheetSelectorProps {
  configs: SyncConfig[];
  currentConfig: SyncConfig | null;
  onSelect: (configId: number) => Promise<void>;
  onCreate: (config: Partial<SyncConfig>) => Promise<SyncConfig | null>;
  onDelete: (configId: number) => Promise<boolean>;
}

const ENTITY_TYPES = [
  { value: 'contacts' as const, label: 'Contacts', description: 'CRM Contacts' },
  { value: 'deals' as const, label: 'Deals', description: 'Sales Deals' },
  { value: 'companies' as const, label: 'Companies', description: 'Company Records' },
  { value: 'tasks' as const, label: 'Tasks', description: 'Tasks & Activities' },
];

export default function SheetSelector({
  configs,
  currentConfig,
  onSelect,
  onCreate,
  onDelete,
}: SheetSelectorProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    sheet_id: '',
    sheet_name: '',
    gid: '0',
    entity_type: 'contacts' as 'contacts' | 'deals' | 'companies' | 'tasks',
  });
  const [isDeleting, setIsDeleting] = useState<number | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.sheet_id.trim()) {
      alert('Please enter a Sheet ID');
      return;
    }

    setIsCreating(true);
    try {
      const newConfig = await onCreate({
        sheet_id: formData.sheet_id,
        sheet_name: formData.sheet_name || 'Untitled Sheet',
        gid: formData.gid,
        entity_type: formData.entity_type,
        color_scheme: {
          primary: '#1f2937',
          secondary: '#374151',
          accent: '#3b82f6',
        },
      });

      if (newConfig) {
        setShowCreateForm(false);
        setFormData({
          sheet_id: '',
          sheet_name: '',
          gid: '0',
          entity_type: 'contacts',
        });
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (configId: number) => {
    if (!confirm('Are you sure you want to delete this configuration?')) {
      return;
    }

    setIsDeleting(configId);
    try {
      await onDelete(configId);
    } finally {
      setIsDeleting(null);
    }
  };

  const sortedConfigs = useMemo(
    () => [...configs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [configs]
  );

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Sync Configurations</h3>
          <p className="text-sm text-slate-600">Manage your Google Sheets sync settings</p>
        </div>

        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
        >
          + New Configuration
        </button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="mb-6 p-6 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-semibold text-slate-900 mb-4">Create New Sync Configuration</h4>

          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-900 mb-1">
                Sheet ID *
              </label>
              <input
                type="text"
                placeholder="1BxiMVs0XRA5nFMKejzYhbFS4fbb5DQKgvE2h2Xw3WmQ"
                value={formData.sheet_id}
                onChange={(e) => setFormData({ ...formData, sheet_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
              <p className="text-xs text-slate-600 mt-1">
                Find this in your Google Sheet URL: docs.google.com/spreadsheets/d/<strong>SHEET_ID</strong>/edit
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1">
                  Sheet Name
                </label>
                <input
                  type="text"
                  placeholder="My Sales Data"
                  value={formData.sheet_name}
                  onChange={(e) => setFormData({ ...formData, sheet_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-900 mb-1">
                  Sheet Tab ID (gid)
                </label>
                <input
                  type="text"
                  placeholder="0"
                  value={formData.gid}
                  onChange={(e) => setFormData({ ...formData, gid: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                />
                <p className="text-xs text-slate-600 mt-1">Usually 0 for first tab</p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-900 mb-3">
                Sync to Entity Type *
              </label>
              <div className="grid grid-cols-2 gap-2">
                {ENTITY_TYPES.map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, entity_type: type.value })}
                    className={`p-3 text-left rounded-lg border-2 transition ${
                      formData.entity_type === type.value
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="font-medium text-sm text-slate-900">{type.label}</div>
                    <div className="text-xs text-slate-600">{type.description}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-2 pt-4">
              <button
                type="submit"
                disabled={isCreating}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white rounded-lg font-medium transition"
              >
                {isCreating ? 'Creating...' : 'Create Configuration'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="flex-1 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 rounded-lg font-medium transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Configurations List */}
      {sortedConfigs.length === 0 ? (
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
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
          <p className="text-slate-600 font-medium mb-4">No configurations yet</p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
          >
            Create Your First Configuration
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {sortedConfigs.map((config) => (
            <div
              key={config.id}
              onClick={() => onSelect(config.id)}
              className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                currentConfig?.id === config.id
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-slate-900">{config.sheet_name}</h4>
                  <div className="flex gap-4 mt-2 text-sm text-slate-600">
                    <span>📋 {config.entity_type}</span>
                    <span>📅 {new Date(config.created_at).toLocaleDateString()}</span>
                    {config.last_sync_at && (
                      <span>
                        🔄 {new Date(config.last_sync_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        config.enabled
                          ? 'bg-green-100 text-green-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {config.enabled ? '✓ Active' : 'Disabled'}
                    </span>
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-slate-100 text-slate-800">
                      {config.field_mappings.length} fields
                    </span>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(config.id);
                  }}
                  disabled={isDeleting === config.id}
                  className="ml-4 p-2 text-red-600 hover:bg-red-50 rounded-lg transition disabled:opacity-50"
                  title="Delete configuration"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
