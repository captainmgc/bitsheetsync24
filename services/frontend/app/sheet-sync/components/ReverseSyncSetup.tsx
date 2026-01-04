'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Play,
  Settings,
  FileSpreadsheet,
  Webhook,
  Palette,
  AlertTriangle,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useSheetSync, SyncConfig, ReverseSyncSetupResult, BitrixFieldSummary } from '@/hooks/useSheetSync';

interface ReverseSyncSetupProps {
  config: SyncConfig;
  onRefresh?: () => void;
}

type SetupStep = 'idle' | 'fields' | 'format' | 'webhook' | 'complete' | 'error';

const ENTITY_LABELS: Record<string, string> = {
  lead: 'Potansiyeller',
  contact: 'Kişiler',
  company: 'Firmalar',
  deal: 'Fırsatlar',
  task: 'Görevler',
  activity: 'Aktiviteler',
};

export default function ReverseSyncSetup({ config, onRefresh }: ReverseSyncSetupProps) {
  const {
    isLoading,
    error,
    getBitrixFields,
    getAllBitrixFieldsSummary,
    setupReverseSync,
    formatSheet,
    installWebhook,
    uninstallWebhook,
  } = useSheetSync();

  const [currentStep, setCurrentStep] = useState<SetupStep>('idle');
  const [stepProgress, setStepProgress] = useState(0);
  const [setupResult, setSetupResult] = useState<ReverseSyncSetupResult | null>(null);
  const [fieldSummary, setFieldSummary] = useState<BitrixFieldSummary | null>(null);
  const [allFieldsSummary, setAllFieldsSummary] = useState<Record<string, { total: number; editable: number; readonly: number }> | null>(null);
  const [stepErrors, setStepErrors] = useState<string[]>([]);

  // Load field summary on mount
  useEffect(() => {
    loadFieldSummary();
  }, [config.entity_type]);

  const loadFieldSummary = async () => {
    const summary = await getBitrixFields(config.entity_type);
    if (summary) {
      setFieldSummary(summary);
    }
    
    const allSummary = await getAllBitrixFieldsSummary();
    if (allSummary) {
      setAllFieldsSummary(allSummary);
    }
  };

  const handleOneClickSetup = async () => {
    setStepErrors([]);
    setCurrentStep('fields');
    setStepProgress(0);

    try {
      // Step 1: Setup (includes field detection)
      setStepProgress(10);
      await new Promise((resolve) => setTimeout(resolve, 500)); // Visual feedback
      
      setCurrentStep('format');
      setStepProgress(33);
      
      // Step 2: Format sheet with colors
      const formatSuccess = await formatSheet(config.id, true);
      if (!formatSuccess) {
        setStepErrors((prev) => [...prev, 'Sheet formatlanamadı']);
      }
      
      setStepProgress(66);
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      setCurrentStep('webhook');
      
      // Step 3: Full setup (includes webhook)
      const result = await setupReverseSync(config.id);
      
      setStepProgress(100);
      
      if (result?.success) {
        setSetupResult(result);
        setCurrentStep('complete');
      } else {
        setCurrentStep('error');
        if (result?.error) {
          setStepErrors((prev) => [...prev, result.error!]);
        }
      }
    } catch (err) {
      setCurrentStep('error');
      setStepErrors((prev) => [...prev, err instanceof Error ? err.message : 'Beklenmeyen hata']);
    }
  };

  const handleUninstall = async () => {
    const success = await uninstallWebhook(config.id);
    if (success) {
      setSetupResult(null);
      setCurrentStep('idle');
      onRefresh?.();
    }
  };

  const handleRetry = () => {
    setCurrentStep('idle');
    setStepProgress(0);
    setStepErrors([]);
    setSetupResult(null);
  };

  const getStepLabel = (step: SetupStep): string => {
    switch (step) {
      case 'fields':
        return 'Bitrix24 alanları analiz ediliyor...';
      case 'format':
        return 'Sheet formatlanıyor (renkler uygulanıyor)...';
      case 'webhook':
        return 'Webhook kuruluyor (Apps Script)...';
      case 'complete':
        return 'Kurulum tamamlandı!';
      case 'error':
        return 'Kurulum başarısız';
      default:
        return '';
    }
  };

  const isWebhookInstalled = config.webhook_registered || (setupResult?.success && setupResult.script_id);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Çift Yönlü Senkronizasyon</h3>
          <p className="text-sm text-muted-foreground">
            Google Sheets'te yaptığınız değişiklikleri otomatik olarak Bitrix24'e aktarın
          </p>
        </div>
        <Badge variant={isWebhookInstalled ? 'default' : 'secondary'}>
          {isWebhookInstalled ? (
            <>
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Aktif
            </>
          ) : (
            <>
              <XCircle className="h-3 w-3 mr-1" />
              Kurulum Gerekli
            </>
          )}
        </Badge>
      </div>

      {/* Entity Field Summary */}
      {fieldSummary && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4" />
              {ENTITY_LABELS[config.entity_type] || config.entity_type} - Alan Bilgileri
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-3 bg-secondary/50 rounded-lg">
                <div className="text-2xl font-bold">{fieldSummary.total_fields}</div>
                <div className="text-xs text-muted-foreground">Toplam Alan</div>
              </div>
              <div className="p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                <div className="text-2xl font-bold text-green-600">{fieldSummary.editable_count}</div>
                <div className="text-xs text-green-600">Düzenlenebilir</div>
              </div>
              <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                <div className="text-2xl font-bold text-red-600">{fieldSummary.readonly_count}</div>
                <div className="text-xs text-red-600">Salt Okunur</div>
              </div>
            </div>

            {/* Color Legend */}
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm font-medium mb-2">Sütun Renkleri:</p>
              <div className="flex gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: '#E8F5E9' }} />
                  <span className="text-muted-foreground">Düzenlenebilir (Yeşil)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: '#FFEBEE' }} />
                  <span className="text-muted-foreground">Salt Okunur (Kırmızı)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: '#FFF8E1' }} />
                  <span className="text-muted-foreground">Senkronizasyon Durumu (Sarı)</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Setup Progress */}
      {currentStep !== 'idle' && currentStep !== 'complete' && currentStep !== 'error' && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="font-medium">{getStepLabel(currentStep)}</span>
              </div>
              <Progress value={stepProgress} className="h-2" />
              
              {/* Step Indicators */}
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <div className={`flex items-center gap-1 ${currentStep === 'fields' || stepProgress > 0 ? 'text-primary' : ''}`}>
                  <Settings className="h-3 w-3" />
                  Alan Analizi
                </div>
                <div className={`flex items-center gap-1 ${currentStep === 'format' || stepProgress >= 33 ? 'text-primary' : ''}`}>
                  <Palette className="h-3 w-3" />
                  Formatlama
                </div>
                <div className={`flex items-center gap-1 ${currentStep === 'webhook' || stepProgress >= 66 ? 'text-primary' : ''}`}>
                  <Webhook className="h-3 w-3" />
                  Webhook
                </div>
                <div className={`flex items-center gap-1 ${stepProgress === 100 ? 'text-primary' : ''}`}>
                  <CheckCircle2 className="h-3 w-3" />
                  Tamamlandı
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Success State */}
      {currentStep === 'complete' && setupResult && (
        <Alert className="border-green-500/50 bg-green-500/10">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertTitle className="text-green-600">Kurulum Başarılı!</AlertTitle>
          <AlertDescription className="text-green-600/80">
            <div className="mt-2 space-y-1">
              <p>✓ {setupResult.editable_columns} düzenlenebilir sütun belirlendi</p>
              <p>✓ {setupResult.readonly_columns} salt okunur sütun belirlendi</p>
              {setupResult.status_column_index && (
                <p>✓ Senkronizasyon durumu sütunu eklendi (Sütun {setupResult.status_column_index})</p>
              )}
              {setupResult.script_id && (
                <p>✓ Apps Script webhook kuruldu</p>
              )}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Error State */}
      {currentStep === 'error' && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Kurulum Başarısız</AlertTitle>
          <AlertDescription>
            {stepErrors.length > 0 ? (
              <ul className="list-disc list-inside mt-2">
                {stepErrors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            ) : (
              <p>Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.</p>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {!isWebhookInstalled && currentStep === 'idle' && (
          <Button 
            onClick={handleOneClickSetup} 
            disabled={isLoading}
            size="lg"
            className="flex-1"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Tek Tık Kurulum
          </Button>
        )}

        {currentStep === 'error' && (
          <Button onClick={handleRetry} variant="outline" size="lg" className="flex-1">
            <RefreshCw className="h-4 w-4 mr-2" />
            Tekrar Dene
          </Button>
        )}

        {isWebhookInstalled && currentStep !== 'error' && (
          <>
            <Button 
              onClick={loadFieldSummary} 
              variant="outline" 
              disabled={isLoading}
              className="flex-1"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Yenile
            </Button>
            <Button 
              onClick={handleUninstall} 
              variant="destructive" 
              disabled={isLoading}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Kaldır
            </Button>
          </>
        )}
      </div>

      {/* How It Works */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Nasıl Çalışır?</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3 text-sm text-muted-foreground">
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">1</span>
              <span>Google Sheets'e veri aktarılır ve sütunlar renklendirilir (yeşil: düzenlenebilir, kırmızı: salt okunur)</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">2</span>
              <span>Apps Script otomatik olarak kurulur ve değişiklikleri izlemeye başlar</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">3</span>
              <span>Yeşil sütunlarda değişiklik yaptığınızda, değişiklik otomatik olarak Bitrix24'e gönderilir</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-medium">4</span>
              <span>"Senkronizasyon" sütununda işlem durumunu görebilirsiniz (OK, ERROR, PENDING)</span>
            </li>
          </ol>
        </CardContent>
      </Card>

      {/* All Entities Summary (Collapsible) */}
      {allFieldsSummary && Object.keys(allFieldsSummary).length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Tüm Varlıklar - Alan Özeti</CardTitle>
            <CardDescription>Bitrix24'teki tüm varlıkların alan sayıları</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(allFieldsSummary).map(([entity, counts]) => (
                <div
                  key={entity}
                  className={`p-3 rounded-lg border ${
                    entity === config.entity_type ? 'border-primary bg-primary/5' : 'border-border'
                  }`}
                >
                  <div className="font-medium text-sm">{ENTITY_LABELS[entity] || entity}</div>
                  <div className="flex gap-2 mt-1 text-xs">
                    <span className="text-green-600">{counts.editable} düzenlenebilir</span>
                    <span className="text-muted-foreground">/</span>
                    <span className="text-red-600">{counts.readonly} salt okunur</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Hata</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
