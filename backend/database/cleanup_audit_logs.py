import sys
from pathlib import Path

# Add backend/ to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models.models import AuditLog

db = SessionLocal()

try:
    deleted = db.query(AuditLog).delete()
    db.commit()
    print(f"Deleted {deleted} audit log entries.")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
