"""
Google Apps Script Auto-Installer Service
Automatically deploys webhook script to user's Google Sheet
Uses Google Apps Script API
"""

import httpx
import json
from typing import Dict, Any, Optional
import structlog

from app.config import settings

logger = structlog.get_logger()

# Webhook URL for production
WEBHOOK_URL = "https://etablo.japonkonutlari.com/api/v1/sheet-sync/webhook"

# Google Apps Script code template
APPS_SCRIPT_CODE = '''
/**
 * BitSheet24 - Reverse Sync Webhook
 * Otomatik olarak Sheet değişikliklerini backend'e gönderir
 * 
 * @author BitSheet24 Auto-Installer
 * @version 1.0.0
 */

// Configuration
const CONFIG = {
  webhookUrl: "{{WEBHOOK_URL}}",
  configId: "{{CONFIG_ID}}",
  userId: "{{USER_ID}}",
  entityType: "{{ENTITY_TYPE}}",
  idColumnName: "ID",
  statusColumnName: "Senkronizasyon"
};

/**
 * Trigger: Sheet düzenlendiğinde çalışır
 */
function onEdit(e) {
  try {
    // Get edit info
    const range = e.range;
    const sheet = range.getSheet();
    const row = range.getRow();
    const col = range.getColumn();
    
    // Skip header row
    if (row === 1) return;
    
    // Skip status column updates
    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const statusColIndex = headers.indexOf(CONFIG.statusColumnName);
    if (col === statusColIndex + 1) return;
    
    // Get row data
    const rowData = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
    
    // Find ID column
    const idColIndex = headers.indexOf(CONFIG.idColumnName);
    if (idColIndex === -1) {
      Logger.log("ID column not found");
      return;
    }
    
    const entityId = rowData[idColIndex];
    if (!entityId) {
      Logger.log("No entity ID in row " + row);
      return;
    }
    
    // Get changed field
    const changedHeader = headers[col - 1];
    const oldValue = e.oldValue || "";
    const newValue = e.value || "";
    
    // Prepare webhook payload
    const payload = {
      event: "row_edited",
      config_id: CONFIG.configId,
      user_id: CONFIG.userId,
      entity_type: CONFIG.entityType,
      entity_id: String(entityId),
      row_number: row,
      changes: {},
      row_data: {},
      timestamp: new Date().toISOString()
    };
    
    // Add change info
    payload.changes[changedHeader] = {
      old_value: oldValue,
      new_value: newValue,
      column_index: col - 1
    };
    
    // Add full row data
    headers.forEach((header, idx) => {
      if (header && header !== CONFIG.statusColumnName) {
        payload.row_data[header] = rowData[idx];
      }
    });
    
    // Send webhook
    sendWebhook(payload, sheet, row, statusColIndex);
    
  } catch (error) {
    Logger.log("onEdit error: " + error.toString());
  }
}

/**
 * Webhook gönder
 */
function sendWebhook(payload, sheet, row, statusColIndex) {
  try {
    // Update status to pending
    if (statusColIndex >= 0) {
      sheet.getRange(row, statusColIndex + 1).setValue("⏳ Gönderiliyor...");
    }
    
    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(CONFIG.webhookUrl, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    Logger.log("Webhook response: " + responseCode + " - " + responseText);
    
    // Update status based on response
    if (statusColIndex >= 0) {
      if (responseCode === 200) {
        const result = JSON.parse(responseText);
        if (result.success) {
          sheet.getRange(row, statusColIndex + 1).setValue("✅ Senkronize");
        } else {
          sheet.getRange(row, statusColIndex + 1).setValue("❌ Hata: " + (result.error || "Bilinmeyen"));
        }
      } else {
        sheet.getRange(row, statusColIndex + 1).setValue("❌ Hata: HTTP " + responseCode);
      }
    }
    
  } catch (error) {
    Logger.log("sendWebhook error: " + error.toString());
    if (statusColIndex >= 0) {
      sheet.getRange(row, statusColIndex + 1).setValue("❌ Hata: " + error.toString().substring(0, 30));
    }
  }
}

/**
 * Manuel test fonksiyonu
 */
function testWebhook() {
  const testPayload = {
    event: "test",
    config_id: CONFIG.configId,
    user_id: CONFIG.userId,
    entity_type: CONFIG.entityType,
    timestamp: new Date().toISOString()
  };
  
  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(testPayload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(CONFIG.webhookUrl, options);
  Logger.log("Test response: " + response.getResponseCode() + " - " + response.getContentText());
  return response.getContentText();
}

/**
 * Trigger kurulumu
 */
function setupTrigger() {
  // Mevcut triggerleri temizle
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === "onEdit") {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // Yeni trigger oluştur
  ScriptApp.newTrigger("onEdit")
    .forSpreadsheet(SpreadsheetApp.getActive())
    .onEdit()
    .create();
  
  Logger.log("Trigger setup complete");
}
'''

