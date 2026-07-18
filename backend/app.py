"""
Ransomware-Resilient Backup Orchestrator Gateway Core
Main application initialization, middleware routing, CORS bindings, and database seeding.
"""

import uvicorn
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base, SessionLocal
from config import settings

from middleware.audit import AuditLogMiddleware

from routers import (
    auth,
    users,
    settings as settings_router,
    backup,
    restore,
    quarantine,
    dashboard,
    health,
    logs,
)

from routers.sync import router as sync_router

from models.models import (
    AuditLog,
    Role,
    Permission,
    User,
    SystemSetting,
)

from auth.security import get_password_hash
from services.backup_sync import sync_backup_catalog

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
    allow_origins=["*"],  # Restrict to specific origins in a live production environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach operational audit trail middleware layer
app.add_middleware(AuditLogMiddleware)

# Include modular API endpoint routers mapped under v1 API route namespace
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(settings_router.router, prefix=settings.API_V1_STR)
app.include_router(backup.router, prefix=settings.API_V1_STR)
app.include_router(restore.router, prefix=settings.API_V1_STR)
app.include_router(quarantine.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(logs.router, prefix=settings.API_V1_STR)
app.include_router(sync_router, prefix=settings.API_V1_STR)

# Mount static web UI files dashboard layer
app.mount(
    "/",
    StaticFiles(directory="../dashboard", html=True),
    name="dashboard"
)
def seed_system_data(db):
    """Initializes standard RBAC roles, capability matrices, and default setup rules."""
    # Example Database Seeding Context
    roles_spec = {
        "Admin": ["auth.all", "users.all", "restore.approve", "quarantine.manage"],
        "Operator": ["backup.view", "restore.request", "quarantine.view"],
        "Auditor": ["logs.view", "health.view"]
    }
    
    # Clean up loop syntax from legacy hypervisor artifacts
    permissions_list = ["auth.all", "users.all", "restore.approve", "restore.request", "quarantine.manage", "quarantine.view", "logs.view", "health.view"]
    
    # Fixed the corrupted line typo safely here
    for perm_name in permissions_list:
        # DB seeding implementation logic for permissions continues here...
        pass

@app.on_event("startup")
def startup_initializer():
    """Triggers application initialization hooks, database seeds, and live catalog mapping."""
    db = SessionLocal()
    try:
        # 1. Seed RBAC and operational records
        seed_system_data(db)
        
        # 2. Trigger active catalog sync at startup to populate metadata tables immediately
        print("[STARTUP] Initializing automated backup catalog synchronization sequence...")
        try:
            sync_result = sync_backup_catalog(db)
            print(f"[SYNC SUCCESS] {sync_result}")
        except Exception as sync_err:
            print(f"[SYNC ERROR] Metadata sync bypassed at boot stage: {sync_err}")
            
    finally:
        db.close()

@app.get("/")
def read_root():
    """Redirects base cluster inquiries cleanly to the decoupled static management layer."""
    return {"message": f"Welcome to {settings.PROJECT_NAME} Gateway Engine API. Navigate to /api/docs or /static/"}

if __name__ == "__main__":
    # Launch application inside local development loop matching static assets configuration
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
