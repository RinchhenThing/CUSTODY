"""
Quarantine Sandbox Router

Dashboard interface for Quarantine VM Agent.

Architecture:

Dashboard
    |
    | X-API-Key
    |
Quarantine Agent
    |
    v
Quarantine Storage
"""


from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from dependencies import require_permission
from services.vm_client import quarantine_client


router = APIRouter(
    prefix="/quarantine",
    tags=["Quarantine Sandbox"]
)



@router.get(
    "",
    dependencies=[
        require_permission("quarantine.view")
    ]
)
def get_quarantine_files():

    """
    Retrieves live quarantine inventory
    from Quarantine VM.
    """


    agent_call = (
        quarantine_client
        .get_quarantine_files()
    )


    if agent_call.get("status") != "ONLINE":

        raise HTTPException(
            status_code=502,
            detail="Quarantine VM unavailable"
        )


    return agent_call.get(
        "data",
        []
    )



@router.post(
    "/release",
    dependencies=[
        require_permission("quarantine.manage")
    ]
)
def release_from_quarantine(
    payload: Dict[str, Any]
):

    """
    Release a quarantined file.
    
    Expected:
    {
        "filename": "qq.txt"
    }
    """


    filename = payload.get(
        "filename"
    )


    if not filename:

        raise HTTPException(
            status_code=400,
            detail="filename required"
        )


    agent_call = (
        quarantine_client
        .release_quarantine(
            filename
        )
    )


    if agent_call.get("status") != "ONLINE":

        raise HTTPException(
            status_code=502,
            detail="Quarantine VM release failed"
        )


    return {
        "status": "SUCCESS",
        "agent": agent_call
    }



@router.post(
    "/purge",
    dependencies=[
        require_permission("quarantine.manage")
    ]
)
def purge_malicious_payload(
    payload: Dict[str, Any]
):

    """
    Permanently delete quarantined file.

    Expected:

    {
        "filename":"qq.txt"
    }
    """


    filename = payload.get(
        "filename"
    )


    if not filename:

        raise HTTPException(
            status_code=400,
            detail="filename required"
        )


    agent_call = (
        quarantine_client
        .purge_quarantine(
            filename
        )
    )


    if agent_call.get("status") != "ONLINE":

        raise HTTPException(
            status_code=502,
            detail="Quarantine VM purge failed"
        )


    return {
        "status": "SUCCESS",
        "agent": agent_call
    }
