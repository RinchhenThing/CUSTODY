"""
Infrastructure Health Router
Provides health status of connected VM agents.
"""

from fastapi import APIRouter
import datetime

from services.vm_client import (
    detection_client,
    backup_client,
    quarantine_client
)


router = APIRouter(
    prefix="/health",
    tags=["Infrastructure Health Tracker"]
)


@router.get("/vms")
def aggregate_infrastructure_health():
    """
    Queries backend service nodes and builds
    an infrastructure health map.
    """

    return {
        "Detection_VM": detection_client.get_detection_health(),
        "Backup_VM": backup_client.get_backup_health(),
        "Quarantine_VM": quarantine_client._safe_request(
            "GET",
            "/api/health"
        ),
        "timestamp": datetime.datetime.utcnow()
    }
