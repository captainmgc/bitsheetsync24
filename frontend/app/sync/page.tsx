"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  RefreshCw, 
  Play, 
  Pause, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  Database,
  Activity,
  Users,
  Building2,
  FileText,
  MessageSquare,
  UserCheck,
  Briefcase
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4001";

interface EntityStats {
  last_sync: string | null;
  total_count: number;
}

interface SyncHistory {
  entity: string;
  synced_at: string | null;
  records: number;
  status: string;
  error: string | null;
}

interface SyncStatus {
  is_running: boolean;
  last_sync: string | null;
  auto_sync: {
    enabled: boolean;
    interval: number;
    interval_label: string;
  };
  entities: Record<string, EntityStats>;
  history: SyncHistory[];
}

interface SyncStats {
  entities: Record<string, number>;
  total_records: number;
  synced_today: number;
  is_running: boolean;
  auto_sync_enabled: boolean;
}

const entityIcons: Record<string, React.ReactNode> = {
  deals: <Briefcase className="h-4 w-4" />,
  contacts: <Users className="h-4 w-4" />,
  companies: <Building2 className="h-4 w-4" />,
  tasks: <FileText className="h-4 w-4" />,
  activities: <Activity className="h-4 w-4" />,
  task_comments: <MessageSquare className="h-4 w-4" />,
  leads: <UserCheck className="h-4 w-4" />,
  users: <Users className="h-4 w-4" />,
};

const entityLabels: Record<string, string> = {
  deals: "Anlaşmalar",
  contacts: "Kişiler",
  companies: "Şirketler",
  tasks: "Görevler",
  activities: "Aktiviteler",
  task_comments: "Yorum",
  leads: "Potansiyel",
  users: "Kullanıcılar",
};

const intervalOptions = [
  { value: 300, label: "5 dakika" },
  { value: 900, label: "15 dakika" },
  { value: 3600, label: "1 saat" },
  { value: 86400, label: "Günlük" },
];

export default function SyncPage() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [stats, setStats] = useState<SyncStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedInterval, setSelectedInterval] = useState(300);
  const [autoSyncEnabled, setAutoSyncEnabled] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/sync/status`),
        fetch(`${API_URL}/api/sync/stats`)
      ]);
      
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
        setAutoSyncEnabled(statusData.auto_sync?.enabled || false);
        setSelectedInterval(statusData.auto_sync?.interval || 300);
      }
      
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
        setSyncing(statsData.is_running);
      }
    } catch (error) {
      console.error("Failed to fetch sync status:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleSyncNow = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API_URL}/api/sync/now`, { method: "POST" });
      if (res.ok) {
        // Start polling for status
        setTimeout(fetchStatus, 1000);
      }
    } catch (error) {
      console.error("Failed to start sync:", error);
    }
  };

  const handleAutoSyncToggle = async () => {
    const newEnabled = !autoSyncEnabled;
    try {
      const res = await fetch(`${API_URL}/api/sync/auto`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: newEnabled,
          interval: selectedInterval
        })
      });
      
      if (res.ok) {
        setAutoSyncEnabled(newEnabled);
        fetchStatus();
      }
    } catch (error) {
      console.error("Failed to toggle auto sync:", error);
    }
  };

  const handleIntervalChange = async (interval: number) => {
    setSelectedInterval(interval);
    if (autoSyncEnabled) {
      try {
        await fetch(`${API_URL}/api/sync/auto`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: true,
            interval: interval
          })
        });
        fetchStatus();
      } catch (error) {
        console.error("Failed to update interval:", error);
      }
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Hiç";
    const date = new Date(dateStr);
    return date.toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("tr-TR").format(num);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Senkronizasyon</h1>
          <p className="text-muted-foreground">
            Bitrix24 verilerini anlık olarak senkronize edin
          </p>
        </div>
        <Button 
          size="lg" 
          onClick={handleSyncNow}
          disabled={syncing}
          className="gap-2"
        >
          {syncing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Senkronize Ediliyor...
            </>
          ) : (
            <>
              <RefreshCw className="h-5 w-5" />
              Şimdi Senkronize Et
            </>
          )}
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Toplam Kayıt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(stats?.total_records || 0)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Bugün Senkronize
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {formatNumber(stats?.synced_today || 0)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Son Senkronizasyon
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-medium">
              {formatDate(status?.last_sync || null)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Durum
            </CardTitle>
          </CardHeader>
          <CardContent>
            {syncing ? (
              <Badge variant="default" className="gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Çalışıyor
              </Badge>
            ) : autoSyncEnabled ? (
              <Badge variant="secondary" className="gap-1 bg-green-100 text-green-700">
                <CheckCircle2 className="h-3 w-3" />
                Otomatik Aktif
              </Badge>
            ) : (
              <Badge variant="outline" className="gap-1">
                <Clock className="h-3 w-3" />
                Beklemede
              </Badge>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Auto Sync Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Otomatik Senkronizasyon
          </CardTitle>
          <CardDescription>
            Belirli aralıklarla otomatik veri güncellemesi
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <Button
              variant={autoSyncEnabled ? "default" : "outline"}
              onClick={handleAutoSyncToggle}
              className="gap-2"
            >
              {autoSyncEnabled ? (
                <>
                  <Pause className="h-4 w-4" />
                  Otomatik Senkronizasyonu Durdur
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Otomatik Senkronizasyonu Başlat
                </>
              )}
            </Button>

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Her:</span>
              <div className="flex gap-2">
                {intervalOptions.map((opt) => (
                  <Button
                    key={opt.value}
                    variant={selectedInterval === opt.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleIntervalChange(opt.value)}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Entity Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Veri Kaynakları
          </CardTitle>
          <CardDescription>
            Her tablonun senkronizasyon durumu
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {stats?.entities && Object.entries(stats.entities).map(([entity, count]) => (
              <div 
                key={entity}
                className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
              >
                <div className="p-2 rounded-md bg-primary/10 text-primary">
                  {entityIcons[entity] || <Database className="h-4 w-4" />}
                </div>
                <div className="flex-1">
                  <div className="font-medium">
                    {entityLabels[entity] || entity}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatNumber(count)} kayıt
                  </div>
                </div>
                {status?.entities[entity]?.last_sync && (
                  <div className="text-xs text-muted-foreground">
                    {formatDate(status.entities[entity].last_sync)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Sync History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Senkronizasyon Geçmişi
          </CardTitle>
          <CardDescription>
            Son senkronizasyon işlemleri
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status?.history && status.history.length > 0 ? (
            <div className="space-y-2">
              {status.history.slice(0, 10).map((item, index) => (
                <div 
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    {item.status === "success" ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <div>
                      <div className="font-medium">
                        {entityLabels[item.entity] || item.entity}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {item.records} kayıt senkronize edildi
                      </div>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatDate(item.synced_at)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Henüz senkronizasyon geçmişi yok
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
