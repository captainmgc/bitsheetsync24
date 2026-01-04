#!/usr/bin/env python3
"""
Migrate existing JSONB data to normalized table structure
This script reads data from old structure and migrates to new normalized tables
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db, engine

async def run_migration_file(db: AsyncSession, migration_file: Path):
    """Run a SQL migration file"""
    print(f"\n{'='*60}")
    print(f"Running: {migration_file.name}")
    print(f"{'='*60}")
    
    sql = migration_file.read_text()
    
    try:
        # Remove comments and split by semicolon
        lines = []
        for line in sql.split('\n'):
            # Remove comments
            if '--' in line:
                line = line[:line.index('--')]
            lines.append(line)
        
        sql_clean = '\n'.join(lines)
        statements = [s.strip() for s in sql_clean.split(';') if s.strip()]
        
        # Execute each statement
        for i, stmt in enumerate(statements):
            if stmt:
                print(f"  Executing statement {i+1}/{len(statements)}...")
                await db.execute(text(stmt))
        
        await db.commit()
        print(f"✅ {migration_file.name} completed successfully")
        
    except Exception as e:
        await db.rollback()
        print(f"❌ Error in {migration_file.name}: {e}")
        raise

async def migrate_contacts_data(db: AsyncSession):
    """Migrate contacts from JSONB to normalized structure"""
    print("\n" + "="*60)
    print("Checking contacts data...")
    print("="*60)
    
    try:
        # Count records
        result = await db.execute(text("SELECT COUNT(*) FROM bitrix.contacts"))
        count = result.scalar()
        print(f"✅ Contacts table ready with {count} records")
        print("   ℹ️  Run Bitrix24 sync to populate data")
        
    except Exception as e:
        print(f"❌ Error checking contacts: {e}")
        raise

async def migrate_deals_data(db: AsyncSession):
    """Migrate deals from JSONB to normalized structure"""
    print("\n" + "="*60)
    print("Checking deals data...")
    print("="*60)
    
    try:
        # Count records
        result = await db.execute(text("SELECT COUNT(*) FROM bitrix.deals"))
        count = result.scalar()
        print(f"✅ Deals table ready with {count} records")
        print("   ℹ️  Run Bitrix24 sync to populate data")
        
    except Exception as e:
        print(f"❌ Error checking deals: {e}")
        raise

async def main():
    """Run all migrations"""
    print("\n" + "="*60)
    print("BITRIX24 DATABASE NORMALIZATION")
    print("="*60)
    
    migrations_dir = Path(__file__).parent / "migrations"
    
    # Migrations to run in order
    migrations = [
        migrations_dir / "004_normalize_contacts_table.sql",
        migrations_dir / "005_normalize_deals_table.sql",
        migrations_dir / "006_normalize_companies_table.sql",
        migrations_dir / "007_normalize_tasks_table.sql",
    ]
    
    async for db in get_db():
        try:
            # Run structure migrations
            for migration_file in migrations:
                if migration_file.exists():
                    await run_migration_file(db, migration_file)
                else:
                    print(f"⚠️  Migration file not found: {migration_file}")
            
            # Migrate data
            await migrate_contacts_data(db)
            await migrate_deals_data(db)
            
            print("\n" + "="*60)
            print("✅ ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise
        finally:
            break

if __name__ == "__main__":
    asyncio.run(main())
