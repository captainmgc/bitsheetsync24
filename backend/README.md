# Bitrix24 Google Sheets Export - Backend

Modern FastAPI backend for exporting Bitrix24 data to Google Sheets with automatic relationship detection.

## Features

✅ **Async/Await** - Full async support with SQLAlchemy 2.0  
✅ **Auto Relationships** - Detects foreign keys automatically  
✅ **Turkish Export** - Turkish column names + DD/MM/YYYY dates  
✅ **Smart Merge** - Updates existing, appends new records  
✅ **Batch Processing** - Handles large datasets with retry logic  
✅ **Webhook Integration** - Auto-export on Bitrix24 events  
✅ **Progress Tracking** - Real-time export progress  
✅ **Structured Logging** - JSON logs with structlog  

## Tech Stack

- **FastAPI 0.115+** - Modern Python web framework
- **SQLAlchemy 2.0+** - Async ORM
- **Pydantic v2** - Data validation
- **asyncpg** - Async PostgreSQL driver
- **httpx** - Async HTTP client
- **structlog** - Structured logging

## Quick Start

```bash
# Setup
chmod +x setup.sh
./setup.sh

# Configure
edit .env

# Run
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Exports

- `POST /api/exports` - Create new export
- `GET /api/exports/{id}` - Get export status
- `GET /api/exports` - List all exports
- `DELETE /api/exports/{id}` - Cancel export
- `POST /api/exports/{id}/retry` - Retry failed export

### Tables

- `GET /api/tables` - List all tables with metadata
- `GET /api/tables/{name}` - Get table details
- `GET /api/tables/{name}/relationships` - Get relationships
- `GET /api/tables/{name}/related` - Get related tables

### Webhooks

- `POST /api/webhooks/bitrix24` - Bitrix24 event receiver

## Usage Example

```python
import httpx

# Create export
async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8000/api/exports", json={
        "entity_name": "deals",
        "export_type": "date_range",
        "date_range": {
            "date_from": "2025-01-01T00:00:00",
            "date_to": "2025-12-31T23:59:59"
        },
        "include_related": true,
        "use_turkish_names": true,
        "separate_date_time": true,
        "batch_size": 500,
        "sheet_gid": "0"
    })
    
    export_id = response.json()["id"]
    print(f"Export created: {export_id}")
    
    # Check progress
    status = await client.get(f"http://localhost:8000/api/exports/{export_id}")
    print(status.json())
```

## Configuration

See `.env.example` for all configuration options.

## Database Migrations

```bash
psql postgresql://bitsheet:bitsheet123@localhost:5432/bitsheet_db -f migrations/001_create_export_tables.sql
```

## Development

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Format code
black app/
isort app/
```

## Production

```bash
# Use gunicorn with uvicorn workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## License

MIT
