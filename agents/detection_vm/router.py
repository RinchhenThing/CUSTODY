# router.py
import os
import shutil
from analyzer import Verdict

QUARANTINE_DIR = "/mnt/quarantine"   # share to Quarantine VM
BACKUP_INBOX_DIR = "/mnt/backup_inbox"  # share to Backup VM

def safe_move(src, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.basename(src)
    dest = os.path.join(dest_dir, base)
    shutil.copy2(src, dest)  # keep original as "evidence"
    # optionally delete src after copy
    # os.remove(src)

def route_file(path, verdict: Verdict):
    if verdict in (Verdict.SUSPICIOUS, Verdict.MALICIOUS):
        safe_move(path, QUARANTINE_DIR)
    elif verdict == Verdict.CLEAN:
        safe_move(path, BACKUP_INBOX_DIR)
