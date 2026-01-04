#!/usr/bin/env python3
"""
Task Comments Sync Progress Monitor
Gerçek zamanlı ilerleme takibi
"""
import psycopg2
import time
import sys
from datetime import datetime, timedelta

def clear_screen():
    print("\033[2J\033[H", end="")

def get_progress():
    conn = psycopg2.connect('postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db')
    cur = conn.cursor()
    
    # Genel durum
    cur.execute("""
        SELECT 
            COUNT(*) as total_comments,
            COUNT(DISTINCT data->>'TASK_ID') as processed_tasks,
            MIN(created_at) as first_comment_time,
            MAX(created_at) as last_comment_time
        FROM bitrix.task_comments
    """)
    total_comments, processed_tasks, first_time, last_time = cur.fetchone()
    
    # Sync hızı hesapla
    if first_time and processed_tasks > 0:
        elapsed_minutes = (datetime.now() - first_time).total_seconds() / 60
        tasks_per_minute = processed_tasks / elapsed_minutes if elapsed_minutes > 0 else 0
        
        remaining_tasks = 43431 - processed_tasks
        remaining_minutes = remaining_tasks / tasks_per_minute if tasks_per_minute > 0 else 0
        eta = datetime.now() + timedelta(minutes=remaining_minutes)
    else:
        elapsed_minutes = 0
        tasks_per_minute = 0
        remaining_minutes = 0
        eta = None
    
    # Son 1 dakikadaki aktivite
    cur.execute("""
        SELECT COUNT(*)
        FROM bitrix.task_comments
        WHERE created_at > NOW() - INTERVAL '1 minute'
    """)
    last_minute_count = cur.fetchone()[0]
    
    # Ortalama yorum sayısı
    if processed_tasks > 0:
        avg_comments = total_comments / processed_tasks
    else:
        avg_comments = 0
    
    conn.close()
    
    return {
        'total_comments': total_comments,
        'processed_tasks': processed_tasks,
        'total_tasks': 43431,
        'percent': (processed_tasks / 43431 * 100) if processed_tasks else 0,
        'elapsed_minutes': elapsed_minutes,
        'tasks_per_minute': tasks_per_minute,
        'remaining_minutes': remaining_minutes,
        'eta': eta,
        'last_minute_count': last_minute_count,
        'avg_comments': avg_comments,
        'last_update': last_time
    }

def format_time(minutes):
    """Dakikayı saat:dakika formatına çevir"""
    if minutes < 60:
        return f"{int(minutes)} dakika"
    hours = int(minutes / 60)
    mins = int(minutes % 60)
    return f"{hours} saat {mins} dakika"

def draw_progress_bar(percent, width=50):
    """ASCII progress bar çiz"""
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percent:.1f}%"

def main():
    print("🔄 Task Comments Sync Monitör Başlatıldı...")
    print("   Ctrl+C ile çıkış yapabilirsiniz\n")
    time.sleep(2)
    
    try:
        while True:
            clear_screen()
            data = get_progress()
            
            print("=" * 80)
            print("🔄 TASK COMMENTS SYNC İLERLEME RAPORU".center(80))
            print("=" * 80)
            print()
            
            # İlerleme çubuğu
            print("📊 GENEL İLERLEME")
            print("-" * 80)
            print(f"   {draw_progress_bar(data['percent'])}")
            print(f"   İşlenen Görev: {data['processed_tasks']:,} / {data['total_tasks']:,}")
            print(f"   Toplam Yorum: {data['total_comments']:,}")
            print(f"   Görev Başına Ort: {data['avg_comments']:.1f} yorum")
            print()
            
            # Hız metrikleri
            print("⚡ HIZ VE PERFORMANS")
            print("-" * 80)
            print(f"   Geçen Süre: {format_time(data['elapsed_minutes'])}")
            print(f"   Sync Hızı: {data['tasks_per_minute']:.1f} görev/dakika")
            print(f"   Son 1 Dakika: {data['last_minute_count']} yorum eklendi")
            print()
            
            # Tahmini bitiş
            print("🕐 TAHMINI BİTİŞ")
            print("-" * 80)
            if data['eta']:
                print(f"   Kalan Süre: {format_time(data['remaining_minutes'])}")
                print(f"   Bitiş Zamanı: {data['eta'].strftime('%H:%M:%S (%d/%m/%Y)')}")
            else:
                print("   Hesaplanıyor...")
            print()
            
            # Son güncelleme
            print("ℹ️  BİLGİ")
            print("-" * 80)
            if data['last_update']:
                print(f"   Son Güncelleme: {data['last_update'].strftime('%H:%M:%S')}")
            print(f"   Şu An: {datetime.now().strftime('%H:%M:%S')}")
            print("   Yenileme: Her 5 saniye")
            print()
            print("=" * 80)
            print("   [Ctrl+C] Çıkış".center(80))
            print("=" * 80)
            
            # 5 saniye bekle
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n✅ Monitör durduruldu.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
