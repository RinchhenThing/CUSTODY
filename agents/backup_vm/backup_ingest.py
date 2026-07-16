import os
import time
import shutil
import hashlib
from backup_db import init_db, insert_file, get_latest_version

INBOX_DIR = "/mnt/backup_inbox"
BACKUP_ROOT = "/srv/backup_root"

def sha256sum(path, blocksize=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(blocksize), b""):
            h.update(chunk)
    return h.hexdigest()

def store_file(src_path):
    rel_path = os.path.relpath(src_path, INBOX_DIR)
    latest = get_latest_version(rel_path)
    new_version = latest + 1

    dest_dir = os.path.join(BACKUP_ROOT, rel_path)
    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, f"v{new_version}")

    shutil.copy2(src_path, dest_file)
    st = os.stat(dest_file)
    h = sha256sum(dest_file)
    insert_file(rel_path, new_version, h, st.st_size)
    print(f"[INGEST] Backed up: {rel_path} v{new_version}")

def process_inbox():
    for root, dirs, files in os.walk(INBOX_DIR):
        for f in files:
            path = os.path.join(root, f)
            try:
                store_file(path)
                os.remove(path)
            except Exception as e:
                print(f"[ERROR] Ingest failed for {path}: {e}")

if __name__ == "__main__":
    init_db()
    print("Backup ingest daemon is running... checking /mnt/backup_inbox")
    while True:
        process_inbox()
        time.sleep(5)
