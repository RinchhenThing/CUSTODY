from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Authentication Schemas ---
class LoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["password123"])

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None

# --- User Management Schemas ---
class UserBase(BaseModel):
    username: str
    role_id: int
    is_active: bool = True
    is_locked: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

class PasswordResetRequest(BaseModel):
    new_password: str

class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    role_id: int
    is_active: bool
    is_locked: bool
    created_at: datetime
    role: Optional[RoleResponse] = None

    class Config:
        from_attributes = True

# --- Backup Schemas ---
class BackupVersionResponse(BaseModel):
    id: int
    backup_file_id: int
    version_number: int
    file_size: int
    sha256_hash: str
    storage_path: str
    created_at: datetime

    class Config:
        from_attributes = True

class BackupFileResponse(BaseModel):
    id: int
    filename: str
    original_path: str
    created_at: datetime
    versions: List[BackupVersionResponse] = []

    class Config:
        from_attributes = True

# --- Restore Schemas ---
class RestoreRequestCreate(BaseModel):
    backup_version_id: int
    destination_path: str

class RestoreRequestReject(BaseModel):
    reason: str

class RestoreRequestResponse(BaseModel):
    id: int
    backup_version_id: int
    requested_by_id: int
    approved_by_id: Optional[int] = None
    status: str
    destination_path: str
    requested_at: datetime
    processed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True

# --- Quarantine & Detection Schemas ---
class QuarantineFileResponse(BaseModel):
    id: int
    filename: str
    sha256_hash: str
    size: int
    quarantine_path: str
    detected_reason: str
    status: str
    captured_at: datetime

    class Config:
        from_attributes = True

class QuarantineReleaseRequest(BaseModel):
    release_to_path: str

class DetectionLogResponse(BaseModel):
    id: int
    filename: str
    status: str
    details: Optional[str] = None
    scanned_at: datetime

    class Config:
        from_attributes = True

# --- Infrastructure Logs, System Health & Settings ---
class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user: str
    role: str
    action: str
    target: str
    ip_address: str
    status: str

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class VMHealthResponse(BaseModel):
    vm_name: str
    status: str
    last_checked_at: datetime

    class Config:
        from_attributes = True

class DashboardSummaryResponse(BaseModel):
    total_backups: int
    active_quarantine_count: int
    critical_alerts: int
    system_status: str

class SettingUpdate(BaseModel):
    value: str