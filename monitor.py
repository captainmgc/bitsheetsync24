#!/usr/bin/env python3
"""
BitSheet24 - Kapsamlı Sync Monitoring Sistemi
Tüm tabloların senkronizasyon durumunu gerçek zamanlı izler
"""
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 yüklü değil! Yükleniyor...")
    subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True)
    import psycopg2
    from psycopg2.extras import RealDictCursor

# Veritabanı bağlantısı
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db")

# Renk kodları
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def check_daemon_status() -> Dict[str, Any]:
    """Systemd daemon durumunu kontrol et"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "bitrix-sync"],
            capture_output=True, text=True
        )
        is_active = result.stdout.strip() == "active"
        
        # Uptime al
        uptime = "N/A"
        if is_active:
            result = subprocess.run(
                ["systemctl", "show", "bitrix-sync", "--property=ActiveEnterTimestamp"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ts_str = result.stdout.strip().split("=")[1]
                if ts_str:
                    try:
                        start_time = datetime.strptime(ts_str, "%a %Y-%m-%d %H:%M:%S %Z")
                        delta = datetime.now() - start_time
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, seconds = divmod(remainder, 60)
                        uptime = f"{hours}s {minutes}dk {seconds}sn"
                    except:
                        uptime = ts_str
        
        return {"active": is_active, "uptime": uptime}
    except Exception as e:
        return {"active": False, "uptime": "N/A", "error": str(e)}

def get_sync_state(conn) -> list:
    """sync_state tablosundan durumu al"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    entity,
                    last_sync_at,
                    last_full_sync_at,
                    record_count,
                    status,
                    error_message,
                    updated_at
                FROM bitrix.sync_state
                ORDER BY entity
            """)
            return cur.fetchall()
    except Exception as e:
        return []

def get_table_counts(conn) -> Dict[str, int]:
    """Her tablonun gerçek kayıt sayısını al"""
    tables = ['leads', 'contacts', 'companies', 'deals', 'activities', 'tasks', 'task_comments', 'users', 'departments']
    counts = {}
    
    with conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM bitrix.{table}")
                counts[table] = cur.fetchone()[0]
            except:
                counts[table] = 0
    
    return counts

def get_recent_activity(conn, minutes: int = 5) -> Dict[str, int]:
    """Son X dakikada güncellenen kayıt sayıları"""
    tables = ['leads', 'contacts', 'companies', 'deals', 'activities', 'tasks', 'task_comments']
    recent = {}
    
    with conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(f"""
                    SELECT COUNT(*) FROM bitrix.{table}
                    WHERE fetched_at > NOW() - INTERVAL '{minutes} minutes'
                """)
                recent[table] = cur.fetchone()[0]
            except:
                recent[table] = 0
    
    return recent

def format_time_ago(dt: Optional[datetime]) -> str:
    """Zamanı 'X dakika önce' formatına çevir"""
    if not dt:
        return "Hiç"
    
    # Timezone-aware datetime'ı naive'e çevir
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    
    delta = datetime.now() - dt
    seconds = int(delta.total_seconds())
    
    if seconds < 60:
        return f"{seconds} sn önce"
    elif seconds < 3600:
        return f"{seconds // 60} dk önce"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}s {mins}dk önce"
    else:
        return f"{seconds // 86400} gün önce"

def get_status_icon(status: str) -> str:
    """Durum ikonu döndür"""
    icons = {
        "completed": f"{Colors.GREEN}✅{Colors.ENDC}",
        "running": f"{Colors.YELLOW}🔄{Colors.ENDC}",
        "failed": f"{Colors.RED}❌{Colors.ENDC}",
        "pending": f"{Colors.CYAN}⏳{Colors.ENDC}",
    }
    return icons.get(status, "❓")

def print_header():
    """Başlık yazdır"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═" * 78 + "╗")
    print("║" + "📊 BitSheet24 - Senkronizasyon Monitoring Sistemi".center(78) + "║")
    print("╚" + "═" * 78 + "╝")
    print(f"{Colors.ENDC}")

def print_daemon_status(status: Dict[str, Any]):
    """Daemon durumunu yazdır"""
    print(f"\n{Colors.BOLD}🔧 DAEMON DURUMU:{Colors.ENDC}")
    
    if status.get("active"):
        print(f"   {Colors.GREEN}● Çalışıyor{Colors.ENDC} (Uptime: {status.get('uptime', 'N/A')})")
    else:
        print(f"   {Colors.RED}● Durdu{Colors.ENDC}")
        if status.get("error"):
            print(f"   {Colors.RED}  Hata: {status['error']}{Colors.ENDC}")

