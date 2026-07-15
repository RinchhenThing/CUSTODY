"""
VM Client Service Module
Handles all safe, decoupled HTTP communication with external VM agents.
"""
import requests
from typing import Dict, Any, Optional
from config import settings

class VMAgentClient:
    def __init__(self):
        self.production_url = settings.PRODUCTION_AGENT_URL
        self.detection_url = settings.DETECTION_AGENT_URL
        self.backup_url = settings.BACKUP_AGENT_URL
        self.quarantine_url = settings.QUARANTINE_AGENT_URL
        self.timeout = 5.0 # Safe internal socket timeout in seconds

    def _safe_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Executes network calls safely, intercepting errors to provide state objects."""
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code in [200, 201]:
                return {"status": "ONLINE", "data": response.json(), "error": None}
            return {
                "status": "DEGRADED", 
                "data": None, 
                "error": f"Agent returned status code {response.status_code}"
            }
        except requests.exceptions.RequestException as e:
            return {"status": "OFFLINE", "data": None, "error": str(e)}

    # --- Health Matrix Endpoints ---
    def get_production_health(self) -> Dict[str, Any]:
        return self._safe_request("GET", f"{self.production_url}/api/health")

    def get_detection_health(self) -> Dict[str, Any]:
        return self._safe_request("GET", f"{self.detection_url}/api/health")

    def get_backup_health(self) -> Dict[str, Any]:
        return self._safe_request("GET", f"{self.backup_url}/api/health")

    def get_quarantine_health(self) -> Dict[str, Any]:
        return self._safe_request("GET", f"{self.quarantine_url}/api/health")

    # --- Backup Agent Operations ---
    def get_backup_storage(self) -> Dict[str, Any]:
        """Fetches active storage capacities and hardware status from Backup VM."""
        return self._safe_request("GET", f"{self.backup_url}/api/storage/info")

    def trigger_backup_deletion(self, storage_path: str) -> Dict[str, Any]:
        """Instructs the Backup agent to erase an unlinked, expired, or corrupted version file."""
        return self._safe_request("POST", f"{self.backup_url}/api/storage/delete", json={"path": storage_path})

    # --- Restore Manager Operations ---
    def request_restore(self, sha256_hash: str, storage_path: str, destination_path: str) -> Dict[str, Any]:
        """
        Commands the Backup VM agent to verify hash integrity and securely 
        pipe the clean binary straight back to the designated Production path.
        """
        payload = {
            "sha256": sha256_hash,
            "storage_path": storage_path,
            "destination_path": destination_path
        }
        return self._safe_request("POST", f"{self.backup_url}/api/restore/execute", json=payload)

    # --- Quarantine Agent Operations ---
    def get_quarantine_files_status(self) -> Dict[str, Any]:
        """Pulls runtime operational state details for sandbox analysis updates."""
        return self._safe_request("GET", f"{self.quarantine_url}/api/quarantine/status")

    def release_quarantine(self, file_hash: str, target_path: str) -> Dict[str, Any]:
        """Commands the Quarantine VM to decrypt and pass a cleared binary back to production."""
        payload = {
            "sha256": file_hash,
            "destination_path": target_path
        }
        return self._safe_request("POST", f"{self.quarantine_url}/api/quarantine/release", json=payload)

    def purge_quarantine(self, file_hash: str) -> Dict[str, Any]:
        """Permanently annihilates a confirmed ransomware binary payload from isolated storage."""
        return self._safe_request("DELETE", f"{self.quarantine_url}/api/quarantine/purge/{file_hash}")
    
    #recently added
    '''
    def purge_malicious_payload(self, file_hash: str):
        return self.purge_quarantine(file_hash)
    '''

# Instantiate global communication agent client
vm_client = VMAgentClient()