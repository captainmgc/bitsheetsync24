"""
Google Sheets Uploader Service
Handles communication with Google Sheets via webhook
"""
import httpx
from typing import List, Dict, Any, Optional
import structlog
from app.config import settings

logger = structlog.get_logger()


class SheetsUploader:
    """
    Uploads data to Google Sheets using webhook
    Implements Smart Merge strategy
    """
    
    def __init__(self):
        self.webhook_url = settings.google_sheets_webhook_url
        self.timeout = settings.export_timeout_seconds
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def upload_batch(
        self,
        data: List[List[Any]],
        sheet_gid: str = "0",
        operation: str = "append"
    ) -> Dict[str, Any]:
        """
        Upload a batch of data to Google Sheets
        
        Args:
            data: 2D array of data (including headers if first batch)
            sheet_gid: Sheet ID (gid parameter)
            operation: "append", "replace", "upsert"
            
        Returns:
            Response from Google Apps Script
        """
        try:
            payload = {
                "data": data,
                "gid": sheet_gid,
                "operation": operation
            }
            
            response = await self.client.post(
                f"{self.webhook_url}?gid={sheet_gid}",
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("sheets_upload_success",
                       rows=len(data),
                       gid=sheet_gid,
                       operation=operation)
            
            return result
            
        except httpx.TimeoutException as e:
            logger.error("sheets_upload_timeout", error=str(e), timeout=self.timeout)
            raise Exception(f"Google Sheets webhook timeout after {self.timeout}s")
            
        except httpx.HTTPStatusError as e:
            logger.error("sheets_upload_http_error", 
                        status=e.response.status_code,
                        error=str(e))
            raise Exception(f"Google Sheets API error: {e.response.status_code}")
            
        except Exception as e:
            logger.error("sheets_upload_error", error=str(e))
            raise
    
    async def clear_sheet(self, sheet_gid: str = "0") -> bool:
        """Clear all data from a sheet"""
        try:
            payload = {
                "operation": "clear",
                "gid": sheet_gid
            }
            
            response = await self.client.post(
                f"{self.webhook_url}?gid={sheet_gid}",
                json=payload
            )
            
            response.raise_for_status()
            logger.info("sheets_cleared", gid=sheet_gid)
            return True
            
        except Exception as e:
            logger.error("sheets_clear_error", gid=sheet_gid, error=str(e))
            return False
    
    async def smart_merge(
        self,
        data: List[List[Any]],
        sheet_gid: str = "0",
        id_column: int = 0
    ) -> Dict[str, Any]:
        """
        Smart merge: Update existing rows, append new ones
        
        Args:
            data: 2D array with headers
            sheet_gid: Sheet ID
            id_column: Column index for ID matching (default 0)
            
        Returns:
            Statistics about merge operation
        """
        try:
            payload = {
                "data": data,
                "gid": sheet_gid,
                "operation": "smart_merge",
                "id_column": id_column
            }
            
            response = await self.client.post(
                f"{self.webhook_url}?gid={sheet_gid}",
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("sheets_smart_merge",
                       total_rows=len(data) - 1,  # Exclude header
                       updated=result.get("updated", 0),
                       inserted=result.get("inserted", 0))
            
            return result
            
        except Exception as e:
            logger.error("sheets_smart_merge_error", error=str(e))
            raise
    
    async def test_connection(self) -> bool:
        """Test webhook connectivity"""
        try:
            payload = {
                "operation": "ping",
                "data": [["test"]]
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            logger.info("sheets_connection_test_success")
            return True
            
        except Exception as e:
            logger.error("sheets_connection_test_failed", error=str(e))
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
