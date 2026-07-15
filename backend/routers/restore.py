"""
Restore Engine Router
Governs multi-role authorization approvals and secure data recovery pipelines.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from models.models import RestoreRequest, BackupVersion, User
from schemas.schemas import RestoreRequestResponse, RestoreRequestCreate, RestoreRequestReject
from dependencies import require_permission, get_current_user
from services.vm_client import vm_client
import datetime

router = APIRouter(prefix="/restore", tags=["Restore Engine"])

@router.get("/requests", response_model=List[RestoreRequestResponse], dependencies=[require_permission("restore.view")])
def list_restore_requests(db: Session = Depends(get_db)):
    """Pulls full audit queue of pending, authorized, or rejected restoration tasks."""
    return db.query(RestoreRequest).all()

@router.post("/requests", response_model=RestoreRequestResponse, dependencies=[require_permission("restore.request")])
def create_restore_request(payload: RestoreRequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Submits a new recovery request to the authorization queue."""
    version = db.query(BackupVersion).filter(BackupVersion.id == payload.backup_version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Selected backup version invalid")
        
    new_request = RestoreRequest(
        backup_version_id=payload.backup_version_id,
        requested_by_id=current_user.id,
        destination_path=payload.destination_path,
        status="PENDING"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

@router.post("/requests/{request_id}/approve", dependencies=[require_permission("restore.approve")])
def approve_restore(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Approves a recovery workflow, initiating inter-VM integrity verification and transport."""
    req = db.query(RestoreRequest).filter(RestoreRequest.id == request_id).first()
    if not req or req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Request not found or not in a mutable PENDING state")
        
    version = db.query(BackupVersion).filter(BackupVersion.id == req.backup_version_id).first()
    
    # Issue the execution command to the Backup VM agent
    agent_reply = vm_client.request_restore(
        sha256_hash=version.sha256_hash,
        storage_path=version.storage_path,
        destination_path=req.destination_path
    )
    
    if agent_reply["status"] != "ONLINE":
        req.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=502, detail=f"VM Ingestion Layer Error: {agent_reply['error']}")
        
    req.status = "COMPLETED"
    req.approved_by_id = current_user.id
    req.processed_at = datetime.datetime.utcnow()
    db.commit()
    
    return {"status": "SUCCESS", "message": "Integrity verified. Asset successfully restored to production."}

@router.post("/requests/{request_id}/reject", dependencies=[require_permission("restore.approve")])
def reject_restore(request_id: int, payload: RestoreRequestReject, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Denies a restoration request and documents the audit reason."""
    req = db.query(RestoreRequest).filter(RestoreRequest.id == request_id).first()
    if not req or req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Request not found or not mutable")
        
    req.status = "REJECTED"
    req.approved_by_id = current_user.id
    req.rejection_reason = payload.reason
    req.processed_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "SUCCESS", "message": "Restoration request denied"}