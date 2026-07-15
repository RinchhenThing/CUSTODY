from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
import datetime
from database import Base

# Association Table for Role-Permission mapping
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete="CASCADE"), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # Admin, Operator, Auditor
    description = Column(String, nullable=True)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g., "backup.restore"
    description = Column(String, nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    role = relationship("Role", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")

class BackupFile(Base):
    __tablename__ = "backup_files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    versions = relationship("BackupVersion", back_populates="backup_file", cascade="all, delete-orphan")

class BackupVersion(Base):
    __tablename__ = "backup_versions"
    id = Column(Integer, primary_key=True, index=True)
    backup_file_id = Column(Integer, ForeignKey("backup_files.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_size = Column(Integer, nullable=False) # in bytes
    sha256_hash = Column(String(64), nullable=False)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    backup_file = relationship("BackupFile", back_populates="versions")

class RestoreRequest(Base):
    __tablename__ = "restore_requests"
    id = Column(Integer, primary_key=True, index=True)
    backup_version_id = Column(Integer, ForeignKey("backup_versions.id"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED, COMPLETED, FAILED
    destination_path = Column(String, nullable=False)
    requested_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

    version = relationship("BackupVersion")
    requester = relationship("User", foreign_keys=[requested_by_id])
    approver = relationship("User", foreign_keys=[approved_by_id])

class QuarantineFile(Base):
    __tablename__ = "quarantine_files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    quarantine_path = Column(String, nullable=False)
    detected_reason = Column(String, nullable=False) # e.g., "Signature Match: Ransom.WannaCry"
    status = Column(String, default="ISOLATED") # ISOLATED, RELEASED, DELETED
    captured_at = Column(DateTime, default=datetime.datetime.utcnow)

class DetectionLog(Base):
    __tablename__ = "detection_logs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False) # CLEAN, SUSPICIOUS, MALICIOUS
    details = Column(String, nullable=True)
    scanned_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user = Column(String, nullable=False)
    role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    status = Column(String, nullable=False) # SUCCESS, FAILURE

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info") # info, warning, danger
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SystemHealth(Base):
    __tablename__ = "system_health"
    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String, nullable=False) # Production, Detection, Backup, Quarantine
    status = Column(String, nullable=False) # ONLINE, OFFLINE, DEGRADED
    last_checked_at = Column(DateTime, default=datetime.datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)