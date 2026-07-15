from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from models.models import AuditLog
from schemas.schemas import AuditLogResponse
from dependencies import require_permission

router = APIRouter(prefix="/logs", tags=["Audit Core"])

@router.get("/audit", response_model=List[AuditLogResponse], dependencies=[require_permission("logs.view")])
def fetch_system_audit_trail(db: Session = Depends(get_db)):
    """Returns the immutable workspace event log for compliance reviews."""
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()