from pathlib import Path
from datetime import datetime

from models.models import BackupFile, BackupVersion
from services.vm_client import backup_client


def sync_backup_catalog(db):
    """
    Synchronize backup inventory from the Backup VM catalog.
    The Backup VM is treated as the source of truth.
    """

    response = backup_client.get_backup_catalog()

    if response["status"] != "ONLINE":
        return {
            "files": 0,
            "versions": 0,
            "error": response["error"]
        }

    catalog = response["data"] or []

    try:
        # Clear existing inventory
        db.query(BackupVersion).delete()
        db.query(BackupFile).delete()
        db.commit()

        file_map = {}

        files_created = 0
        versions_created = 0

        for row in catalog:
            path = row["rel_path"]

            if path not in file_map:
                backup_file = BackupFile(
                    filename=Path(path).name,
                    original_path=path
                )

                db.add(backup_file)
                db.flush()

                file_map[path] = backup_file
                files_created += 1

            backup_file = file_map[path]

            created_at = datetime.utcnow()

            if row.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(
                        row["created_at"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            version = BackupVersion(
                backup_file_id=backup_file.id,
                version_number=row["version"],
                file_size=row["size"],
                sha256_hash=row["sha256"],
                storage_path=path,
                created_at=created_at
            )

            db.add(version)
            versions_created += 1

        db.commit()

        return {
            "files": files_created,
            "versions": versions_created
        }

    except Exception:
        db.rollback()
        raise
