'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, RefreshCw, ExternalLink, FileSpreadsheet, Clock, Table2 } from 'lucide-react';
import { useSheetSync } from '@/hooks/useSheetSync';
import { apiUrl } from '@/lib/config';
import SheetSelector from './components/SheetSelector';
import FieldMappingDisplay from './components/FieldMappingDisplay';
import ColorSchemePicker from './components/ColorSchemePicker';
import SyncHistory from './components/SyncHistory';
import ReverseSyncSetup from './components/ReverseSyncSetup';
import ChangeDetectionPreview from './components/ChangeDetectionPreview';

export default function SheetSyncPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <SheetSyncContent />
      </DashboardLayout>
    </ProtectedRoute>
  );
}

function SheetSyncContent() {
  const { data: session } = useSession();
  const [activeTab, setActiveTab] = useState<'exports' | 'configs' | 'mappings' | 'colors' | 'reverse' | 'changes' | 'history'>('exports');
  const [exportLogs, setExportLogs] = useState<any[]>([]);
  const [loadingExports, setLoadingExports] = useState(false);
  
  const {
    userToken,
    syncConfigs,
    currentConfig,
    isLoading,
    error,
    startOAuth,
    loadSyncConfigs,
    createSyncConfig,
    getSyncConfig,
    deleteSyncConfig,
    loadSyncHistory,
  } = useSheetSync();

  // Fetch export logs
  const fetchExportLogs = async () => {
    setLoadingExports(true);
    try {
      const response = await fetch(apiUrl('/api/v1/exports/?page=1&page_size=50'));
      if (response.ok) {
        const data = await response.json();
        setExportLogs(data.exports || []);
      }
    } catch (err) {
      console.error('Failed to fetch export logs:', err);
    } finally {
      setLoadingExports(false);
    }
  };

  useEffect(() => {
    fetchExportLogs();
  }, []);

  const handleSelectConfig = async (configId: number) => {
    await getSyncConfig(configId);
  };

  const handleRefresh = () => {
    loadSyncConfigs();
    fetchExportLogs();
  };

  if (isLoading && !userToken){
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Başlık ve Durum */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Google Sheets Senkronizasyon</h1>
          <p className="text-muted-foreground mt-2">
            Bitrix24 verilerinizi Google Sheets ile senkronize edin
          </p>
        </div>
        <div className="flex items-center gap-3">
          {userToken?.is_active ? (
            <Badge variant="default" className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Bağlı
            </Badge>
          ) : (
            <Badge variant="destructive" className="flex items-center gap-2">
              <XCircle className="h-4 w-4" />
              Bağlantı Gerekli
            </Badge>
          )}
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
        </div>
      </div>

      {/* Hata Mesajı */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Bağlantı Durumu */}
      {userToken?.is_active === false || userToken === null ? (
        <Card>
          <CardHeader>
            <CardTitle>Google Sheets Bağlantısı</CardTitle>
            <CardDescription>
              Google Sheets ile senkronizasyon için hesabınızı bağlayın
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <div className="text-center space-y-2">
                <p className="text-muted-foreground">
                  Google Sheets'e erişim izni vermek için aşağıdaki butona tıklayın.
                </p>
                <p className="text-sm text-muted-foreground">
                  Hesabınız otomatik olarak yapılandırılacaktır.
                </p>
              </div>
              <Button onClick={startOAuth} size="lg" className="gap-2">
                <ExternalLink className="h-4 w-4" />
                Google ile Bağlan
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Kullanıcı Bilgileri Kartı */}
          <Card>
            <CardHeader>
              <CardTitle>Bağlı Hesap</CardTitle>
              <CardDescription>Google Sheets hesap bilgileriniz</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">E-posta:</span>
                  <span className="text-sm text-muted-foreground">{userToken.user_email}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Durum:</span>
                  <Badge variant="default" className="text-xs">Aktif</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Son Kullanım:</span>
                  <span className="text-sm text-muted-foreground">
                    {new Date(userToken.last_used_at).toLocaleString('tr-TR')}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Sekme Navigasyonu */}
          <div className="border-b border-border">
            <nav className="flex gap-4 overflow-x-auto">
              {[
                { id: 'exports', label: 'Export Geçmişi', icon: '📊' },
                { id: 'configs', label: 'Yapılandırmalar', icon: '⚙️' },
                { id: 'mappings', label: 'Alan Eşleştirme', icon: '🔗', disabled: !currentConfig},
                { id: 'reverse', label: 'Çift Yönlü Senkron', icon: '🔄', disabled: !currentConfig},
                { id: 'changes', label: 'Değişiklik Algılama', icon: '🔍', disabled: !currentConfig},
                { id: 'colors', label: 'Renkler', icon: '🎨', disabled: !currentConfig},
                { id: 'history', label: 'Geçmiş', icon: '📜', disabled: !currentConfig},
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => !tab.disabled && setActiveTab(tab.id as any)}
                  disabled={tab.disabled}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    activeTab === tab.id
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Sekme İçeriği */}
          <div className="min-h-[400px]">
            {activeTab === 'exports' && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <FileSpreadsheet className="h-5 w-5" />
                        Oluşturulan E-Tablolar
                      </CardTitle>
                      <CardDescription>
                        Export işlemleri ile oluşturduğunuz Google Sheets dosyaları
                      </CardDescription>
                    </div>
                    <Button onClick={fetchExportLogs} variant="outline" size="sm" disabled={loadingExports}>
                      <RefreshCw className={`h-4 w-4 mr-2 ${loadingExports ? 'animate-spin' : ''}`} />
                      Yenile
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {loadingExports ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                  ) : exportLogs.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground">
                      <FileSpreadsheet className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Henüz export işlemi yapılmamış</p>
                      <p className="text-sm mt-2">
                        <a href="/export" className="text-primary hover:underline">
                          Export sayfasından veri aktarın →
                        </a>
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {exportLogs.map((log) => (
                        <div 
                          key={log.id} 
                          className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                        >
                          <div className="flex items-start justify-between">
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <Table2 className="h-4 w-4 text-primary" />
                                <span className="font-medium">{log.entity_name}</span>
                                <Badge variant={log.status === 'COMPLETED' ? 'default' : 'destructive'}>
                                  {log.status === 'COMPLETED' ? 'Başarılı' : log.status}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {new Date(log.created_at).toLocaleString('tr-TR')}
                                </span>
                                <span>{log.total_records || log.processed_records || 0} kayıt</span>
                              </div>
                            </div>
                            {(log.destination || log.sheet_url) && (
                              <a
                                href={log.destination || log.sheet_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary hover:underline"
                              >
                                <ExternalLink className="h-4 w-4" />
                                Aç
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {activeTab === 'configs' && (
              <Card>
                <CardContent className="pt-6">
                  <SheetSelector
                    configs={syncConfigs}
                    currentConfig={currentConfig}
                    onSelect={handleSelectConfig}
                    onCreate={createSyncConfig}
                    onDelete={deleteSyncConfig}
                  />
                </CardContent>
              </Card>
            )}

            {activeTab === 'mappings' && currentConfig && (
              <Card>
                <CardContent className="pt-6">
                  <FieldMappingDisplay config={currentConfig} />
                </CardContent>
              </Card>
            )}

            {activeTab === 'colors' && currentConfig && (
              <Card>
                <CardContent className="pt-6">
                  <ColorSchemePicker config={currentConfig} />
                </CardContent>
              </Card>
            )}

            {activeTab === 'reverse' && currentConfig && (
              <Card>
                <CardContent className="pt-6">
                  <ReverseSyncSetup config={currentConfig} onRefresh={loadSyncConfigs} />
                </CardContent>
              </Card>
            )}

            {activeTab === 'changes' && currentConfig && (
              <ChangeDetectionPreview configId={currentConfig.id} configName={currentConfig.sheet_name} />
            )}

            {activeTab === 'history' && currentConfig && (
              <Card>
                <CardContent className="pt-6">
                  <SyncHistory
                    configId={currentConfig.id}
                    onLoadHistory={loadSyncHistory}
                  />
                </CardContent>
              </Card>
            )}

            {/* Yapılandırma Seçilmedi Mesajı */}
            {(activeTab === 'mappings' || activeTab === 'colors' || activeTab === 'history' || activeTab === 'changes') && !currentConfig&&(
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">
                      Lütfen önce bir yapılandırma seçin
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
