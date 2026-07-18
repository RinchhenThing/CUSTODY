from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.backup_sync import sync_backup_catalog

router = APIRouter(
    prefix="/sync",
    tags=["Synchronization"]
)


@router.post("/backup-catalog")
def sync_catalog(db: Session = Depends(get_db)):
    return sync_backup_catalog(db)
