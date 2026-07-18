# Plan: Fix the empty backup inbox / missing dashboard backup data

## Goal
Make the backup-inbox flow work end to end so files routed by the Detection VM appear in the dashboard as backup records instead of disappearing or staying invisible.

## Root cause summary
The current system has a split workflow:
- Detection VM copies files into the shared backup inbox.
- Backup ingest processes files from that inbox.
- The dashboard, however, reads backup data from the gateway database, and that database is not being populated by the agent flow.

That means the inbox may receive files, but the dashboard still shows nothing because no gateway backup records were created.

## Work items

### 1. Make the agent flow reliable
- Confirm the shared directories exist and are writable:
  - /mnt/backup_inbox
  - /mnt/quarantine
  - /mnt/prod/Prod_Files (or the detection watch directory)
- Ensure the Detection VM routes files to the correct shared inbox path.
- Ensure the Backup VM ingest process runs and actually stores files.
- Verify that the backup agent is using the correct paths and permissions.

### 2. Bridge agent output into gateway database records
- Add code to ingest backup results into the gateway database.
- Create or update BackupFile and BackupVersion rows when files are successfully stored by the backup agent.
- Ensure the dashboard reads these records instead of relying on an implicit side effect.

### 3. Fix the API contract mismatch
- Align the gateway client and the agent endpoints so they use the same paths, payloads, auth headers, and response formats.
- Make sure the gateway sends X-API-Key where required.
- Check that the backup agent routes and the gateway client use the same request structure.

### 4. Verify the dashboard data path
- Confirm the dashboard endpoint /api/dashboard/summary and /api/backups are returning data from the database.
- After a scan and backup ingest run, verify that backup rows appear in the database and are visible in the UI.

### 5. Add basic runtime verification
- Run the detection and backup agents.
- Trigger a test file through the detection flow.
- Confirm that:
  - the file reaches the backup inbox,
  - the backup agent stores it,
  - a backup record is created in the gateway DB,
  - the dashboard shows the backup entry.

## Suggested implementation order
1. Inspect and fix directory paths and permissions.
2. Make the backup agent ingest flow work reliably.
3. Add gateway DB ingestion for backup events.
4. Test with a sample file end to end.
5. Fix any remaining API/auth mismatch.

## Success criteria
- A file scanned by the Detection VM ends up in the backup flow.
- A corresponding backup record appears in the gateway database.
- The dashboard shows that backup entry under the backup section.
