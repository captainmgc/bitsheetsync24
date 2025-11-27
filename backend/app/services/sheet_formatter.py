"""
Google Sheet Formatter Service
Handles:
- Column coloring (editable = green, readonly = red)
- Sync status column management
- Error message writing to sheets
"""

import httpx
from typing import Dict, List, Any, Optional
import structlog

from app.config import settings

logger = structlog.get_logger()


# Color definitions (RGB format for Google Sheets API)
COLORS = {
    "editable": {
        "red": 0.91,    # #E8F5E9 - Light green
        "green": 0.96,
        "blue": 0.91
    },
    "readonly": {
        "red": 1.0,     # #FFEBEE - Light red
        "green": 0.92,
        "blue": 0.93
    },
    "sync_status": {
        "red": 1.0,     # #FFF8E1 - Light yellow
        "green": 0.97,
        "blue": 0.88
    },
    "error": {
        "red": 1.0,     # #FFCDD2 - Stronger red for errors
        "green": 0.80,
        "blue": 0.82
    },
    "success": {
        "red": 0.78,    # #C8E6C9 - Stronger green for success
        "green": 0.90,
        "blue": 0.79
    },
    "pending": {
        "red": 1.0,     # #FFE0B2 - Orange for pending
        "green": 0.88,
        "blue": 0.70
    },
    "white": {
        "red": 1.0,
        "green": 1.0,
        "blue": 1.0
    }
}

# Sync status column name
SYNC_STATUS_COLUMN = "Senkronizasyon"

# Status values
STATUS_VALUES = {
    "synced": "✅ Senkronize",
    "pending": "⏳ Beklemede",
    "syncing": "🔄 Senkronize ediliyor",
    "error": "❌ Hata",
    "conflict": "⚠️ Çakışma"
}


