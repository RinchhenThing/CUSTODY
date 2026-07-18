"""
Quarantine Sandbox Router
Tracks isolated payloads and provides administrative release/purge controls.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from database import get_db
from models.models import QuarantineFile
from schemas.schemas import (
    QuarantineFileResponse,
    QuarantineReleaseRequest
)
from dependencies import require_permission
from services.vm_client import quarantine_client


router = APIRouter(
    prefix="/quarantine",
    tags=["Quarantine Sandbox"]
)


@router.get(
    "",
    response_model=List[QuarantineFileResponse],
    dependencies=[require_permission("quarantine.view")]
)
def get_quarantine_files(
    db: Session = Depends(get_db)
):
    """
    Lists all suspicious or malicious objects
    locked in the sandbox environment.
    """

    return db.query(QuarantineFile).all()



@router.post(
    "/{file_id}/release",
    dependencies=[require_permission("quarantine.manage")]
)
def release_from_quarantine(
    file_id: int,
    payload: QuarantineReleaseRequest,
    db: Session = Depends(get_db)
):
    """
    Commands the Quarantine VM to safely
    extract and deploy an isolated object.
    """

    q_file = (
        db.query(QuarantineFile)
        .filter(
            QuarantineFile.id == file_id
        )
        .first()
    )


    if not q_file or q_file.status != "ISOLATED":
        raise HTTPException(
            status_code=400,
            detail="Target file not found or already processed"
        )


    agent_call = quarantine_client.release_quarantine(
        q_file.sha256_hash,
        payload.release_to_path
    )


    if agent_call.get("status") != "ONLINE":
        raise HTTPException(
            status_code=502,
            detail="Quarantine VM Agent communication failure"
        )


    q_file.status = "RELEASED"
    db.commit()


    return {
        "status": "SUCCESS",
        "message": "Asset safely extracted and restored"
    }



@router.delete(
    "/{file_id}/purge",
    dependencies=[require_permission("quarantine.manage")]
)
def purge_malicious_payload(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    Permanently deletes a confirmed malicious
    binary payload from isolated storage.
    """

    q_file = (
        db.query(QuarantineFile)
        .filter(
            QuarantineFile.id == file_id
        )
        .first()
    )


    if not q_file:
        raise HTTPException(
            status_code=404,
            detail="Target file not found"
        )


    agent_call = quarantine_client.purge_quarantine(
        q_file.sha256_hash
    )


    if agent_call.get("status") != "ONLINE":
        raise HTTPException(
            status_code=502,
            detail="Quarantine VM Agent failure during purge operation"
        )


    q_file.status = "DELETED"
    db.commit()


    return {
        "status": "SUCCESS",
        "message": "Threat payload permanently eliminated from sandbox storage"
    }
