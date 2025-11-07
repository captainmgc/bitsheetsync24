'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, RefreshCw, ExternalLink } from 'lucide-react';
import { useSheetSync } from '@/hooks/useSheetSync';
import SheetSelector from './components/SheetSelector';
import FieldMappingDisplay from './components/FieldMappingDisplay';
import ColorSchemePicker from './components/ColorSchemePicker';
import SyncHistory from './components/SyncHistory';

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
  const [activeTab, setActiveTab] = useState<'configs' | 'mappings' | 'colors' | 'history'>('configs');
  
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

  const handleSelectConfig = async (configId: number) => {
    await getSyncConfig(configId);
  };

  const handleRefresh = () => {
    loadSyncConfigs();
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
            <nav className="flex gap-4">
              {[
                { id: 'configs', label: 'Yapılandırmalar', icon: '⚙️' },
                { id: 'mappings', label: 'Alan Eşleştirme', icon: '🔗', disabled: !currentConfig},
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
            {(activeTab === 'mappings' || activeTab === 'colors' || activeTab === 'history') && !currentConfig&&(
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
