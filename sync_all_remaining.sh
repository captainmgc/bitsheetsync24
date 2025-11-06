#!/bin/bash
# Full sync of all remaining data

cd /home/captain/bitsheet24
source venv/bin/activate

echo "🔄 Starting full sync of all tables..."

# Sync contacts (29,500 total)
echo "📞 Syncing contacts..."
python sync_bitrix.py contacts 2>&1 | tee /tmp/sync_contacts_full.log &
CONTACTS_PID=$!

# Wait a bit to avoid connection overload
sleep 5

# Sync deals (28,866 total)
echo "💼 Syncing deals..."
python sync_bitrix.py deals 2>&1 | tee /tmp/sync_deals_full.log &
DEALS_PID=$!

# Wait a bit
sleep 5

# Sync tasks if needed
echo "✅ Syncing tasks..."
python sync_bitrix.py tasks 2>&1 | tee /tmp/sync_tasks_full.log &
TASKS_PID=$!

echo "⏳ Syncs running in background..."
echo "   - Contacts PID: $CONTACTS_PID"
echo "   - Deals PID: $DEALS_PID"
echo "   - Tasks PID: $TASKS_PID"
echo ""
echo "Check progress with:"
echo "  tail -f /tmp/sync_contacts_full.log"
echo "  tail -f /tmp/sync_deals_full.log"
echo "  tail -f /tmp/sync_tasks_full.log"
