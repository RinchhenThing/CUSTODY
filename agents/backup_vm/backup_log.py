import os
import hashlib
import backup_db


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def record_backup(root_source, full_path):
    rel_path = os.path.relpath(full_path, root_source)
    size = os.path.getsize(full_path)
    digest = sha256_file(full_path)


    latest = backup_db.get_latest_version(rel_path)
    new_version = latest + 1


    backup_db.insert_file(
        rel_path=rel_path,
        version=new_version,
        sha256=digest,
        size=size,
    )


SOURCE_DIR = "/var/backups"


for root, dirs, files in os.walk(SOURCE_DIR):
    for name in files:
        full_path = os.path.join(root, name)
        record_backup(SOURCE_DIR, full_path)
