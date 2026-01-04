# Migration Results: Sync original_data/data JSONB to Columns

**Executed:** 2024-11-28

## Summary

Successfully migrated JSONB data from `original_data` and `data` columns to normalized individual columns across all 9 Bitrix24 tables.

## Results

| Table | Rows Updated | Status |
|-------|-------------|--------|
| deals | 30,355 | ✅ Success |
| contacts | 30,962 | ✅ Success |
| companies | 58 | ✅ Success |
| tasks | 60,793 | ✅ Success |
| activities | 205,435 | ✅ Success |
| task_comments | 163,096 | ✅ Success |
| leads | 9,289 | ✅ Success |
| users | 51 | ✅ Success |
| departments | 14 | ✅ Success |

**Total rows updated: 500,053**

## Schema Changes

### New Columns Added

#### activities table
- `bitrix_id` VARCHAR(50)
- `subject` VARCHAR(500)
- `description` TEXT
- `type_id` VARCHAR(50)
- `owner_id` VARCHAR(50)
- `owner_type_id` VARCHAR(50)
- `author_id` VARCHAR(50)
- `responsible_id` VARCHAR(50)
- `provider_id` VARCHAR(100)
- `provider_type_id` VARCHAR(100)
- `created` TIMESTAMPTZ
- `last_updated` TIMESTAMPTZ

#### task_comments table
- `bitrix_id` VARCHAR(50)
- `author_id` VARCHAR(50)
- `author_name` VARCHAR(500)
- `author_email` VARCHAR(255)
- `post_message` TEXT
- `post_message_html` TEXT
- `post_date` TIMESTAMPTZ

#### leads table
- `bitrix_id` VARCHAR(50)
- `title` VARCHAR(500)
- `source_id` VARCHAR(100)
- `status_id` VARCHAR(100)
- `assigned_by_id` VARCHAR(50)
- `date_create` TIMESTAMPTZ
- `date_modify` TIMESTAMPTZ

#### users table
- `bitrix_id` VARCHAR(50)
- `name` VARCHAR(500)
- `last_name` VARCHAR(255)
- `second_name` VARCHAR(255)
- `email` VARCHAR(255)
- `active` BOOLEAN
- `user_type` VARCHAR(100)
- `work_position` VARCHAR(255)
- `work_phone` VARCHAR(100)
- `personal_mobile` VARCHAR(100)
- `time_zone` VARCHAR(100)
- `last_login` TIMESTAMPTZ
- `date_register` TIMESTAMPTZ

#### departments table
- `bitrix_id` VARCHAR(50)
- `name` VARCHAR(500)
- `sort` INTEGER

## Notes

1. **Companies EMPLOYEES field**: The EMPLOYEES field in Bitrix24 JSONB contains values like "EMPLOYEES_1" (string enum), not actual integer counts. These were migrated as NULL since the column expects integers.

2. **Table structure differences**: 
   - `deals`, `contacts`, `companies`, `tasks` use `original_data` column
   - `activities`, `task_comments`, `leads`, `users`, `departments` use `data` column

3. **API Endpoint updated**: The `/api/data/{table}` endpoint now excludes `original_data`, `source_hash`, `fetched_at`, and `data` columns from SELECT queries for cleaner data display.

## Backup

A database backup was taken before migration:
- Location: `/opt/bitsheet24/backups/bitrix_backup_20251128_175115.dump`