# Apps Script project manifest
APPS_SCRIPT_MANIFEST = {
    "timeZone": "Europe/Istanbul",
    "dependencies": {},
    "exceptionLogging": "STACKDRIVER",
    "runtimeVersion": "V8",
    "webapp": {
        "executeAs": "USER_DEPLOYING",
        "access": "ANYONE_ANONYMOUS"
    }
}


class AppsScriptInstaller:
    """
    Automatically installs Google Apps Script webhook to user's sheet
    Uses Google Apps Script API
    """
    
    def __init__(self, access_token: str):
        """
        Initialize with user's access token
        
        Args:
            access_token: Google OAuth access token with script.projects scope
        """
        self.access_token = access_token
        self.script_api_url = "https://script.googleapis.com/v1/projects"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def create_script_project(
        self,
        spreadsheet_id: str,
        title: str = "BitSheet24 Webhook"
    ) -> Dict[str, Any]:
        """
        Create a new Apps Script project bound to the spreadsheet
        
        Args:
            spreadsheet_id: Google Sheet ID
            title: Project title
            
        Returns:
            Created project info
        """
        try:
            body = {
                "title": title,
                "parentId": spreadsheet_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.script_api_url,
                    headers=self.headers,
                    json=body,
                    timeout=30
                )
                response.raise_for_status()
                project = response.json()
            
            logger.info(
                "script_project_created",
                project_id=project.get("scriptId"),
                spreadsheet_id=spreadsheet_id
            )
            
            return project
            
        except httpx.HTTPError as e:
            logger.error("create_script_project_failed", error=str(e))
            raise Exception(f"Failed to create Apps Script project: {str(e)}")

    async def update_script_content(
        self,
        script_id: str,
        config_id: str,
        user_id: str,
        entity_type: str,
        webhook_url: str = WEBHOOK_URL
    ) -> Dict[str, Any]:
        """
        Update script content with webhook code
        
        Args:
            script_id: Apps Script project ID
            config_id: BitSheet24 config ID
            user_id: User ID
            entity_type: Bitrix24 entity type
            webhook_url: Backend webhook URL
            
        Returns:
            Update result
        """
        try:
            # Prepare script code with config values
            script_code = APPS_SCRIPT_CODE.replace("{{WEBHOOK_URL}}", webhook_url)
            script_code = script_code.replace("{{CONFIG_ID}}", str(config_id))
            script_code = script_code.replace("{{USER_ID}}", user_id)
            script_code = script_code.replace("{{ENTITY_TYPE}}", entity_type)
            
            # Prepare request body
            body = {
                "files": [
                    {
                        "name": "Code",
                        "type": "SERVER_JS",
                        "source": script_code
                    },
                    {
                        "name": "appsscript",
                        "type": "JSON",
                        "source": json.dumps(APPS_SCRIPT_MANIFEST)
                    }
                ]
            }
            
            url = f"{self.script_api_url}/{script_id}/content"
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url,
                    headers=self.headers,
                    json=body,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(
                "script_content_updated",
                script_id=script_id,
                config_id=config_id
            )
            
            return result
            
        except httpx.HTTPError as e:
            logger.error("update_script_content_failed", error=str(e))
            raise Exception(f"Failed to update script content: {str(e)}")

    async def get_script_content(self, script_id: str) -> Dict[str, Any]:
        """Get current script content"""
        try:
            url = f"{self.script_api_url}/{script_id}/content"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error("get_script_content_failed", error=str(e))
            raise

    async def run_script_function(
        self,
        script_id: str,
        function_name: str,
        parameters: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run a function in the Apps Script project
        
        Args:
            script_id: Apps Script project ID
            function_name: Function to run (e.g., "setupTrigger")
            parameters: Optional parameters
            
        Returns:
            Execution result
        """
        try:
            url = f"{self.script_api_url}/{script_id}:run"
            body = {
                "function": function_name,
                "devMode": True
            }
            if parameters:
                body["parameters"] = parameters
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=body,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(
                "script_function_executed",
                script_id=script_id,
                function=function_name
            )
            
            return result
            
        except httpx.HTTPError as e:
            logger.error("run_script_function_failed", error=str(e))
            raise Exception(f"Failed to run script function: {str(e)}")

    async def install_webhook(
        self,
        spreadsheet_id: str,
        config_id: str,
        user_id: str,
        entity_type: str,
        webhook_url: str = WEBHOOK_URL
    ) -> Dict[str, Any]:
        """
        Full installation: Create project, add code, setup trigger
        
        Args:
            spreadsheet_id: Google Sheet ID
            config_id: BitSheet24 config ID
            user_id: User ID
            entity_type: Bitrix24 entity type
            webhook_url: Backend webhook URL
            
        Returns:
            Installation result with script_id
        """
        result = {
            "spreadsheet_id": spreadsheet_id,
            "config_id": config_id,
            "steps": []
        }
        
        try:
            # Step 1: Create project
            project = await self.create_script_project(
                spreadsheet_id,
                f"BitSheet24 - {entity_type.title()}"
            )
            script_id = project.get("scriptId")
            result["script_id"] = script_id
            result["steps"].append({
                "step": "create_project",
                "success": True,
                "script_id": script_id
            })
            
            # Step 2: Update content
            await self.update_script_content(
                script_id,
                config_id,
                user_id,
                entity_type,
                webhook_url
            )
            result["steps"].append({
                "step": "update_content",
                "success": True
            })
            
            # Step 3: Setup trigger (runs setupTrigger function)
            # Note: This requires additional OAuth scope
            try:
                await self.run_script_function(script_id, "setupTrigger")
                result["steps"].append({
                    "step": "setup_trigger",
                    "success": True
                })
            except Exception as e:
                # Trigger setup might fail due to permissions
                # User can run it manually from script editor
                result["steps"].append({
                    "step": "setup_trigger",
                    "success": False,
                    "error": str(e),
                    "manual_required": True
                })
            
            result["success"] = True
            result["webhook_url"] = webhook_url
            
            logger.info(
                "webhook_installed",
                spreadsheet_id=spreadsheet_id,
                script_id=script_id
            )
            
            return result
            
        except Exception as e:
            logger.error("webhook_installation_failed", error=str(e))
            result["success"] = False
            result["error"] = str(e)
            return result

    async def check_existing_script(self, spreadsheet_id: str) -> Optional[str]:
        """
        Check if spreadsheet already has a BitSheet24 script
        
        Args:
            spreadsheet_id: Google Sheet ID
            
        Returns:
            Script ID if exists, None otherwise
        """
        try:
            # List all scripts for the spreadsheet
            url = f"https://www.googleapis.com/drive/v3/files"
            params = {
                "q": f"'{spreadsheet_id}' in parents and mimeType='application/vnd.google-apps.script'",
                "fields": "files(id,name)"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
            
            files = data.get("files", [])
            for file in files:
                if "BitSheet24" in file.get("name", ""):
                    return file.get("id")
            
            return None
            
        except Exception as e:
            logger.warning("check_existing_script_failed", error=str(e))
            return None

    async def uninstall_webhook(self, script_id: str) -> Dict[str, Any]:
        """
        Remove Apps Script project
        
        Args:
            script_id: Script project ID to delete
            
        Returns:
            Deletion result
        """
        try:
            url = f"https://www.googleapis.com/drive/v3/files/{script_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=self.headers, timeout=30)
                response.raise_for_status()
            
            logger.info("webhook_uninstalled", script_id=script_id)
            
            return {"success": True, "deleted_script_id": script_id}
            
        except httpx.HTTPError as e:
            logger.error("webhook_uninstall_failed", error=str(e))
            return {"success": False, "error": str(e)}
