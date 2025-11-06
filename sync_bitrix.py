#!/usr/bin/env python3
"""
CLI to sync Bitrix24 entities into PostgreSQL (bitrix schema)
"""
import argparse
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sync_bitrix.log')
    ]
)

logger = logging.getLogger(__name__)

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

ENTITIES = ["leads", "contacts", "companies", "deals", "activities", "tasks", "task_comments", "users", "departments"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("entity", nargs="?", choices=ENTITIES + ["all"], default="all")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of records to sync (for testing)")
    parser.add_argument("--incremental", action="store_true", help="Sync only changed records since last sync from sync_state table")
    args = parser.parse_args()

    client = BitrixClient()

    def run(entity):
        mode = "incremental" if args.incremental else "full"
        logger.info(f"[{entity}] Starting {mode} sync...")
        print(f"[{entity}] Starting {mode} sync...")  # Keep print for CLI output
        
        if entity == "leads":
            c = leads_ing.incremental_sync(client, limit=args.limit) if args.incremental else leads_ing.full_sync(client, limit=args.limit)
        elif entity == "contacts":
            c = contacts_ing.incremental_sync(client, limit=args.limit) if args.incremental else contacts_ing.full_sync(client, limit=args.limit)
        elif entity == "companies":
            c = companies_ing.incremental_sync(client, limit=args.limit) if args.incremental else companies_ing.full_sync(client, limit=args.limit)
        elif entity == "deals":
            c = deals_ing.incremental_sync(client, limit=args.limit) if args.incremental else deals_ing.full_sync(client, limit=args.limit)
        elif entity == "activities":
            c = activities_ing.incremental_sync(client, limit=args.limit) if args.incremental else activities_ing.full_sync(client, limit=args.limit)
        elif entity == "tasks":
            c = tasks_ing.incremental_sync(client, limit=args.limit) if args.incremental else tasks_ing.full_sync(client, limit=args.limit)
        elif entity == "task_comments":
            c = task_comments_ing.incremental_sync(client, limit=args.limit) if args.incremental else task_comments_ing.full_sync(client, limit=args.limit)
        elif entity == "users":
            c = users_ing.full_sync(client, limit=args.limit)
        elif entity == "departments":
            c = departments_ing.full_sync(client, limit=args.limit)
        else:
            c = 0
        logger.info(f"[{entity}] Synced {c} records (mode={mode}, total_hint={getattr(client, 'last_total', None)})")
        print(f"[{entity}] Synced {c} records (mode={mode}, total_hint={getattr(client, 'last_total', None)})")

    if args.entity == "all":
        # Only sync incremental-capable entities if --incremental
        entities_to_sync = ["leads", "contacts", "companies", "deals", "activities", "tasks"] if args.incremental else ENTITIES
        for e in entities_to_sync:
            run(e)
    else:
        run(args.entity)

if __name__ == "__main__":
    main()
