/**
 * useSheetSync Hook
 * Manages Google Sheets sync state and API interactions
 * 
 * Features:
 * - OAuth flow management
 * - Sync configuration CRUD
 * - Field mapping management
 * - Sync history tracking
 * - Real-time status updates
 */

import { useState, useCallback, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { config } from '@/lib/config';

const API_BASE = config.apiUrl;

export interface UserSheetsToken {
  user_id: string;
  user_email: string;
  is_active: boolean;
  last_used_at: string;
}

export interface FieldMapping {
  id: number;
  sheet_column_index: number;
  sheet_column_name: string;
  bitrix_field: string;
  data_type: 'string' | 'number' | 'date' | 'boolean';
  is_updatable: boolean;
  is_readonly?: boolean;
  color_code?: string;
  bitrix_field_type?: string;
  bitrix_field_title?: string;
}

export interface SyncConfig {
  id: number;
  sheet_id: string;
  sheet_name: string;
  gid: string;
  entity_type: 'contacts' | 'deals' | 'companies' | 'tasks' | 'leads' | 'activities';
  webhook_url: string;
  enabled: boolean;
  color_scheme: {
    primary?: string;
    secondary?: string;
    accent?: string;
  };
  created_at: string;
  last_sync_at?: string;
  field_mappings: FieldMapping[];
  // Reverse sync fields
  status_column_index?: number;
  status_column_name?: string;
  script_id?: string;
  script_installed_at?: string;
  webhook_registered?: boolean;
}

export interface SyncLog {
  id: number;
  entity_id: string;
  row_id: number;
  status: 'pending' | 'syncing' | 'completed' | 'failed' | 'retrying';
  changes: Record<string, { old: unknown; new: unknown }>;
  error?: string;
  created_at: string;
  updated_at?: string;
}

export interface WebhookEvent {
  status: string;
  event_id: number;
  log_id: number;
}

// Bitrix24 Field Info
export interface BitrixFieldInfo {
  name: string;
  title: string;
  type: string;
  isRequired: boolean;
  isMultiple: boolean;
  editable: boolean;
}

export interface BitrixFieldSummary {
  entity_type: string;
  total_fields: number;
  editable_count: number;
  readonly_count: number;
  editable_fields: string[];
  readonly_fields: string[];
}

export interface ReverseSyncSetupResult {
  success: boolean;
  config_id: number;
  steps_completed: string[];
  editable_fields_count: number;
  readonly_fields_count: number;
  editable_columns: number;
  readonly_columns: number;
  status_column_index?: number;
  script_id?: string;
  error?: string;
}

interface UseSheetSyncReturn {
  // State
  isLoading: boolean;
  error: string | null;
  userToken: UserSheetsToken | null;
  syncConfigs: SyncConfig[];
  currentConfig: SyncConfig | null;
  syncLogs: SyncLog[];
  isAuthenticating: boolean;

  // OAuth
  startOAuth: () => Promise<void>;
  completeOAuth: (code: string, state: string) => Promise<boolean>;
  revokeAccess: () => Promise<boolean>;

  // Configuration
  createSyncConfig: (config: Partial<SyncConfig>) => Promise<SyncConfig | null>;
  getSyncConfig: (configId: number) => Promise<void>;
  deleteSyncConfig: (configId: number) => Promise<boolean>;
  loadSyncConfigs: () => Promise<void>;

  // Field Mapping
  updateFieldMapping: (mappingId: number, bitrixField: string, isUpdatable: boolean) => Promise<boolean>;

  // Sync History
  loadSyncHistory: (configId: number, statusFilter?: string, limit?: number) => Promise<void>;
  retryFailedSyncs: (configId: number) => Promise<boolean>;
  getSyncStatus: (logId: number) => Promise<SyncLog | null>;

  // Reverse Sync (NEW)
  getBitrixFields: (entityType: string, editableOnly?: boolean) => Promise<BitrixFieldSummary | null>;
  getAllBitrixFieldsSummary: () => Promise<Record<string, { total: number; editable: number; readonly: number }> | null>;
  setupReverseSync: (configId: number) => Promise<ReverseSyncSetupResult | null>;
  formatSheet: (configId: number, addStatusColumn?: boolean) => Promise<boolean>;
  installWebhook: (configId: number) => Promise<boolean>;
  uninstallWebhook: (configId: number) => Promise<boolean>;
}

export function useSheetSync(): UseSheetSyncReturn {
  const { data: session } = useSession();
  
  // State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userToken, setUserToken] = useState<UserSheetsToken | null>(null);
  const [syncConfigs, setSyncConfigs] = useState<SyncConfig[]>([]);
  const [currentConfig, setCurrentConfig] = useState<SyncConfig | null>(null);
  const [syncLogs, setSyncLogs] = useState<SyncLog[]>([]);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  // Get user ID from session
  const userId = (session?.user as any)?.id;

  // =========================================================================
  // LOAD USER TOKEN ON MOUNT
  // =========================================================================

  useEffect(() => {
    if (!userId) {
      return;
    }

    const loadUserToken = async () => {
      try {
        // First try to load existing token
        const url = `${API_BASE}/api/v1/sheet-sync/oauth/token?user_id=${userId}`;
        
        const response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (response.ok) {
          const data = await response.json();
          setUserToken(data);
        } else if (response.status === 404) {
          // No token exists yet - try auto-connect using NextAuth session info
          const userEmail = (session?.user as any)?.email;
          if (userEmail) {
            try {
              const autoConnectUrl = `${API_BASE}/api/v1/sheet-sync/oauth/auto-connect?user_id=${userId}&user_email=${encodeURIComponent(userEmail)}`;
              const autoConnectResponse = await fetch(autoConnectUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
              });

              if (autoConnectResponse.ok) {
                const autoConnectData = await autoConnectResponse.json();
                setUserToken({
                  user_id: autoConnectData.user_id,
                  user_email: autoConnectData.user_email,
                  is_active: true,
                  last_used_at: new Date().toISOString(),
                });
              }
            } catch (autoConnectErr) {
              console.error('Auto-connect failed:', autoConnectErr);
            }
          }
        } else {
          const errorText = await response.text();
          console.warn('Failed to load token:', response.status, errorText);
        }
      } catch (err) {
        console.error('Error loading user token:', err);
      }
    };

    loadUserToken();
  }, [userId, session, API_BASE]);

  // =========================================================================
  // OAUTH METHODS
  // =========================================================================

  const startOAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/api/v1/sheet-sync/oauth/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error('Failed to start OAuth flow');
      }

      const data = await response.json();
      
      // Store state for validation in callback
      sessionStorage.setItem('oauth_state', data.state);
      
      // Redirect to Google OAuth
      window.location.href = data.oauth_url;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'OAuth initialization failed';
      setError(errorMsg);
      console.error('OAuth start error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const completeOAuth = useCallback(
    async (code: string, state: string): Promise<boolean> => {
      try {
        setIsAuthenticating(true);
        setError(null);

        // Validate state
        const storedState = sessionStorage.getItem('oauth_state');
        if (state !== storedState) {
          throw new Error('Invalid state parameter - possible CSRF attack');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/oauth/callback?code=${code}&state=${state}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('OAuth callback failed');
        }

        const data = await response.json();

        if (data.success) {
          setUserToken({
            user_id: data.user_id,
            user_email: data.user_email,
            is_active: true,
            last_used_at: new Date().toISOString(),
          });

          // Clear stored state
          sessionStorage.removeItem('oauth_state');
          return true;
        }

        throw new Error(data.error || 'OAuth callback failed');
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'OAuth callback failed';
        setError(errorMsg);
        console.error('OAuth complete error:', err);
        return false;
      } finally {
        setIsAuthenticating(false);
      }
    },
    []
  );

  const revokeAccess = useCallback(async (): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);

      // TODO: Call backend to revoke tokens
      // For now, just clear local state
      setUserToken(null);
      setSyncConfigs([]);
      setCurrentConfig(null);

      return true;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to revoke access';
      setError(errorMsg);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // =========================================================================
  // CONFIGURATION METHODS
  // =========================================================================

  const createSyncConfig = useCallback(
    async (config: Partial<SyncConfig>): Promise<SyncConfig | null> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(`${API_BASE}/api/v1/sheet-sync/config?user_id=${userId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create sync config');
        }

        const newConfig = await response.json();
        setSyncConfigs((prev) => [...prev, newConfig]);
        setCurrentConfig(newConfig);

        return newConfig;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to create sync config';
        setError(errorMsg);
        console.error('Create config error:', err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [userId]
  );

  const getSyncConfig = useCallback(
    async (configId: number): Promise<void> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/config/${configId}?user_id=${userId}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to load sync config');
        }

        const config = await response.json();
        setCurrentConfig(config);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load sync config';
        setError(errorMsg);
        console.error('Get config error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [userId]
  );

  const deleteSyncConfig = useCallback(
    async (configId: number): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/config/${configId}?user_id=${userId}`,
          {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to delete sync config');
        }

        setSyncConfigs((prev) => prev.filter((c) => c.id !== configId));
        if (currentConfig?.id === configId) {
          setCurrentConfig(null);
        }

        return true;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to delete sync config';
        setError(errorMsg);
        console.error('Delete config error:', err);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, currentConfig?.id]
  );

  const loadSyncConfigs = useCallback(async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      if (!userId) {
        return;
      }

      // TODO: Implement endpoint to get all configs for user
      // For now, start with empty list
      setSyncConfigs([]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load sync configs';
      setError(errorMsg);
      console.error('Load configs error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // =========================================================================
  // FIELD MAPPING METHODS
  // =========================================================================

  const updateFieldMapping = useCallback(
    async (mappingId: number, bitrixField: string, isUpdatable: boolean): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId || !currentConfig) {
          throw new Error('User or config not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/field-mapping/${mappingId}?` +
          `config_id=${currentConfig.id}&user_id=${userId}&` +
          `bitrix_field=${bitrixField}&is_updatable=${isUpdatable}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to update field mapping');
        }

        // Update local state
        setCurrentConfig((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            field_mappings: prev.field_mappings.map((m) =>
              m.id === mappingId ? { ...m, bitrix_field: bitrixField, is_updatable: isUpdatable } : m
            ),
          };
        });

        return true;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to update field mapping';
        setError(errorMsg);
        console.error('Update mapping error:', err);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, currentConfig]
  );

  // =========================================================================
  // SYNC HISTORY METHODS
  // =========================================================================

  const loadSyncHistory = useCallback(
    async (configId: number, statusFilter?: string, limit: number = 50): Promise<void> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        let url = `${API_BASE}/api/v1/sheet-sync/logs/${configId}?user_id=${userId}&limit=${limit}`;
        if (statusFilter) {
          url += `&status_filter=${statusFilter}`;
        }

        const response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          throw new Error('Failed to load sync history');
        }

        const data = await response.json();
        setSyncLogs(data.logs);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load sync history';
        setError(errorMsg);
        console.error('Load history error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [userId]
  );

  const retryFailedSyncs = useCallback(
    async (configId: number): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/retry/${configId}?user_id=${userId}&max_retries=10`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to retry failed syncs');
        }

        // Reload history
        await loadSyncHistory(configId);
        return true;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to retry failed syncs';
        setError(errorMsg);
        console.error('Retry syncs error:', err);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, loadSyncHistory]
  );

  const getSyncStatus = useCallback(
    async (logId: number): Promise<SyncLog | null> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(`${API_BASE}/api/v1/sheet-sync/status/${logId}?user_id=${userId}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          throw new Error('Failed to load sync status');
        }

        const log = await response.json();
        return log;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load sync status';
        setError(errorMsg);
        console.error('Get status error:', err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [userId]
  );

  // =========================================================================
  // REVERSE SYNC METHODS (NEW)
  // =========================================================================

  const getBitrixFields = useCallback(
    async (entityType: string, editableOnly: boolean = false): Promise<BitrixFieldSummary | null> => {
      try {
        setIsLoading(true);
        setError(null);

        const url = `${API_BASE}/api/v1/sheet-sync/bitrix-fields/${entityType}?editable_only=${editableOnly}`;
        const response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          throw new Error('Failed to load Bitrix24 fields');
        }

        return await response.json();
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load Bitrix24 fields';
        setError(errorMsg);
        console.error('Get Bitrix fields error:', err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const getAllBitrixFieldsSummary = useCallback(
    async (): Promise<Record<string, { total: number; editable: number; readonly: number }> | null> => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE}/api/v1/sheet-sync/bitrix-fields`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          throw new Error('Failed to load Bitrix24 fields summary');
        }

        const data = await response.json();
        return data.summary;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load Bitrix24 fields summary';
        setError(errorMsg);
        console.error('Get all Bitrix fields error:', err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const setupReverseSync = useCallback(
    async (configId: number): Promise<ReverseSyncSetupResult | null> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/setup-reverse-sync/${configId}?user_id=${userId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to setup reverse sync');
        }

        const result = await response.json();

        // Update current config with new data
        if (result.success && currentConfig?.id === configId) {
          setCurrentConfig((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              status_column_index: result.status_column_index,
              script_id: result.script_id,
              webhook_registered: true,
            };
          });
        }

        return result;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to setup reverse sync';
        setError(errorMsg);
        console.error('Setup reverse sync error:', err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, currentConfig?.id]
  );

  const formatSheet = useCallback(
    async (configId: number, addStatusColumn: boolean = true): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/format-sheet/${configId}?user_id=${userId}&add_status_column=${addStatusColumn}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to format sheet');
        }

        const result = await response.json();
        return result.success;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to format sheet';
        setError(errorMsg);
        console.error('Format sheet error:', err);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [userId]
  );

  const installWebhook = useCallback(
    async (configId: number): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/install-webhook/${configId}?user_id=${userId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to install webhook');
        }

        const result = await response.json();

        // Update current config
        if (result.success && currentConfig?.id === configId) {
          setCurrentConfig((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              script_id: result.script_id,
              webhook_registered: true,
            };
          });
        }

        return result.success;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to install webhook';
        setError(errorMsg);
        console.error('Install webhook error:', err);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, currentConfig?.id]
  );

  const uninstallWebhook = useCallback(
    async (configId: number): Promise<boolean> => {
      try {
        setIsLoading(true);
        setError(null);

        if (!userId) {
          throw new Error('User ID not found');
        }

        const response = await fetch(
          `${API_BASE}/api/v1/sheet-sync/uninstall-webhook/${configId}?user_id=${userId}`,
          {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to uninstall webhook');
        }

        const result = await response.json();

        // Update current config
        if (result.success && currentConfig?.id === configId) {
          setCurrentConfig((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              script_id: undefined,
              webhook_registered: false,
            };
          });
        }

        return result.success;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to uninstall webhook';
        setError(errorMsg);
        console.error('Uninstall webhook error:', err);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    [userId, currentConfig?.id]
  );

  return {
    // State
    isLoading,
    error,
    userToken,
    syncConfigs,
    currentConfig,
    syncLogs,
    isAuthenticating,

    // OAuth
    startOAuth,
    completeOAuth,
    revokeAccess,

    // Configuration
    createSyncConfig,
    getSyncConfig,
    deleteSyncConfig,
    loadSyncConfigs,

    // Field Mapping
    updateFieldMapping,

    // Sync History
    loadSyncHistory,
    retryFailedSyncs,
    getSyncStatus,

    // Reverse Sync (NEW)
    getBitrixFields,
    getAllBitrixFieldsSummary,
    setupReverseSync,
    formatSheet,
    installWebhook,
    uninstallWebhook,
  };
}
