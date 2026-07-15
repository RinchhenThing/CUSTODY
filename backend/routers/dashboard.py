from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.models import BackupFile, QuarantineFile, Notification
from schemas.schemas import DashboardSummaryResponse
from dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard Interface"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Compiles core workspace metrics for display on the SOC dashboard dashboard frame."""
    total_backups = db.query(BackupFile).count()
    active_quarantine = db.query(QuarantineFile).filter(QuarantineFile.status == "ISOLATED").count()
    critical_alerts = db.query(Notification).filter(Notification.is_read == False).count()
    
    return {
        "total_backups": total_backups,
        "active_quarantine_count": active_quarantine,
        "critical_alerts": critical_alerts,
        "system_status": "SECURE" if active_quarantine == 0 else "WARNING"
    }