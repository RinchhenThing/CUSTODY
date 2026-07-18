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
from services.vm_client import backup_client
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
        raise HTTPException(status_code=404, detail="Target backup version not found")
        
    req = RestoreRequest(
        backup_version_id=payload.backup_version_id,
        requested_by_id=current_user.id,
        destination_path=payload.destination_path,  # Fixed missing required field constraint
        status="PENDING"
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.post("/requests/{request_id}/approve", response_model=RestoreRequestResponse, dependencies=[require_permission("restore.approve")])
def approve_restore(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Signs off a pending restoration request, instructing replication engines to execute recovery."""
    req = db.query(RestoreRequest).filter(RestoreRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Restore request not found")
        
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request already processed. Status: {req.status}")
        
    version = db.query(BackupVersion).filter(BackupVersion.id == req.backup_version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Associated backup metadata file missing")

    # Defensive validation step preventing potential internal AttributeError crashes
    if not version.backup_file:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backup file metadata reference is missing"
        )

    # Connect to the refactored, type-safe backup microservice endpoint
    agent_reply = backup_client.request_restore(
        path=version.backup_file.filename,
        version=int(version.version_number)
    )
    
    if agent_reply.get("status") == "OFFLINE":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Backup engine unreachable: {agent_reply.get('error')}"
        )
        
    if agent_reply.get("status") == "DEGRADED":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backup engine execution error: {agent_reply.get('error')}"
        )
        
    # Updated to COMPLETED since execution succeeded synchronously over the network
    req.status = "COMPLETED"
    req.approved_by_id = current_user.id
    req.processed_at = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(req)
    return req


@router.post("/requests/{request_id}/reject", response_model=RestoreRequestResponse, dependencies=[require_permission("restore.approve")])
def reject_restore(request_id: int, payload: RestoreRequestReject, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Rejects the recovery configuration and locks the execution track."""
    req = db.query(RestoreRequest).filter(RestoreRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Restore request not found")
        
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")
        
    req.status = "REJECTED"
    req.approved_by_id = current_user.id
    req.processed_at = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(req)
    return req
