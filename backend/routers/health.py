from fastapi import APIRouter
from services.vm_client import vm_client
import datetime

router = APIRouter(prefix="/health", tags=["Infrastructure Health Tracker"])

@router.get("/vms")
def aggregate_infrastructure_health():
    """Queries all four back-end hypervisor nodes to build an up-to-date health map."""
    return {
        "Production_VM": vm_client.get_production_health(),
        "Detection_VM": vm_client.get_detection_health(),
        "Backup_VM": vm_client.get_backup_health(),
        "Quarantine_VM": vm_client.get_quarantine_health(),
        "timestamp": datetime.datetime.utcnow()
    }