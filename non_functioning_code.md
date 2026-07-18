# Non-functioning and incomplete code review

This is a static review of directly observable failures and incomplete integrations. It does not claim that every untested path is broken. No code was changed during this review.

## Confirmed syntax failure

| Location | Finding | Effect |
| --- | --- | --- |
| `agents/backup_vm/app.broken.py:69` | Missing comma after `user=session["user"]` in `render_template(...)`. | The file cannot be imported or run. |
| `agents/backup_vm/app.broken.py:91` | Missing closing `)` in `int(request.form["version"]`. | The file cannot be imported or run. |

All other project Python files, excluding the repository's `venv/` and this intentionally named broken file, pass `py_compile`. The backend was not started because the current environment does not have `uvicorn` installed; install `backend/requirements.txt` to perform runtime testing.

## Gateway-to-agent API contracts do not match

`backend/services/vm_client.py` is the client used by all gateway routers, but it does not match the FastAPI agent routes in this repository.

| Gateway call | Gateway expectation | Implemented agent route | Result |
| --- | --- | --- | --- |
| VM health | `GET {agent}/api/health` | Detection, Backup, and Quarantine expose `GET /health`. No Production agent exists. | Health dashboard reports agents degraded/offline even when those three agents are running. |
| Scheduled scan | `POST {detection}/api/scan/trigger` | This path exists in `detection_agent.py`, but requires `X-API-Key`. | The gateway scheduler sends no API key and receives a validation/auth failure every 30 seconds. |
| Backup purge | `POST {backup}/api/storage/delete` with `{path}` | `backup_agent.py` has no deletion route. | `DELETE /api/backups/versions/{id}` cannot remove the underlying backup file. |
| Restore execution | `POST {backup}/api/restore/execute` with SHA-256, storage path, destination | Backup agent exposes `POST /restore` with `rel_path` and integer `version`; its restore function does not accept/use the requested destination override. | Approving a restore cannot execute against the supplied backup agent. |
| Quarantine release | `POST {quarantine}/api/quarantine/release` with `sha256` | Quarantine agent exposes `POST /release` with `filename`. | Gateway release requests fail. |
| Quarantine purge | `DELETE {quarantine}/api/quarantine/purge/{sha256}` | Quarantine agent exposes `DELETE /files/{filename}`. | Gateway purge requests fail. |
| Agent auth | Gateway client sends no `X-API-Key` on any call. | Most operational agent routes require that header. | Operational agent calls fail even where the URL otherwise matches. |

The unused alternative client at `agents/detection_vm/vm_client.py` also does not resolve this: it calls a non-existent detection `/scan-directory` path and sends `version: null` to the backup restore endpoint, whose schema requires an integer.

## Missing synchronization between the gateway and agent data

- The gateway has read-only backup routes plus version deletion, but no route or background job creates `BackupFile` or `BackupVersion` records from the backup agent. Consequently, the gateway backup list, restore selector, and dashboard backup total will stay empty unless database rows are inserted outside this codebase.
- The detection and quarantine agents only handle files. They do not create gateway `QuarantineFile`, `DetectionLog`, or `Notification` records. Therefore the quarantine console and unread-alert statistic have no implemented feed.
- `Notification` has a model and the dashboard counts unread notifications, but `backend/routers/notifications.py` is empty and no code creates notifications.
- No Production VM agent is included, although the gateway config and health matrix expect one at port `8001`.

## Authentication and session defects

| Location | Finding | Effect |
| --- | --- | --- |
| `backend/schemas/schemas.py` / `backend/routers/auth.py` | `LogoutRequest` defines `refresh_token`, but the logout handler accesses `payload.token`. | The console sends `{ token: accessToken }`, which does not satisfy the request schema; a correctly shaped request would later raise an attribute error. Logout is non-functional server-side. |
| `backend/routers/auth.py` | Login stores the access token in the sessions table but logout is designed around a refresh token. | Even after correcting the field mismatch, token invalidation semantics are inconsistent. |

## Backup and detection implementation issues

- `agents/backup_vm/backup_log.py` runs a full `/var/backups` walk as soon as it is imported, does not call `init_db()`, and only records metadata. It does not copy files into `BACKUP_ROOT`, so its entries cannot be restored by `restore.py`.
- `agents/backup_vm/app.py` is an older Flask interface. It refers to `dashboard.html`, `login.html`, and `backups.html`, but no Flask template directory or those templates are present in the repository. Its `/backups` data is hard-coded and `/restore_request` only prints a message. It is not integrated with the FastAPI gateway.
- `agents/detection_vm/detector_watchdog.py` processes both create and modify events. Because routing copies instead of moves the source, a single file can be copied repeatedly and create repeated backup versions or quarantine copies.
- `agents/detection_vm/detection_agent.py` tracks processed files by path only. A changed file at an already-seen path will not be rescanned during normal scheduled scans.

## Audit logging contradicts its stated purpose

- `backend/app.py` starts `cleanup_audit_logs_task`, which deletes **all** audit log records every 24 hours. This conflicts with the README and log router description of an immutable audit trail.
- The audit middleware excludes login and health requests but logs anonymous static-file requests and other unauthenticated traffic, so the audit view can accumulate non-operator asset requests.

## Recommended order of repair

1. Choose and document one API contract for every agent, including base paths, payloads, response shapes, and API-key handling; then make the gateway client and agents conform to it.
2. Implement the missing ingestion/status synchronization so gateway database records reflect agent operations.
3. Correct logout request/token handling and add runtime API tests for login, logout, RBAC, and each agent-backed operation.
4. Decide whether audit retention should be immutable/retained or purged by policy, then implement that stated policy.
5. Remove, quarantine, or clearly label the legacy Flask and `app.broken.py` prototypes so they are not mistaken for supported services.