class SheetFormatter:
    """
    Formats Google Sheets with colors and status columns
    """
    
    def __init__(self, access_token: str):
        """
        Initialize with user's access token
        
        Args:
            access_token: Valid Google API access token
        """
        self.access_token = access_token
        self.sheets_api_url = "https://sheets.googleapis.com/v4/spreadsheets"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def get_sheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet metadata including sheet info
        
        Args:
            spreadsheet_id: Google Sheet ID
            
        Returns:
            Spreadsheet metadata
        """
        try:
            url = f"{self.sheets_api_url}/{spreadsheet_id}"
            params = {"fields": "sheets(properties,data.rowData.values.userEnteredValue)"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error("sheet_metadata_failed", error=str(e))
            raise

    async def get_sheet_id_by_gid(self, spreadsheet_id: str, gid: str) -> Optional[int]:
        """
        Get sheet ID (for API) from GID (URL parameter)
        
        Args:
            spreadsheet_id: Google Sheet ID
            gid: Sheet GID from URL
            
        Returns:
            Sheet ID for API calls
        """
        try:
            metadata = await self.get_sheet_metadata(spreadsheet_id)
            sheets = metadata.get("sheets", [])
            
            for sheet in sheets:
                props = sheet.get("properties", {})
                if str(props.get("sheetId")) == str(gid):
                    return props.get("sheetId")
            
            # If gid is 0 or not found, return first sheet
            if sheets:
                return sheets[0].get("properties", {}).get("sheetId", 0)
            
            return 0
            
        except Exception as e:
            logger.error("get_sheet_id_failed", error=str(e))
            return 0

    async def apply_column_colors(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        editable_columns: List[int],
        readonly_columns: List[int],
        total_rows: int = 1000
    ) -> Dict[str, Any]:
        """
        Apply colors to columns based on editability
        
        Args:
            spreadsheet_id: Google Sheet ID
            sheet_id: Sheet ID (not GID)
            editable_columns: List of column indices that are editable
            readonly_columns: List of column indices that are read-only
            total_rows: Number of rows to apply formatting
            
        Returns:
            API response
        """
        requests = []
        
        # Color editable columns (green)
        for col_idx in editable_columns:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,  # Only header row
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": COLORS["editable"]
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })
        
        # Color read-only columns (red)
        for col_idx in readonly_columns:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,  # Only header row
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": COLORS["readonly"]
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })
        
        if not requests:
            return {"status": "no_changes"}
        
        return await self._batch_update(spreadsheet_id, requests)

    async def add_sync_status_column(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        column_index: int
    ) -> Dict[str, Any]:
        """
        Add "Senkronizasyon" column at specified index
        
        Args:
            spreadsheet_id: Google Sheet ID
            sheet_id: Sheet ID
            column_index: Where to insert the column
            
        Returns:
            API response
        """
        requests = [
            # Insert column
            {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index,
                        "endIndex": column_index + 1
                    },
                    "inheritFromBefore": False
                }
            },
            # Set header
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": column_index,
                        "endColumnIndex": column_index + 1
                    },
                    "rows": [{
                        "values": [{
                            "userEnteredValue": {"stringValue": SYNC_STATUS_COLUMN},
                            "userEnteredFormat": {
                                "backgroundColor": COLORS["sync_status"],
                                "textFormat": {"bold": True}
                            }
                        }]
                    }],
                    "fields": "userEnteredValue,userEnteredFormat"
                }
            },
            # Set column width
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": column_index,
                        "endIndex": column_index + 1
                    },
                    "properties": {"pixelSize": 150},
                    "fields": "pixelSize"
                }
            }
        ]
        
        return await self._batch_update(spreadsheet_id, requests)

    async def update_sync_status(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
        status_column_index: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update sync status for a specific row
        
        Args:
            spreadsheet_id: Google Sheet ID
            sheet_name: Sheet name
            row_number: Row number (1-indexed)
            status_column_index: Column index for status (0-indexed)
            status: Status key (synced, pending, error, conflict)
            error_message: Optional error message
            
        Returns:
            API response
        """
        # Convert column index to letter (A, B, C, ...)
        col_letter = self._index_to_column_letter(status_column_index)
        range_notation = f"'{sheet_name}'!{col_letter}{row_number}"
        
        # Build status text
        status_text = STATUS_VALUES.get(status, status)
        if error_message and status == "error":
            status_text = f"❌ Hata: {error_message[:50]}"
        
        try:
            url = f"{self.sheets_api_url}/{spreadsheet_id}/values/{range_notation}"
            params = {"valueInputOption": "USER_ENTERED"}
            body = {"values": [[status_text]]}
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    json=body,
                    timeout=30
                )
                response.raise_for_status()
                
            logger.info(
                "sync_status_updated",
                spreadsheet_id=spreadsheet_id,
                row=row_number,
                status=status
            )
            
            return {"success": True, "row": row_number, "status": status}
            
        except httpx.HTTPError as e:
            logger.error("sync_status_update_failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def batch_update_sync_status(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        status_column_index: int,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update sync status for multiple rows
        
        Args:
            spreadsheet_id: Google Sheet ID
            sheet_name: Sheet name
            status_column_index: Column index for status
            updates: List of {row_number, status, error_message}
            
        Returns:
            API response
        """
        col_letter = self._index_to_column_letter(status_column_index)
        
        data = []
        for update in updates:
            row_num = update["row_number"]
            status = update["status"]
            error_msg = update.get("error_message")
            
            status_text = STATUS_VALUES.get(status, status)
            if error_msg and status == "error":
                status_text = f"❌ Hata: {error_msg[:50]}"
            
            data.append({
                "range": f"'{sheet_name}'!{col_letter}{row_num}",
                "values": [[status_text]]
            })
        
        try:
            url = f"{self.sheets_api_url}/{spreadsheet_id}/values:batchUpdate"
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": data
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=body,
                    timeout=60
                )
                response.raise_for_status()
                
            logger.info(
                "batch_sync_status_updated",
                spreadsheet_id=spreadsheet_id,
                count=len(updates)
            )
            
            return {"success": True, "updated_count": len(updates)}
            
        except httpx.HTTPError as e:
            logger.error("batch_sync_status_failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def format_sheet_for_reverse_sync(
        self,
        spreadsheet_id: str,
        gid: str,
        editable_column_indices: List[int],
        readonly_column_indices: List[int],
        add_status_column: bool = True
    ) -> Dict[str, Any]:
        """
        Full sheet formatting for reverse sync
        
        Args:
            spreadsheet_id: Google Sheet ID
            gid: Sheet GID
            editable_column_indices: Editable column indices
            readonly_column_indices: Read-only column indices
            add_status_column: Whether to add sync status column
            
        Returns:
            Formatting result
        """
        try:
            # Get sheet ID
            sheet_id = await self.get_sheet_id_by_gid(spreadsheet_id, gid)
            
            result = {
                "spreadsheet_id": spreadsheet_id,
                "sheet_id": sheet_id,
                "gid": gid,
                "actions": []
            }
            
            # Apply column colors
            if editable_column_indices or readonly_column_indices:
                color_result = await self.apply_column_colors(
                    spreadsheet_id,
                    sheet_id,
                    editable_column_indices,
                    readonly_column_indices
                )
                result["actions"].append({
                    "action": "apply_colors",
                    "editable_count": len(editable_column_indices),
                    "readonly_count": len(readonly_column_indices),
                    "result": color_result
                })
            
            # Add status column
            if add_status_column:
                # Status column at the end
                status_col_idx = max(
                    max(editable_column_indices or [0]),
                    max(readonly_column_indices or [0])
                ) + 1
                
                status_result = await self.add_sync_status_column(
                    spreadsheet_id,
                    sheet_id,
                    status_col_idx
                )
                result["actions"].append({
                    "action": "add_status_column",
                    "column_index": status_col_idx,
                    "result": status_result
                })
                result["status_column_index"] = status_col_idx
            
            result["success"] = True
            
            logger.info(
                "sheet_formatted",
                spreadsheet_id=spreadsheet_id,
                editable_cols=len(editable_column_indices),
                readonly_cols=len(readonly_column_indices)
            )
            
            return result
            
        except Exception as e:
            logger.error("sheet_format_failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def _batch_update(self, spreadsheet_id: str, requests: List[Dict]) -> Dict[str, Any]:
        """Execute batch update request"""
        try:
            url = f"{self.sheets_api_url}/{spreadsheet_id}:batchUpdate"
            body = {"requests": requests}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=body,
                    timeout=60
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error("batch_update_failed", error=str(e))
            raise

    @staticmethod
    def _index_to_column_letter(index: int) -> str:
        """Convert 0-indexed column to letter (0=A, 1=B, 26=AA, etc.)"""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result
