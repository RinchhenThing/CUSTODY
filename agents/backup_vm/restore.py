import os
import sqlite3
import hashlib
import shutil
from backup_db import DB_PATH

BACKUP_ROOT = "/srv/backup_root"
RESTORE_ROOT = "/srv/restore_area"

def sha256sum(path, blocksize=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(blocksize), b""):
            h.update(chunk)
    return h.hexdigest()

def restore_file(rel_path, version):
    """Verifies file integrity against DB record and restores if intact."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sha256 FROM files WHERE rel_path=? AND version=?", (rel_path, version))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise ValueError(f"No database records found for {rel_path} v{version}")

    expected_hash = row[0]
    src_file = os.path.join(BACKUP_ROOT, rel_path, f"v{version}")
    
    if not os.path.exists(src_file):
        raise FileNotFoundError(f"Underlying backup file is missing on disk: {src_file}")

    actual_hash = sha256sum(src_file)
    if actual_hash != expected_hash:
        raise ValueError("CRITICAL INTEGRITY FAILURE: Backup file hash mismatch! Possible disk tampering.")

    # Securely stage for restoration
    dest_dir = os.path.join(RESTORE_ROOT, os.path.dirname(rel_path))
    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, f"restored_v{version}_{os.path.basename(rel_path)}")
    
    shutil.copy2(src_file, dest_file)
    return dest_file
