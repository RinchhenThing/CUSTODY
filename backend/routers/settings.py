"""
Settings Management Router
Stores global threshold limits, scanning variables, and system configurations.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.models import SystemSetting
from schemas.schemas import SettingUpdate
from dependencies import require_permission

router = APIRouter(prefix="/settings", tags=["System Settings"])

@router.get("", dependencies=[require_permission("settings.view")])
def get_all_settings(db: Session = Depends(get_db)):
    """Pulls all key-value threshold criteria configured for the central gateway."""
    settings_list = db.query(SystemSetting).all()
    return {setting.key: setting.value for setting in settings_list}

@router.put("", dependencies=[require_permission("settings.edit")])
def update_setting(payload: dict, db: Session = Depends(get_db)):
    """Updates key parameters inside the SQLite parameters repository table."""
    for key, val in payload.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = str(val)
        else:
            new_setting = SystemSetting(key=key, value=str(val))
            db.add(new_setting)
    db.commit()
    return {"status": "SUCCESS", "message": "Global structural configurations updated"}