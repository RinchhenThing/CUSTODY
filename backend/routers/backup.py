"""
Backup Management Router
Tracks secure version storage records and cryptographic file hashes.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from database import get_db
from models.models import BackupFile, BackupVersion
from schemas.schemas import BackupFileResponse, BackupVersionResponse
from dependencies import require_permission
from services.vm_client import backup_client


router = APIRouter(
    prefix="/backups",
    tags=["Backup Management"]
)


@router.get(
    "",
    response_model=List[BackupFileResponse],
    dependencies=[require_permission("backups.view")]
)
def list_backups(db: Session = Depends(get_db)):
    """
    Retrieves all tracked production paths
    and their associated integrity versions.
    """
    return db.query(BackupFile).all()


@router.get(
    "/{file_id}/versions",
    response_model=List[BackupVersionResponse],
    dependencies=[require_permission("backups.view")]
)
def get_file_versions(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    Fetches the cryptographic timeline/history
    for a targeted file entry.
    """

    versions = (
        db.query(BackupVersion)
        .filter(
            BackupVersion.backup_file_id == file_id
        )
        .all()
    )

    if not versions:
        raise HTTPException(
            status_code=404,
            detail="No backup versions found for this asset"
        )

    return versions


@router.delete(
    "/versions/{version_id}",
    dependencies=[require_permission("backups.delete")]
)
def purge_backup_version(
    version_id: int,
    db: Session = Depends(get_db)
):
    """
    Removes a specific backup version entry
    and requests deletion from Backup VM.
    """

    version = (
        db.query(BackupVersion)
        .filter(
            BackupVersion.id == version_id
        )
        .first()
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail="Targeted backup version not found"
        )


    # Ask Backup VM agent to remove physical backup data
    agent_call = backup_client.trigger_backup_deletion(
        version.storage_path
    )


    if agent_call.get("status") == "OFFLINE":
        raise HTTPException(
            status_code=503,
            detail="Backup VM Agent is offline. Purge aborted."
        )


    # Remove database record after successful agent communication
    db.delete(version)
    db.commit()


    return {
        "status": "SUCCESS",
        "message": "Backup version purged from database and disk storage"
    }
