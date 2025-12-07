"use client";

import React, { useState, useCallback } from "react";
import { 
  useSheetSync, 
  ChangeDetectionResult, 
  RowChange, 
  RowDetails,
  SyncRowResult,
  BatchSyncResult 
} from "@/hooks/useSheetSync";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Checkbox } from "@/components/ui/checkbox";
import { 
  RefreshCw, 
  ChevronDown, 
  ChevronRight, 
  Info, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight,
  Send,
  CheckCheck,
  Loader2,
  XCircle,
  RotateCcw
} from "lucide-react";

interface ChangeDetectionPreviewProps {
  configId: number;
  configName?: string;
}

type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

interface RowSyncStatus {
  [rowNumber: number]: {
    status: SyncStatus;
    message?: string;
  };
}

export function ChangeDetectionPreview({ configId, configName }: ChangeDetectionPreviewProps) {
  const { 
    detectChanges, 
    getRowDetails, 
    saveSnapshot, 
    isLoading,
    syncSingleRow,
    syncSelectedRows,
    syncAllChanges,
    retryFailedReverseSyncs
  } = useSheetSync();

  const [changeResult, setChangeResult] = useState<ChangeDetectionResult | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [selectedRowDetails, setSelectedRowDetails] = useState<RowDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  // Sync states
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [rowSyncStatus, setRowSyncStatus] = useState<RowSyncStatus>({});
  const [batchSyncing, setBatchSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<BatchSyncResult | null>(null);
  const [showSyncResultDialog, setShowSyncResultDialog] = useState(false);

  // Editable row hesapla
  const getEditableRows = useCallback((result: ChangeDetectionResult | null): RowChange[] => {
    if (!result) return [];
    return result.row_changes.filter(row => 
      row.cell_changes.some(cell => cell.is_editable)
    );
  }, []);

  // Değişiklikleri algıla
  const handleDetectChanges = useCallback(async () => {
    setIsDetecting(true);
    try {
      const result = await detectChanges(configId);
      setChangeResult(result);
      setExpandedRows(new Set());
      setSelectedRows(new Set());
      setRowSyncStatus({});
    } catch (error) {
      console.error("Değişiklik algılama hatası:", error);
    } finally {
      setIsDetecting(false);
    }
  }, [configId, detectChanges]);

  // Snapshot kaydet
  const handleSaveSnapshot = async () => {
    setIsSaving(true);
    try {
      await saveSnapshot(configId);
      // Snapshot kaydedildikten sonra değişiklikleri tekrar kontrol et
      await handleDetectChanges();
    } catch (error) {
      console.error("Snapshot kaydetme hatası:", error);
    } finally {
      setIsSaving(false);
    }
  };

  // Satır detaylarını getir
  const handleRowDetails = async (rowNumber: number) => {
    setDetailsLoading(true);
    try {
      const details = await getRowDetails(configId, rowNumber);
      setSelectedRowDetails(details);
    } catch (error) {
      console.error("Satır detayları hatası:", error);
    } finally {
      setDetailsLoading(false);
    }
  };

  // Satır genişletme
  const toggleRowExpansion = (rowNumber: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(rowNumber)) {
      newExpanded.delete(rowNumber);
    } else {
      newExpanded.add(rowNumber);
    }
    setExpandedRows(newExpanded);
  };

  // Satır seçimi
  const toggleRowSelection = (rowNumber: number) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(rowNumber)) {
      newSelected.delete(rowNumber);
    } else {
      newSelected.add(rowNumber);
    }
    setSelectedRows(newSelected);
  };

  // Tüm satırları seç/kaldır
  const toggleAllRows = () => {
    const editableRows = getEditableRows(changeResult);
    if (selectedRows.size === editableRows.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(editableRows.map(row => row.row_number)));
    }
  };

  // Satırın düzenlenebilir olup olmadığını kontrol et
  const isRowEditable = (row: RowChange): boolean => {
    return row.cell_changes.some(cell => cell.is_editable);
  };

  // Tek satır senkronizasyonu
  const handleSyncRow = async (rowNumber: number) => {
    setRowSyncStatus(prev => ({
      ...prev,
      [rowNumber]: { status: 'syncing' }
    }));

    try {
      const result = await syncSingleRow(configId, rowNumber);
      
      if (result) {
        setRowSyncStatus(prev => ({
          ...prev,
          [rowNumber]: { 
            status: result.success ? 'success' : 'error',
            message: result.error || undefined
          }
        }));

        // Başarılıysa, değişiklikleri yeniden algıla
        if (result.success) {
          setTimeout(() => handleDetectChanges(), 1500);
        }
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Senkronizasyon hatası';
      setRowSyncStatus(prev => ({
        ...prev,
        [rowNumber]: { 
          status: 'error',
          message: errorMessage
        }
      }));
    }
  };

  // Seçili satırları senkronize et
  const handleSyncSelected = async () => {
    if (selectedRows.size === 0) return;

    setBatchSyncing(true);
    const rowNumbers = Array.from(selectedRows);

    // Her satır için syncing durumu ayarla
    const newStatus: RowSyncStatus = {};
    rowNumbers.forEach(row => {
      newStatus[row] = { status: 'syncing' };
    });
    setRowSyncStatus(prev => ({ ...prev, ...newStatus }));

    try {
      const result = await syncSelectedRows(configId, rowNumbers);
      
      if (result) {
        // Sonuçları güncelle
        const updatedStatus: RowSyncStatus = {};
        result.results.forEach((rowResult: SyncRowResult) => {
          updatedStatus[rowResult.row_number] = {
            status: rowResult.success ? 'success' : 'error',
            message: rowResult.error || undefined
          };
        });
        setRowSyncStatus(prev => ({ ...prev, ...updatedStatus }));

        setLastSyncResult(result);
        setShowSyncResultDialog(true);

        // Başarılı satırları seçimden kaldır
        const successfulRows = result.results
          .filter((r: SyncRowResult) => r.success)
          .map((r: SyncRowResult) => r.row_number);
        setSelectedRows(prev => {
          const newSet = new Set(prev);
          successfulRows.forEach((row: number) => newSet.delete(row));
          return newSet;
        });

        // Başarılı varsa değişiklikleri yeniden algıla
        if (result.successful > 0) {
          setTimeout(() => handleDetectChanges(), 2000);
        }
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Senkronizasyon hatası';
      // Tüm satırlar için hata durumu
      const errorStatus: RowSyncStatus = {};
      rowNumbers.forEach(row => {
        errorStatus[row] = { status: 'error', message: errorMessage };
      });
      setRowSyncStatus(prev => ({ ...prev, ...errorStatus }));
    } finally {
      setBatchSyncing(false);
    }
  };

  // Tüm değişiklikleri senkronize et
  const handleSyncAll = async () => {
    const editableRows = getEditableRows(changeResult);
    if (editableRows.length === 0) return;

    setBatchSyncing(true);
    const editableRowNumbers = editableRows.map(row => row.row_number);

    // Her satır için syncing durumu ayarla
    const newStatus: RowSyncStatus = {};
    editableRowNumbers.forEach(row => {
      newStatus[row] = { status: 'syncing' };
    });
    setRowSyncStatus(newStatus);

    try {
      const result = await syncAllChanges(configId);
      
      if (result) {
        // Sonuçları güncelle
        const updatedStatus: RowSyncStatus = {};
        result.results.forEach((rowResult: SyncRowResult) => {
          updatedStatus[rowResult.row_number] = {
            status: rowResult.success ? 'success' : 'error',
            message: rowResult.error || undefined
          };
        });
        setRowSyncStatus(updatedStatus);

        setLastSyncResult(result);
        setShowSyncResultDialog(true);

        // Başarılı varsa değişiklikleri yeniden algıla
        if (result.successful > 0) {
          setTimeout(() => handleDetectChanges(), 2000);
        }
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Senkronizasyon hatası';
      // Tüm satırlar için hata durumu
      const errorStatus: RowSyncStatus = {};
      editableRowNumbers.forEach(row => {
        errorStatus[row] = { status: 'error', message: errorMessage };
      });
      setRowSyncStatus(errorStatus);
    } finally {
      setBatchSyncing(false);
    }
  };

  // Başarısız senkronizasyonları yeniden dene
  const handleRetryFailed = async () => {
    const failedRows = Object.entries(rowSyncStatus)
      .filter(([, status]) => status.status === 'error')
      .map(([row]) => parseInt(row));

    if (failedRows.length === 0) return;

    setBatchSyncing(true);
    
    // Yeniden deneme durumuna al
    const retryStatus: RowSyncStatus = {};
    failedRows.forEach(row => {
      retryStatus[row] = { status: 'syncing' };
    });
    setRowSyncStatus(prev => ({ ...prev, ...retryStatus }));

    try {
      const result = await retryFailedReverseSyncs(configId);
      
      if (result) {
        const updatedStatus: RowSyncStatus = {};
        result.results.forEach((rowResult: SyncRowResult) => {
          updatedStatus[rowResult.row_number] = {
            status: rowResult.success ? 'success' : 'error',
            message: rowResult.error || undefined
          };
        });
        setRowSyncStatus(prev => ({ ...prev, ...updatedStatus }));

        setLastSyncResult(result);
        setShowSyncResultDialog(true);
      }
    } catch (error) {
      console.error("Yeniden deneme hatası:", error);
    } finally {
      setBatchSyncing(false);
    }
  };

  // Değişiklik tipi badge rengi
  const getChangeTypeBadge = (changeType: string) => {
    switch (changeType) {
      case 'modified':
        return <Badge variant="default" className="bg-blue-500">Değiştirildi</Badge>;
      case 'added':
        return <Badge variant="default" className="bg-green-500">Yeni</Badge>;
      case 'deleted':
        return <Badge variant="default" className="bg-red-500">Silindi</Badge>;
      default:
        return <Badge variant="secondary">{changeType}</Badge>;
    }
  };

  // Sync status ikonu
  const getSyncStatusIcon = (rowNumber: number) => {
    const status = rowSyncStatus[rowNumber];
    if (!status) return null;

    switch (status.status) {
      case 'syncing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'error':
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <XCircle className="h-4 w-4 text-red-500" />
              </TooltipTrigger>
              <TooltipContent>
                <p>{status.message || 'Senkronizasyon hatası'}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      default:
        return null;
    }
  };

  // Düzenlenebilir satır ve değişiklik sayıları
  const editableRows = getEditableRows(changeResult);
  const editableRowCount = editableRows.length;
  const editableChangesCount = changeResult?.row_changes.reduce((acc, row) => {
    return acc + row.cell_changes.filter(c => c.is_editable).length;
  }, 0) || 0;
  const readonlyChangesCount = (changeResult?.total_changed_cells || 0) - editableChangesCount;
  const failedSyncCount = Object.values(rowSyncStatus).filter(s => s.status === 'error').length;

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Değişiklik Algılama
              {configName && <span className="text-muted-foreground font-normal">- {configName}</span>}
            </CardTitle>
            <CardDescription>
              Google Sheets&apos;teki değişiklikleri algıla ve Bitrix24&apos;e gönder
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              onClick={handleDetectChanges} 
              disabled={isDetecting || isLoading}
              variant="outline"
            >
              {isDetecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Algılanıyor...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Değişiklikleri Algıla
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!changeResult ? (
          <div className="text-center py-8 text-muted-foreground">
            <Info className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Değişiklikleri görmek için &quot;Değişiklikleri Algıla&quot; butonuna tıklayın.</p>
          </div>
        ) : !changeResult.has_changes ? (
          <div className="text-center py-8">
            <CheckCircle2 className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p className="text-lg font-medium">Değişiklik yok!</p>
            <p className="text-muted-foreground">
              Google Sheets verileri son snapshot ile eşleşiyor.
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Son kontrol: {new Date(changeResult.detected_at).toLocaleString('tr-TR')}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Özet Bilgiler */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Card className="p-4">
                <div className="text-2xl font-bold">{changeResult.total_changed_cells}</div>
                <div className="text-sm text-muted-foreground">Toplam Değişiklik</div>
              </Card>
              <Card className="p-4">
                <div className="text-2xl font-bold text-green-600">{editableChangesCount}</div>
                <div className="text-sm text-muted-foreground">Düzenlenebilir</div>
              </Card>
              <Card className="p-4">
                <div className="text-2xl font-bold text-gray-500">{readonlyChangesCount}</div>
                <div className="text-sm text-muted-foreground">Salt Okunur</div>
              </Card>
              <Card className="p-4">
                <div className="text-2xl font-bold text-blue-600">{selectedRows.size}</div>
                <div className="text-sm text-muted-foreground">Seçili</div>
              </Card>
              <Card className="p-4">
                <div className="text-2xl font-bold text-red-600">{failedSyncCount}</div>
                <div className="text-sm text-muted-foreground">Başarısız</div>
              </Card>
            </div>

            {/* Senkronizasyon Butonları */}
            <div className="flex flex-wrap gap-2 p-4 bg-muted/50 rounded-lg">
              <Button
                onClick={handleSyncSelected}
                disabled={selectedRows.size === 0 || batchSyncing}
                variant="default"
              >
                {batchSyncing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Send className="mr-2 h-4 w-4" />
                )}
                Seçilenleri Gönder ({selectedRows.size})
              </Button>
              <Button
                onClick={handleSyncAll}
                disabled={editableRowCount === 0 || batchSyncing}
                variant="secondary"
              >
                {batchSyncing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCheck className="mr-2 h-4 w-4" />
                )}
                Tümünü Gönder ({editableRowCount})
              </Button>
              {failedSyncCount > 0 && (
                <Button
                  onClick={handleRetryFailed}
                  disabled={batchSyncing}
                  variant="outline"
                  className="border-red-500 text-red-600 hover:bg-red-50"
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Başarısızları Yeniden Dene ({failedSyncCount})
                </Button>
              )}
              <div className="flex-1" />
              <Button
                onClick={handleSaveSnapshot}
                disabled={isSaving}
                variant="outline"
              >
                {isSaving ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                )}
                Snapshot Kaydet
              </Button>
            </div>

            {/* Değişiklik Tablosu */}
            <ScrollArea className="h-[500px] rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={editableRowCount > 0 && selectedRows.size === editableRowCount}
                        onCheckedChange={toggleAllRows}
                        disabled={editableRowCount === 0}
                      />
                    </TableHead>
                    <TableHead className="w-12"></TableHead>
                    <TableHead className="w-20">Satır</TableHead>
                    <TableHead className="w-32">Durum</TableHead>
                    <TableHead>Değişiklik Sayısı</TableHead>
                    <TableHead className="w-32">Tip</TableHead>
                    <TableHead className="w-24">Sync</TableHead>
                    <TableHead className="w-32">İşlemler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {changeResult.row_changes.map((row) => {
                    const rowEditable = isRowEditable(row);
                    const editableCellCount = row.cell_changes.filter(c => c.is_editable).length;
                    
                    return (
                      <React.Fragment key={row.row_number}>
                        {/* Ana Satır */}
                        <TableRow 
                          className={`
                            ${!rowEditable ? 'bg-muted/30' : ''}
                            ${selectedRows.has(row.row_number) ? 'bg-blue-50' : ''}
                            ${rowSyncStatus[row.row_number]?.status === 'success' ? 'bg-green-50' : ''}
                            ${rowSyncStatus[row.row_number]?.status === 'error' ? 'bg-red-50' : ''}
                          `}
                        >
                          <TableCell>
                            <Checkbox
                              checked={selectedRows.has(row.row_number)}
                              onCheckedChange={() => toggleRowSelection(row.row_number)}
                              disabled={!rowEditable || rowSyncStatus[row.row_number]?.status === 'syncing'}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleRowExpansion(row.row_number)}
                            >
                              {expandedRows.has(row.row_number) ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </Button>
                          </TableCell>
                          <TableCell className="font-medium">{row.row_number}</TableCell>
                          <TableCell>
                            {rowEditable ? (
                              <Badge variant="outline" className="border-green-500 text-green-600">
                                Düzenlenebilir ({editableCellCount})
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="border-gray-400 text-gray-500">
                                Salt Okunur
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>{row.cell_changes.length} hücre</TableCell>
                          <TableCell>{getChangeTypeBadge(row.change_type)}</TableCell>
                          <TableCell>{getSyncStatusIcon(row.row_number)}</TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              {rowEditable && rowSyncStatus[row.row_number]?.status !== 'syncing' && (
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleSyncRow(row.row_number)}
                                        disabled={batchSyncing}
                                      >
                                        <Send className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p>Bitrix24&apos;e Gönder</p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              )}
                              <Dialog>
                                <DialogTrigger asChild>
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => handleRowDetails(row.row_number)}
                                  >
                                    <Info className="h-4 w-4" />
                                  </Button>
                                </DialogTrigger>
                                <DialogContent className="max-w-2xl">
                                  <DialogHeader>
                                    <DialogTitle>Satır {row.row_number} Detayları</DialogTitle>
                                    <DialogDescription>
                                      Bu satırdaki tüm alanların karşılaştırması
                                    </DialogDescription>
                                  </DialogHeader>
                                  {detailsLoading ? (
                                    <div className="flex items-center justify-center py-8">
                                      <Loader2 className="h-8 w-8 animate-spin" />
                                    </div>
                                  ) : selectedRowDetails ? (
                                    <ScrollArea className="h-[400px]">
                                      <Table>
                                        <TableHeader>
                                          <TableRow>
                                            <TableHead>Alan</TableHead>
                                            <TableHead>Mevcut Değer</TableHead>
                                            <TableHead></TableHead>
                                            <TableHead>Yeni Değer</TableHead>
                                          </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                          {selectedRowDetails.comparison.map((field, idx) => (
                                            <TableRow 
                                              key={idx}
                                              className={field.is_changed ? 'bg-yellow-50' : ''}
                                            >
                                              <TableCell className="font-medium">
                                                {field.column_name}
                                                {field.is_changed && (
                                                  <Badge variant="secondary" className="ml-2">Değişti</Badge>
                                                )}
                                              </TableCell>
                                              <TableCell className="max-w-[200px] truncate">
                                                {field.stored_value || '-'}
                                              </TableCell>
                                              <TableCell>
                                                {field.is_changed && <ArrowRight className="h-4 w-4" />}
                                              </TableCell>
                                              <TableCell className="max-w-[200px] truncate">
                                                {field.current_value || '-'}
                                              </TableCell>
                                            </TableRow>
                                          ))}
                                        </TableBody>
                                      </Table>
                                    </ScrollArea>
                                  ) : (
                                    <p className="text-center text-muted-foreground py-4">
                                      Detaylar yüklenemedi
                                    </p>
                                  )}
                                  <DialogClose asChild>
                                    <Button variant="outline">Kapat</Button>
                                  </DialogClose>
                                </DialogContent>
                              </Dialog>
                            </div>
                          </TableCell>
                        </TableRow>

                        {/* Genişletilmiş Satır Detayları */}
                        {expandedRows.has(row.row_number) && (
                          <TableRow>
                            <TableCell colSpan={8} className="bg-muted/20 p-4">
                              <div className="space-y-2">
                                <h4 className="font-medium">Değişen Hücreler:</h4>
                                <div className="grid gap-2">
                                  {row.cell_changes.map((cell, idx) => (
                                    <div 
                                      key={idx}
                                      className="flex items-center gap-4 p-2 bg-background rounded border"
                                    >
                                      <div className="font-medium min-w-[120px]">
                                        {cell.column_name}
                                        {cell.is_editable && (
                                          <Badge variant="outline" className="ml-2 text-xs border-green-500 text-green-600">
                                            Düzenlenebilir
                                          </Badge>
                                        )}
                                      </div>
                                      <div className="flex items-center gap-2 flex-1">
                                        <span className="text-muted-foreground line-through">
                                          {cell.old_value || '(boş)'}
                                        </span>
                                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                                        <span className="font-medium text-green-600">
                                          {cell.new_value || '(boş)'}
                                        </span>
                                      </div>
                                      <Badge variant="outline" className="text-xs">
                                        Kolon {cell.column}
                                      </Badge>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            </ScrollArea>

            {/* Son Algılama Zamanı */}
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Son algılama: {new Date(changeResult.detected_at).toLocaleString('tr-TR')}
              </span>
              <span className="flex items-center gap-1 text-blue-600">
                <Info className="h-4 w-4" />
                {changeResult.total_rows_scanned} satır tarandı
              </span>
            </div>
          </div>
        )}

        {/* Senkronizasyon Sonuç Dialog */}
        <Dialog open={showSyncResultDialog} onOpenChange={setShowSyncResultDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {lastSyncResult && lastSyncResult.failed === 0 ? (
                  <span className="flex items-center gap-2 text-green-600">
                    <CheckCircle2 className="h-5 w-5" />
                    Senkronizasyon Tamamlandı
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-yellow-600">
                    <AlertCircle className="h-5 w-5" />
                    Senkronizasyon Sonucu
                  </span>
                )}
              </DialogTitle>
              <DialogDescription>
                {lastSyncResult?.message || 'İşlem tamamlandı'}
              </DialogDescription>
            </DialogHeader>
            {lastSyncResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {lastSyncResult.successful}
                    </div>
                    <div className="text-sm text-green-700">Başarılı</div>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">
                      {lastSyncResult.failed}
                    </div>
                    <div className="text-sm text-red-700">Başarısız</div>
                  </div>
                </div>
                {lastSyncResult.results && lastSyncResult.results.length > 0 && (
                  <ScrollArea className="h-[200px]">
                    <div className="space-y-2">
                      {lastSyncResult.results.map((result: SyncRowResult, idx: number) => (
                        <div 
                          key={idx}
                          className={`p-2 rounded flex items-center gap-2 ${
                            result.success ? 'bg-green-50' : 'bg-red-50'
                          }`}
                        >
                          {result.success ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                          <span className="font-medium">Satır {result.row_number}</span>
                          <span className="text-sm text-muted-foreground">
                            {result.success 
                              ? `${result.fields_synced.length} alan güncellendi` 
                              : result.error}
                          </span>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </div>
            )}
            <DialogClose asChild>
              <Button>Kapat</Button>
            </DialogClose>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}

export default ChangeDetectionPreview;
