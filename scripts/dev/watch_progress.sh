#!/bin/bash
while true; do
    clear
    python << 'EOF'
import psycopg2
from datetime import datetime, timedelta

conn = psycopg2.connect("postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db")
cur = conn.cursor()

cur.execute("""
    SELECT 
        COUNT(*),
        COUNT(DISTINCT data->>'TASK_ID'),
        MIN(created_at)
    FROM bitrix.task_comments
""")
total, tasks, first_time = cur.fetchone()

elapsed = (datetime.now() - first_time).total_seconds() / 60 if first_time else 0
speed = tasks / elapsed if elapsed > 0 else 0
remaining = 43431 - tasks
eta_mins = remaining / speed if speed > 0 else 0

percent = (tasks / 43431 * 100)
filled = int(50 * percent / 100)
bar = "█" * filled + "░" * (50 - filled)

print("=" * 70)
print("🔄 TASK COMMENTS SYNC İLERLEMESİ".center(70))
print("=" * 70)
print()
print(f"[{bar}] {percent:.1f}%")
print()
print(f"İşlenen Görev: {tasks:,} / 43,431")
print(f"Toplam Yorum: {total:,}")
print(f"Ort: {total/tasks:.1f} yorum/görev" if tasks > 0 else "Ort: 0")
print()
print(f"Hız: {speed:.1f} görev/dk")
print(f"Kalan: ~{int(eta_mins/60)}s {int(eta_mins%60)}dk")
print()
print(f"Güncelleme: {datetime.now().strftime('%H:%M:%S')}")
print("=" * 70)
print("\n[Ctrl+C ile çık]")

conn.close()
EOF
    sleep 5
done
