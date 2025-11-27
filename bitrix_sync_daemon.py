#!/usr/bin/env python3
"""
Bitrix24 Sync Daemon - Continuously syncs Bitrix24 data to PostgreSQL
Runs incremental sync every N minutes
"""
import time
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from src.bitrix.client import BitrixClient
from src.bitrix.ingestors import leads as leads_ing
from src.bitrix.ingestors import contacts as contacts_ing
from src.bitrix.ingestors import companies as companies_ing
from src.bitrix.ingestors import deals as deals_ing
from src.bitrix.ingestors import activities as activities_ing
from src.bitrix.ingestors import tasks as tasks_ing
from src.bitrix.ingestors import task_comments as task_comments_ing
from src.bitrix.ingestors import users as users_ing
from src.bitrix.ingestors import departments as departments_ing
from src.bitrix.ingestors import metadata as metadata_ing

# Configuration
SYNC_INTERVAL_SECONDS = 300  # 5 minutes (reduced for more frequent updates)
LOG_FILE = Path(__file__).parent / "logs" / "sync_daemon.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    running = False


def sync_all_entities(client: BitrixClient) -> dict:
    """
    Run incremental sync for all entities (including task_comments)
    Returns dict with entity counts
    """
    results = {}
    
    # Main entities with incremental sync support
    incremental_entities = {
        'leads': leads_ing,
        'contacts': contacts_ing,
        'companies': companies_ing,
        'deals': deals_ing,
        'activities': activities_ing,
        'tasks': tasks_ing,
        'task_comments': task_comments_ing
    }
    
    # Static entities (less frequent updates)
    static_entities = {
        'users': users_ing,
        'departments': departments_ing
    }
    
    # Sync incremental entities
    for entity_name, ingestor in incremental_entities.items():
        try:
            logger.info(f"[{entity_name}] Starting incremental sync...")
            count = ingestor.incremental_sync(client)
            results[entity_name] = count
            logger.info(f"[{entity_name}] ✓ Synced {count} records")
        except Exception as e:
            logger.error(f"[{entity_name}] ✗ Error during sync: {e}", exc_info=True)
            results[entity_name] = -1
    
    # Sync static entities (every 10th cycle or on first run)
    # This is handled by the main loop
    
    return results


def main():
    """Main daemon loop"""
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 80)
    logger.info("Bitrix24 Sync Daemon Starting")
    logger.info(f"Sync interval: {SYNC_INTERVAL_SECONDS} seconds ({SYNC_INTERVAL_SECONDS/60:.1f} minutes)")
    logger.info(f"Entities to sync: leads, contacts, companies, deals, activities, tasks, task_comments")
    logger.info(f"Static entities: metadata, users, departments (synced every 10 cycles)")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("=" * 80)
    
    client = BitrixClient()
    sync_count = 0
    
    try:
        while running:
            sync_count += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"Starting sync cycle #{sync_count} at {datetime.now()}")
            logger.info(f"{'='*80}")
            
            start_time = time.time()
            results = sync_all_entities(client)
            
            # Sync static entities every 10th cycle
            if sync_count % 10 == 0:
                logger.info("\n[STATIC ENTITIES] Syncing users, departments and metadata (every 10 cycles)...")
                
                # Metadata (lookup values, deal categories)
                try:
                    metadata_count = metadata_ing.full_sync(client)
                    results['metadata'] = metadata_count
                    logger.info(f"[metadata] ✓ Synced {metadata_count} records")
                except Exception as e:
                    logger.error(f"[metadata] ✗ Error: {e}", exc_info=True)
                    results['metadata'] = -1
                
                try:
                    user_count = users_ing.full_sync(client)
                    results['users'] = user_count
                    logger.info(f"[users] ✓ Synced {user_count} records")
                except Exception as e:
                    logger.error(f"[users] ✗ Error: {e}", exc_info=True)
                    results['users'] = -1
                
                try:
                    dept_count = departments_ing.full_sync(client)
                    results['departments'] = dept_count
                    logger.info(f"[departments] ✓ Synced {dept_count} records")
                except Exception as e:
                    logger.error(f"[departments] ✗ Error: {e}", exc_info=True)
                    results['departments'] = -1
            
            # Sync metadata on first run
            elif sync_count == 1:
                logger.info("\n[INITIAL SYNC] Syncing metadata (lookup values)...")
                try:
                    metadata_count = metadata_ing.full_sync(client)
                    results['metadata'] = metadata_count
                    logger.info(f"[metadata] ✓ Synced {metadata_count} records")
                except Exception as e:
                    logger.error(f"[metadata] ✗ Error: {e}", exc_info=True)
                    results['metadata'] = -1
            
            elapsed = time.time() - start_time
            
            # Summary
            total_synced = sum(v for v in results.values() if v >= 0)
            logger.info(f"\n{'='*80}")
            logger.info(f"Sync cycle #{sync_count} completed in {elapsed:.2f} seconds")
            logger.info(f"Total records synced: {total_synced}")
            logger.info(f"Results: {results}")
            logger.info(f"Next sync in {SYNC_INTERVAL_SECONDS} seconds...")
            logger.info(f"{'='*80}\n")
            
            # Sleep until next sync (check every second for shutdown signal)
            for _ in range(SYNC_INTERVAL_SECONDS):
                if not running:
                    break
                time.sleep(1)
    
    except Exception as e:
        logger.error(f"Fatal error in daemon: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Bitrix24 Sync Daemon stopped gracefully")
    sys.exit(0)


if __name__ == "__main__":
    main()
