"""
VM Client Service Module
Provides lean, decoupled HTTP communication channels for central engine microservices.
"""

import requests
from typing import Dict, Any
from config import settings


class BaseEngineClient:
    """Core request pipeline offering exception shielding and timeout control."""
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = 5.0  # Internal safety socket timeout

    def _safe_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Safely dispatches network operations, wrapping exceptions in uniform status payloads."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except ValueError:
                    data = None
                return {"status": "ONLINE", "data": data, "error": None}
                
            return {
                "status": "DEGRADED",
                "data": None,
                "error": f"Engine returned status code {response.status_code}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "OFFLINE",
                "data": None,
                "error": "Engine connection timed out",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "OFFLINE", "data": None, "error": str(e)}


class DetectionClient(BaseEngineClient):
    """Interfaces with Detection Engine Core telemetry and observation channels."""
    def __init__(self):
        url = getattr(settings, "DETECTION_SERVICE_URL", "http://localhost:8001")
        super().__init__(url)

    def get_detection_health(self) -> Dict[str, Any]:
        """Polls heartbeats from the Detection Core system."""
        return self._safe_request("GET", "/api/health")

    def get_detection_stats(self) -> Dict[str, Any]:
        """Extracts runtime operations metrics and watch folder performance indicators."""
        return self._safe_request("GET", "/api/stats")

    def get_detection_info(self) -> Dict[str, Any]:
        """Fetches architectural configuration environments from the engine metadata catalog."""
        return self._safe_request("GET", "/api/service-info")


class BackupClient(BaseEngineClient):
    """Interfaces with Backup Engine Core replication layers and catalog tables."""
    def __init__(self):
        url = getattr(settings, "BACKUP_SERVICE_URL", "http://localhost:8002")
        super().__init__(url)

    def get_backup_health(self) -> Dict[str, Any]:
        """Polls heartbeats from the Backup Core system."""
        return self._safe_request("GET", "/api/health")

    def get_backup_stats(self) -> Dict[str, Any]:
        """Queries ingestion processing queues and database summary counts."""
        return self._safe_request("GET", "/api/stats")

    def get_backup_info(self) -> Dict[str, Any]:
        """Queries underlying hardware parameters and system configuration summaries."""
        return self._safe_request("GET", "/api/service-info")

    def request_restore(self, path: str, version: int) -> Dict[str, Any]:
        """Pushes an execution command targeting a clean historic path reference."""
        payload = {"path": path, "version": version}
        return self._safe_request("POST", "/api/restore", json=payload)
    
    # services/vm_client.py

    def get_backup_catalog(self) -> Dict[str, Any]:
        """Retrieves backup catalog inventory from Backup VM."""
        return self._safe_request(
            "GET",
            "/api/catalog"
        )
    def trigger_backup_deletion(self, storage_path: str) -> Dict[str, Any]:
        """
        Requests Backup VM agent to delete a stored backup object.
        """

        payload = {
            "storage_path": storage_path
        }

        return self._safe_request(
            "DELETE",
            "/api/backups/delete",
            json=payload
        )


class QuarantineClient(BaseEngineClient):
    """
    Interfaces with Quarantine VM isolation and recovery operations.
    """

    def __init__(self):

        url = getattr(
            settings,
            "QUARANTINE_AGENT_URL",
            "http://127.0.0.1:8003"
        )

        super().__init__(url)


    def _headers(self):

        return {
            "X-API-Key": settings.AGENT_API_KEY
        }


    def get_quarantine_files(self):

        """
        Retrieves quarantined files.
        """

        return self._safe_request(
            "GET",
            "/api/quarantine",
            headers=self._headers()
        )


    def release_quarantine(
        self,
        filename: str
    ):

        """
        Releases a quarantined file back
        into backup inbox.
        """

        payload = {
            "filename": filename
        }


        return self._safe_request(
            "POST",
            "/api/quarantine/release",
            headers=self._headers(),
            json=payload
        )


    def purge_quarantine(
        self,
        filename: str
    ):

        """
        Permanently deletes a quarantined file.
        """

        payload = {
            "filename": filename
        }


        return self._safe_request(
            "POST",
            "/api/quarantine/purge",
            headers=self._headers(),
            json=payload
        )

    def purge_quarantine(
        self,
        sha256_hash: str
    ) -> Dict[str, Any]:
        """
        Permanently removes quarantined payload.
        """

        payload = {
            "sha256_hash": sha256_hash
        }

        return self._safe_request(
            "DELETE",
            "/api/quarantine/purge",
            json=payload
        )


# Global instantiated module operations interfaces
detection_client = DetectionClient()
backup_client = BackupClient()
quarantine_client = QuarantineClient()
