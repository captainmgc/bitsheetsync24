"""
Google Sheets API Direct Service
Uses Google Sheets API v4 with OAuth access token
"""
import httpx
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class GoogleSheetsService:
    """
    Direct Google Sheets API v4 integration
    Uses user's OAuth access token for authentication
    """
    
    BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
    DRIVE_URL = "https://www.googleapis.com/drive/v3/files"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def create_spreadsheet(
        self,
        title: str,
        sheets: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new Google Spreadsheet
        
        Args:
            title: Spreadsheet title
            sheets: List of sheet names to create (default: ["Sheet1"])
            
        Returns:
            {
                "spreadsheet_id": str,
                "spreadsheet_url": str,
                "sheets": [{"sheet_id": int, "title": str}]
            }
        """
        try:
            if sheets is None:
                sheets = ["Sheet1"]
            
            payload = {
                "properties": {
                    "title": title
                },
                "sheets": [
                    {"properties": {"title": sheet_name}}
                    for sheet_name in sheets
                ]
            }
            
            response = await self.client.post(
                self.BASE_URL,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            spreadsheet_id = result["spreadsheetId"]
            spreadsheet_url = result["spreadsheetUrl"]
            
            created_sheets = [
                {
                    "sheet_id": sheet["properties"]["sheetId"],
                    "title": sheet["properties"]["title"]
                }
                for sheet in result["sheets"]
            ]
            
            logger.info("spreadsheet_created",
                       spreadsheet_id=spreadsheet_id,
                       title=title,
                       sheets=len(created_sheets))
            
            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
                "sheets": created_sheets
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("create_spreadsheet_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise Exception(f"Failed to create spreadsheet: {e.response.text}")
        except Exception as e:
            logger.error("create_spreadsheet_exception", error=str(e))
            raise
    
    async def append_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED"
    ) -> Dict[str, Any]:
        """
        Append values to a sheet
        
        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: A1 notation (e.g., "Sheet1!A1" or just "Sheet1")
            values: 2D array of values
            value_input_option: "RAW" or "USER_ENTERED"
            
        Returns:
            Update response from Sheets API
        """
        try:
            url = f"{self.BASE_URL}/{spreadsheet_id}/values/{range_name}:append"
            
            params = {
                "valueInputOption": value_input_option,
                "insertDataOption": "INSERT_ROWS"
            }
            
            payload = {
                "values": values
            }
            
            response = await self.client.post(
                url,
                json=payload,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info("values_appended",
                       spreadsheet_id=spreadsheet_id,
                       range=range_name,
                       rows=len(values))
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error("append_values_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise Exception(f"Failed to append values: {e.response.text}")
        except Exception as e:
            logger.error("append_values_exception", error=str(e))
            raise
    
    async def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[Any]],
        value_input_option: str = "USER_ENTERED"
    ) -> Dict[str, Any]:
        """
        Update values in a sheet (overwrites existing)
        
        Args:
            spreadsheet_id: The spreadsheet ID
            range_name: A1 notation
            values: 2D array of values
            value_input_option: "RAW" or "USER_ENTERED"
            
        Returns:
            Update response
        """
        try:
            url = f"{self.BASE_URL}/{spreadsheet_id}/values/{range_name}"
            
            params = {
                "valueInputOption": value_input_option
            }
            
            payload = {
                "values": values
            }
            
            response = await self.client.put(
                url,
                json=payload,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info("values_updated",
                       spreadsheet_id=spreadsheet_id,
                       range=range_name,
                       rows=len(values))
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error("update_values_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise Exception(f"Failed to update values: {e.response.text}")
        except Exception as e:
            logger.error("update_values_exception", error=str(e))
            raise
    
    async def batch_update(
        self,
        spreadsheet_id: str,
        requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch update spreadsheet (formatting, adding sheets, etc.)
        
        Args:
            spreadsheet_id: The spreadsheet ID
            requests: List of request objects
            
        Returns:
            Batch update response
        """
        try:
            url = f"{self.BASE_URL}/{spreadsheet_id}:batchUpdate"
            
            payload = {
                "requests": requests
            }
            
            response = await self.client.post(
                url,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            logger.info("batch_update_success",
                       spreadsheet_id=spreadsheet_id,
                       requests=len(requests))
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error("batch_update_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise Exception(f"Failed to batch update: {e.response.text}")
        except Exception as e:
            logger.error("batch_update_exception", error=str(e))
            raise
    
    async def add_sheet(
        self,
        spreadsheet_id: str,
        sheet_title: str
    ) -> Dict[str, Any]:
        """
        Add a new sheet to existing spreadsheet
        
        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_title: Title for the new sheet
            
        Returns:
            Sheet info
        """
        try:
            requests = [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_title
                        }
                    }
                }
            ]
            
            result = await self.batch_update(spreadsheet_id, requests)
            
            sheet_id = result["replies"][0]["addSheet"]["properties"]["sheetId"]
            
            logger.info("sheet_added",
                       spreadsheet_id=spreadsheet_id,
                       sheet_title=sheet_title,
                       sheet_id=sheet_id)
            
            return {
                "sheet_id": sheet_id,
                "title": sheet_title
            }
            
        except Exception as e:
            logger.error("add_sheet_error", error=str(e))
            raise
    
    async def get_spreadsheet_info(
        self,
        spreadsheet_id: str
    ) -> Dict[str, Any]:
        """
        Get spreadsheet metadata
        
        Args:
            spreadsheet_id: The spreadsheet ID
            
        Returns:
            Spreadsheet info
        """
        try:
            url = f"{self.BASE_URL}/{spreadsheet_id}"
            
            response = await self.client.get(
                url,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "spreadsheet_id": result["spreadsheetId"],
                "title": result["properties"]["title"],
                "spreadsheet_url": result["spreadsheetUrl"],
                "sheets": [
                    {
                        "sheet_id": sheet["properties"]["sheetId"],
                        "title": sheet["properties"]["title"],
                        "index": sheet["properties"]["index"]
                    }
                    for sheet in result["sheets"]
                ]
            }
            
        except httpx.HTTPStatusError as e:
            logger.error("get_spreadsheet_info_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise Exception(f"Failed to get spreadsheet info: {e.response.text}")
        except Exception as e:
            logger.error("get_spreadsheet_info_exception", error=str(e))
            raise
    
    async def format_header_row(
        self,
        spreadsheet_id: str,
        sheet_id: int
    ) -> None:
        """
        Format the first row as header (bold, background color)
        
        Args:
            spreadsheet_id: The spreadsheet ID
            sheet_id: The sheet ID (not the name)
        """
        try:
            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.2,
                                    "green": 0.6,
                                    "blue": 0.9
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1.0,
                                        "green": 1.0,
                                        "blue": 1.0
                                    }
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                }
            ]
            
            await self.batch_update(spreadsheet_id, requests)
            
            logger.info("header_formatted",
                       spreadsheet_id=spreadsheet_id,
                       sheet_id=sheet_id)
            
        except Exception as e:
            logger.error("format_header_error", error=str(e))
            # Don't raise - formatting is non-critical
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
