"use client";

import React, { useState, useCallback } from "react";
import { 
  useSheetSync, 
  ConflictDetectionResult, 
  RowConflict, 
  FieldConflict,
  ResolutionStrategy,
  ConflictResolutionResult
} from "@/hooks/useSheetSync";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { 
  AlertTriangle, 
  ChevronDown, 
  ChevronRight, 
  Info, 
  CheckCircle2, 
  Loader2,
  XCircle,
  ArrowLeftRight,
  FileText,
  Database,
  History,
  Check,
  X
} from "lucide-react";

interface ConflictManagerProps {
  configId: number;
  configName?: string;
}

export function ConflictManager({ configId, configName }: ConflictManagerProps) {
  const { 
    detectConflicts, 
    resolveConflict,
    resolveRowConflicts,
    getConflictHistory,
    isLoading,
  } = useSheetSync();

  const [conflictResult, setConflictResult] = useState<ConflictDetectionResult | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [isDetecting, setIsDetecting] = useState(false);
  const [resolving, setResolving] = useState<{rowNumber: number; fieldName: string} | null>(null);
  const [resolutionResults, setResolutionResults] = useState<Map<string, ConflictResolutionResult>>(new Map());
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Çakışmaları algıla
  const handleDetectConflicts = useCallback(async () => {
    setIsDetecting(true);
    try {
      const result = await detectConflicts(configId, undefined, true);
      setConflictResult(result);
      setExpandedRows(new Set());
      setResolutionResults(new Map());
    } catch (error) {
      console.error("Çakışma algılama hatası:", error);
    } finally {
      setIsDetecting(false);
    }
  }, [configId, detectConflicts]);

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

  // Tek çakışmayı çöz
  const handleResolveField = async (
    rowNumber: number, 
    fieldName: string, 
    resolution: ResolutionStrategy
  ) => {
    setResolving({ rowNumber, fieldName });
    try {
      const result = await resolveConflict(configId, rowNumber, fieldName, resolution);
      if (result) {
        const key = `${rowNumber}-${fieldName}`;
        setResolutionResults(prev => new Map(prev).set(key, result));
        
        // Başarılıysa çakışmaları yeniden algıla
        if (result.success) {
          setTimeout(() => handleDetectConflicts(), 1000);
        }
      }
    } catch (error) {
      console.error("Çakışma çözme hatası:", error);
    } finally {
      setResolving(null);
    }
  };

  // Tüm satır çakışmalarını çöz
  const handleResolveRow = async (rowNumber: number, resolution: ResolutionStrategy) => {
    setResolving({ rowNumber, fieldName: '*' });
    try {
      const result = await resolveRowConflicts(configId, rowNumber, resolution);
      if (result?.success) {
        setTimeout(() => handleDetectConflicts(), 1000);
      }
    } catch (error) {
      console.error("Satır çakışmalarını çözme hatası:", error);
    } finally {
      setResolving(null);
    }
  };

  // Geçmişi yükle
  const handleLoadHistory = async () => {
    setLoadingHistory(true);
    try {
      const historyData = await getConflictHistory(configId, 50);
      setHistory(historyData);
      setShowHistoryDialog(true);
    } catch (error) {
      console.error("Geçmiş yükleme hatası:", error);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Çakışma tipi badge
  const getConflictTypeBadge = (conflictType: string) => {
    switch (conflictType) {
      case 'both_modified':
        return <Badge variant="destructive">Her İkisi Değişti</Badge>;
      case 'bitrix_newer':
        return <Badge variant="default" className="bg-blue-500">Bitrix Daha Yeni</Badge>;
      case 'sheet_newer':
        return <Badge variant="default" className="bg-green-500">Sheet Daha Yeni</Badge>;
      case 'deleted_in_bitrix':
        return <Badge variant="destructive">Bitrix&apos;te Silindi</Badge>;
      case 'deleted_in_sheet':
        return <Badge variant="destructive">Sheet&apos;te Silindi</Badge>;
      default:
        return <Badge variant="secondary">{conflictType}</Badge>;
    }
  };

  // Çözüm stratejisi badge
  const getSuggestedResolutionBadge = (resolution: string) => {
    switch (resolution) {
      case 'use_bitrix':
        return <Badge variant="outline" className="border-blue-500 text-blue-600">Bitrix Kullan</Badge>;
      case 'use_sheet':
        return <Badge variant="outline" className="border-green-500 text-green-600">Sheet Kullan</Badge>;
      case 'use_newer':
        return <Badge variant="outline" className="border-yellow-500 text-yellow-600">Yeniyi Kullan</Badge>;
      case 'manual':
        return <Badge variant="outline" className="border-orange-500 text-orange-600">Manuel</Badge>;
      case 'skip':
        return <Badge variant="outline" className="border-gray-500 text-gray-600">Atla</Badge>;
      default:
        return <Badge variant="secondary">{resolution}</Badge>;
    }
  };

  // Çözüm durumu göster
  const getResolutionStatus = (rowNumber: number, fieldName: string) => {
    const key = `${rowNumber}-${fieldName}`;
    const result = resolutionResults.get(key);
    
    if (!result) return null;
    
    if (result.success) {
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    } else {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <XCircle className="h-4 w-4 text-red-500" />
            </TooltipTrigger>
            <TooltipContent>
              <p>{result.error || 'Çözme hatası'}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Çakışma Yönetimi
              {configName && <span className="text-muted-foreground font-normal">- {configName}</span>}
            </CardTitle>
            <CardDescription>
              Bitrix24 ve Google Sheets arasındaki çakışmaları tespit et ve çöz
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button 
              onClick={handleLoadHistory}
              variant="outline"
              disabled={loadingHistory}
            >
              {loadingHistory ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <History className="mr-2 h-4 w-4" />
              )}
              Geçmiş
            </Button>
            <Button 
              onClick={handleDetectConflicts} 
              disabled={isDetecting || isLoading}
              variant="default"
            >
              {isDetecting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Algılanıyor...
                </>
              ) : (
                <>
                  <ArrowLeftRight className="mr-2 h-4 w-4" />
                  Çakışmaları Algıla
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!conflictResult ? (
          <div className="text-center py-8 text-muted-foreground">
            <Info className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Çakışmaları görmek için &quot;Çakışmaları Algıla&quot; butonuna tıklayın.</p>
          </div>
        ) : !conflictResult.has_conflicts ? (
          <div className="text-center py-8">
            <CheckCircle2 className="h-12 w-12 mx-auto mb-4 text-green-500" />
            <p className="text-lg font-medium">Çakışma yok!</p>
            <p className="text-muted-foreground">
              Bitrix24 ve Google Sheets verileri uyumlu.
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Son kontrol: {new Date(conflictResult.detected_at).toLocaleString('tr-TR')}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Özet Bilgiler */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Card className="p-4">
                <div className="text-2xl font-bold">{conflictResult.total_rows_checked}</div>
                <div className="text-sm text-muted-foreground">Kontrol Edilen Satır</div>
              </Card>
              <Card className="p-4 border-yellow-500">
                <div className="text-2xl font-bold text-yellow-600">{conflictResult.row_conflicts.length}</div>
                <div className="text-sm text-muted-foreground">Çakışmalı Satır</div>
              </Card>
              <Card className="p-4 border-red-500">
                <div className="text-2xl font-bold text-red-600">{conflictResult.conflicts_found}</div>
                <div className="text-sm text-muted-foreground">Toplam Çakışma</div>
              </Card>
            </div>

            {/* Çakışma Tablosu */}
            <ScrollArea className="h-[500px] rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12"></TableHead>
                    <TableHead className="w-20">Satır</TableHead>
                    <TableHead className="w-32">Entity ID</TableHead>
                    <TableHead>Çakışma Sayısı</TableHead>
                    <TableHead className="w-48">Toplu Çözüm</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {conflictResult.row_conflicts.map((row) => (
                    <React.Fragment key={row.row_number}>
                      {/* Ana Satır */}
                      <TableRow className="bg-yellow-50">
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
                        <TableCell>{row.entity_id}</TableCell>
                        <TableCell>
                          <Badge variant="destructive">
                            {row.conflict_count} çakışma
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleResolveRow(row.row_number, 'use_bitrix')}
                                    disabled={resolving?.rowNumber === row.row_number}
                                  >
                                    <Database className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Tümünde Bitrix Kullan</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleResolveRow(row.row_number, 'use_sheet')}
                                    disabled={resolving?.rowNumber === row.row_number}
                                  >
                                    <FileText className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Tümünde Sheet Kullan</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        </TableCell>
                      </TableRow>

                      {/* Genişletilmiş Alan Çakışmaları */}
                      {expandedRows.has(row.row_number) && (
                        <TableRow>
                          <TableCell colSpan={5} className="bg-muted/20 p-4">
                            <div className="space-y-2">
                              <h4 className="font-medium flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                                Çakışan Alanlar:
                              </h4>
                              <div className="grid gap-3">
                                {row.field_conflicts.map((field, idx) => (
                                  <div 
                                    key={idx}
                                    className="p-3 bg-background rounded border border-yellow-200"
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <div className="flex items-center gap-2">
                                        <span className="font-medium">{field.field_name}</span>
                                        {getConflictTypeBadge(field.conflict_type)}
                                        {getSuggestedResolutionBadge(field.suggested_resolution)}
                                      </div>
                                      <div className="flex items-center gap-2">
                                        {getResolutionStatus(row.row_number, field.field_name)}
                                        {resolving?.rowNumber === row.row_number && resolving?.fieldName === field.field_name ? (
                                          <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                          <div className="flex gap-1">
                                            <TooltipProvider>
                                              <Tooltip>
                                                <TooltipTrigger asChild>
                                                  <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => handleResolveField(row.row_number, field.field_name, 'use_bitrix')}
                                                    disabled={resolving !== null || field.resolved}
                                                    className="h-7 px-2"
                                                  >
                                                    <Database className="h-3 w-3 mr-1" />
                                                    Bitrix
                                                  </Button>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                  <p>Bitrix24 değerini kullan</p>
                                                </TooltipContent>
                                              </Tooltip>
                                            </TooltipProvider>
                                            <TooltipProvider>
                                              <Tooltip>
                                                <TooltipTrigger asChild>
                                                  <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => handleResolveField(row.row_number, field.field_name, 'use_sheet')}
                                                    disabled={resolving !== null || field.resolved}
                                                    className="h-7 px-2"
                                                  >
                                                    <FileText className="h-3 w-3 mr-1" />
                                                    Sheet
                                                  </Button>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                  <p>Google Sheets değerini kullan</p>
                                                </TooltipContent>
                                              </Tooltip>
                                            </TooltipProvider>
                                            <TooltipProvider>
                                              <Tooltip>
                                                <TooltipTrigger asChild>
                                                  <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleResolveField(row.row_number, field.field_name, 'skip')}
                                                    disabled={resolving !== null || field.resolved}
                                                    className="h-7 px-2 text-gray-500"
                                                  >
                                                    <X className="h-3 w-3" />
                                                  </Button>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                  <p>Bu çakışmayı atla</p>
                                                </TooltipContent>
                                              </Tooltip>
                                            </TooltipProvider>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                      <div className="p-2 bg-blue-50 rounded">
                                        <div className="text-xs text-blue-600 font-medium flex items-center gap-1">
                                          <Database className="h-3 w-3" />
                                          Bitrix24 Değeri
                                        </div>
                                        <div className="mt-1 truncate">
                                          {String(field.bitrix_value) || '(boş)'}
                                        </div>
                                      </div>
                                      <div className="p-2 bg-green-50 rounded">
                                        <div className="text-xs text-green-600 font-medium flex items-center gap-1">
                                          <FileText className="h-3 w-3" />
                                          Sheets Değeri
                                        </div>
                                        <div className="mt-1 truncate">
                                          {String(field.sheet_value) || '(boş)'}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>

            {/* Son Algılama Zamanı */}
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                Son algılama: {new Date(conflictResult.detected_at).toLocaleString('tr-TR')}
              </span>
              {conflictResult.error && (
                <span className="text-red-500">{conflictResult.error}</span>
              )}
            </div>
          </div>
        )}

        {/* Geçmiş Dialog */}
        <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Senkronizasyon Geçmişi</DialogTitle>
              <DialogDescription>
                Son 50 senkronizasyon kaydı
              </DialogDescription>
            </DialogHeader>
            <ScrollArea className="h-[400px]">
              {history.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  Henüz geçmiş kaydı yok
                </p>
              ) : (
                <div className="space-y-2">
                  {history.map((item, idx) => (
                    <div 
                      key={idx}
                      className={`p-3 rounded border ${
                        item.status === 'completed' ? 'bg-green-50 border-green-200' :
                        item.status === 'failed' ? 'bg-red-50 border-red-200' :
                        'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {item.status === 'completed' ? (
                            <Check className="h-4 w-4 text-green-500" />
                          ) : item.status === 'failed' ? (
                            <X className="h-4 w-4 text-red-500" />
                          ) : (
                            <Loader2 className="h-4 w-4 text-gray-500" />
                          )}
                          <span className="font-medium">
                            Satır {item.row_number || '-'} - Entity {item.entity_id || '-'}
                          </span>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {item.created_at ? new Date(item.created_at).toLocaleString('tr-TR') : '-'}
                        </span>
                      </div>
                      {item.error && (
                        <p className="text-sm text-red-600 mt-1">{item.error}</p>
                      )}
                      {item.changed_fields && Object.keys(item.changed_fields).length > 0 && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Değişen alanlar: {Object.keys(item.changed_fields).join(', ')}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
            <DialogClose asChild>
              <Button variant="outline">Kapat</Button>
            </DialogClose>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
