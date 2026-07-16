"""
vm_client.py
------------
The dashboard's "phone book + telephone" for talking to the VM agents.

Every function here makes an HTTP call to one of the agent services
(detection_agent.py, backup_agent.py, quarantine_agent.py) running on
their respective VMs. Nothing here touches files directly — it only
issues commands over the network and interprets the response.

Place this file alongside the FastAPI dashboard (e.g. next to app.py),
so routers like restore.py and a scheduler can import it:

    import vm_client
    vm_client.request_restore(...)
"""
import os
import httpx
from config import settings

# Shared secret sent on every call. Must match AGENT_API_KEY set on each VM.
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "CHANGE_ME_SHARED_SECRET")

DEFAULT_TIMEOUT = 10  # seconds


def _headers():
    return {"X-API-Key": AGENT_API_KEY}


def _post(base_url: str, path: str, json_body: dict | None = None):
    try:
        resp = httpx.post(f"{base_url}{path}", json=json_body, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return {"status": "ONLINE", **resp.json()}
    except httpx.TimeoutException:
        return {"status": "OFFLINE", "error": f"Timed out calling {base_url}{path}"}
    except httpx.ConnectError:
        return {"status": "OFFLINE", "error": f"Could not connect to {base_url}"}
    except httpx.HTTPStatusError as e:
        return {"status": "ERROR", "error": f"{e.response.status_code}: {e.response.text}"}


def _get(base_url: str, path: str, params: dict | None = None):
    try:
        resp = httpx.get(f"{base_url}{path}", params=params, headers=_headers(), timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return {"status": "ONLINE", "data": resp.json()}
    except httpx.TimeoutException:
        return {"status": "OFFLINE", "error": f"Timed out calling {base_url}{path}"}
    except httpx.ConnectError:
        return {"status": "OFFLINE", "error": f"Could not connect to {base_url}"}
    except httpx.HTTPStatusError as e:
        return {"status": "ERROR", "error": f"{e.response.status_code}: {e.response.text}"}


# --- Detection VM ---

def trigger_scan_cycle(force_rescan: bool = False):
    """Called on a timer by the dashboard's scheduler to sweep for new files."""
    return _post(settings.DETECTION_AGENT_URL, f"/scan-directory?force_rescan={str(force_rescan).lower()}")


def request_scan(path: str, auto_route: bool = True):
    """One-off scan of a specific file, e.g. triggered manually from the dashboard UI."""
    return _post(settings.DETECTION_AGENT_URL, "/scan", {"path": path, "auto_route": auto_route})


# --- Backup VM ---

def request_store(src_path: str):
    return _post(settings.BACKUP_AGENT_URL, "/store", {"src_path": src_path})


def request_restore(sha256_hash: str, storage_path: str, destination_path: str):
    return _post(settings.BACKUP_AGENT_URL, "/restore", {
        "rel_path": storage_path,
        "version": None,  # populate from your BackupVersion record if needed
        "destination_path": destination_path,
    })


def get_backup_versions(limit: int = 100):
    return _get(settings.BACKUP_AGENT_URL, "/versions", {"limit": limit})


# --- Quarantine VM ---

def list_quarantine_files():
    return _get(settings.QUARANTINE_AGENT_URL, "/files")


def release_from_quarantine(filename: str, destination_path: str):
    return _post(settings.QUARANTINE_AGENT_URL, "/release", {
        "filename": filename,
        "destination_path": destination_path,
    })


# --- Generic health check, used by the SystemHealth model ---

def check_vm_health(vm_name: str):
    urls = {
        "Detection": settings.DETECTION_AGENT_URL,
        "Backup": settings.BACKUP_AGENT_URL,
        "Quarantine": settings.QUARANTINE_AGENT_URL,
    }
    base_url = urls.get(vm_name)
    if not base_url:
        return {"status": "UNKNOWN", "error": f"No agent URL configured for {vm_name}"}
    return _get(base_url, "/health")