def print_sync_summary(conn):
    """Senkronizasyon özeti yazdır"""
    counts = get_table_counts(conn)
    recent = get_recent_activity(conn)
    sync_states = get_sync_state(conn)
    
    # sync_state'i dict'e çevir
    state_dict = {s['entity']: s for s in sync_states}
    
    print(f"\n{Colors.BOLD}📈 TABLO DURUMU:{Colors.ENDC}")
    print(f"{'─' * 80}")
    print(f"{'Tablo':<15} {'Kayıt':<12} {'Son 5dk':<10} {'Son Sync':<18} {'Durum':<10}")
    print(f"{'─' * 80}")
    
    total_records = 0
    total_recent = 0
    
    for table, count in counts.items():
        total_records += count
        rec = recent.get(table, 0)
        total_recent += rec
        
        state = state_dict.get(table, {})
        last_sync = format_time_ago(state.get('last_sync_at'))
        status = state.get('status', 'unknown')
        status_icon = get_status_icon(status)
        
        # Renklendirme
        recent_color = Colors.GREEN if rec > 0 else Colors.ENDC
        
        print(f"{table:<15} {count:>10,}  {recent_color}{rec:>8}{Colors.ENDC}  {last_sync:<18} {status_icon}")
    
    print(f"{'─' * 80}")
    print(f"{Colors.BOLD}{'TOPLAM':<15} {total_records:>10,}  {total_recent:>8}{Colors.ENDC}")

def print_activity_chart(recent: Dict[str, int]):
    """Son aktivite çubuğu"""
    if not any(recent.values()):
        return
    
    print(f"\n{Colors.BOLD}📊 SON 5 DAKİKA AKTİVİTE:{Colors.ENDC}")
    
    max_val = max(recent.values()) if recent.values() else 1
    
    for table, count in recent.items():
        if count > 0:
            bar_len = int((count / max_val) * 40) if max_val > 0 else 0
            bar = "█" * bar_len
            print(f"   {table:<15} {Colors.GREEN}{bar}{Colors.ENDC} {count}")

def print_errors(sync_states: list):
    """Hataları göster"""
    errors = [s for s in sync_states if s.get('status') == 'failed' and s.get('error_message')]
    
    if errors:
        print(f"\n{Colors.BOLD}{Colors.RED}⚠️  HATALAR:{Colors.ENDC}")
        for err in errors:
            print(f"   {Colors.RED}[{err['entity']}] {err['error_message'][:60]}...{Colors.ENDC}")

def print_footer():
    """Alt bilgi"""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'─' * 80}")
    print(f"Güncelleme: {now} | Yenileme: 5 saniye | {Colors.CYAN}[Ctrl+C çıkış]{Colors.ENDC}")

def run_monitor(interval: int = 5):
    """Ana monitoring döngüsü"""
    print("🚀 Monitoring başlatılıyor...")
    
    try:
        while True:
            clear_screen()
            
            try:
                conn = get_db_connection()
                
                print_header()
                
                # Daemon durumu
                daemon_status = check_daemon_status()
                print_daemon_status(daemon_status)
                
                # Tablo durumları
                print_sync_summary(conn)
                
                # Aktivite grafiği
                recent = get_recent_activity(conn)
                print_activity_chart(recent)
                
                # Hatalar
                sync_states = get_sync_state(conn)
                print_errors(sync_states)
                
                print_footer()
                
                conn.close()
                
            except psycopg2.Error as e:
                print(f"\n{Colors.RED}❌ Veritabanı Hatası: {e}{Colors.ENDC}")
            except Exception as e:
                print(f"\n{Colors.RED}❌ Hata: {e}{Colors.ENDC}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Monitoring durduruldu.{Colors.ENDC}")
        sys.exit(0)

def show_once():
    """Tek seferlik durum göster"""
    try:
        conn = get_db_connection()
        
        print_header()
        
        daemon_status = check_daemon_status()
        print_daemon_status(daemon_status)
        
        print_sync_summary(conn)
        
        recent = get_recent_activity(conn)
        print_activity_chart(recent)
        
        sync_states = get_sync_state(conn)
        print_errors(sync_states)
        
        conn.close()
        
    except Exception as e:
        print(f"{Colors.RED}❌ Hata: {e}{Colors.ENDC}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BitSheet24 Sync Monitor")
    parser.add_argument("-w", "--watch", action="store_true", help="Sürekli izleme modu")
    parser.add_argument("-i", "--interval", type=int, default=5, help="Yenileme aralığı (saniye)")
    args = parser.parse_args()
    
    if args.watch:
        run_monitor(args.interval)
    else:
        show_once()
