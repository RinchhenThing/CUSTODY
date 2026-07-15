"""
Ransomware-Resilient Backup Orchestrator Gateway Core
Main application initialization, middleware routing, CORS bindings, and database seeding.
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from config import settings

# Import the structural middleware layer
from middleware.audit import AuditLogMiddleware

# Import modular api endpoint routers
from routers import (
    auth, users, settings as settings_router, 
    backup, restore, quarantine, dashboard, health, logs
)
from models.models import Role, Permission, User, SystemSetting
from auth.security import get_password_hash

from fastapi.staticfiles import StaticFiles

# Build database tables dynamically on application boot
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS to allow frontend index.html cross-origin communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach the global compliance audit logging middleware
app.add_middleware(AuditLogMiddleware)

# Wire up the endpoint routing tables strictly adhering to API specs
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(settings_router.router, prefix=settings.API_V1_STR)
app.include_router(backup.router, prefix=settings.API_V1_STR)
app.include_router(restore.router, prefix=settings.API_V1_STR)
app.include_router(quarantine.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(logs.router, prefix=settings.API_V1_STR)

# Mount the frontend dashboard workspace directory cleanly
app.mount("/", StaticFiles(directory="../dashboard", html=True), name="frontend")

@app.on_event("startup")
def seed_system_data():
    """Seeds structural database records, access configurations, and administrative profiles."""
    db = SessionLocal()
    try:
        # 1. Seed System Settings thresholds if empty
        default_settings = {
            "SCAN_DELAY_SECONDS": "5",
            "MAX_VERSION_COUNT": "10",
            "ALERT_ON_SUSPICIOUS": "true",
            "QUARANTINE_RETENTION_DAYS": "30"
        }
        for key, value in default_settings.items():
            if not db.query(SystemSetting).filter(SystemSetting.key == key).first():
                db.add(SystemSetting(key=key, value=value, description=f"System {key} configuration value."))

        # 2. Seed Granular Permissions Matrix
        permissions_list = [
            "backups.view", "backups.delete",
            "restore.view", "restore.request", "restore.approve",
            "quarantine.view", "quarantine.manage",
            "users.view", "users.create", "users.edit", "users.lock",
            "settings.view", "settings.edit",
            "logs.view"
        ]
        permission_objects = {}
        for perm_name in permissions_list:
            perm = db.query(Permission).filter(Permission.name == perm_name).first()
            if not perm:
                perm = Permission(name=perm_name, description=f"Allows role to execute {perm_name}")
                db.add(perm)
            permission_objects[perm_name] = perm
        db.commit()

        # 3. Build Standard Roles and Bind Permissions Maps
        roles_spec = {
            "Admin": permissions_list, # Admin automatically inherits all system capabilities
            "Operator": ["backups.view", "restore.view", "restore.request", "quarantine.view", "logs.view"],
            "Auditor": ["backups.view", "restore.view", "quarantine.view", "logs.view", "settings.view"]
        }
        
        role_objects = {}
        for role_name, allowed_perms in roles_spec.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(name=role_name, description=f"Standard structural {role_name} workspace layout.")
                db.add(role)
                db.flush()
            
            # Re-map permissions list relationships into association table
            role.permissions = [permission_objects[p] for p in allowed_perms]
            role_objects[role_name] = role
        db.commit()

        # 4. Create Initial Admin User Account
        if not db.query(User).filter(User.username == "admin").first():
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("password123"), # Dynamic frontend test seed
                role_id=role_objects["Admin"].id,
                is_active=True,
                is_locked=False
            )
            db.add(admin_user)
            
        # Create Initial Operator User Account
        if not db.query(User).filter(User.username == "operator").first():
            operator_user = User(
                username="operator",
                hashed_password=get_password_hash("password123"),
                role_id=role_objects["Operator"].id,
                is_active=True,
                is_locked=False
            )
            db.add(operator_user)
            
        # Create Initial Auditor User Account
        if not db.query(User).filter(User.username == "auditor").first():
            auditor_user = User(
                username="auditor",
                hashed_password=get_password_hash("password123"),
                role_id=role_objects["Auditor"].id,
                is_active=True,
                is_locked=False
            )
            db.add(auditor_user)
            
        db.commit()
        print("[+] Application database tables created and structural system seed data successfully deployed.")
    except Exception as e:
        db.rollback()
        print(f"[-] Database initialization failure: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # Launch application inside local development loop matching static assets configuration
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)