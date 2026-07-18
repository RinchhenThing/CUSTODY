# CUSTODY project overview

## Purpose

CUSTODY is a ransomware-resilient backup-orchestration prototype. It presents a browser console for backup versions, restore approvals, quarantined files, infrastructure health, users, settings, and audit records. The intended security model is to scan files outside production, store verified backup versions, require an approved restore request, and retain an audit trail.

## Main components

| Area | Location | Responsibility |
| --- | --- | --- |
| Gateway API | `backend/` | FastAPI application, SQLite persistence, JWT authentication, RBAC, audit middleware, and API routes under `/api`. |
| Web console | `dashboard/` | Static vanilla HTML/CSS/JavaScript single-page console. It calls the gateway through `dashboard/js/api.js`. |
| Detection agent | `agents/detection_vm/` | Classifies files using extension and entropy rules, then copies clean files to the backup inbox or suspicious files to quarantine. |
| Backup agent | `agents/backup_vm/` | Stores versioned copies, records SHA-256 hashes in an agent-local SQLite database, and restores verified copies. |
| Quarantine agent | `agents/quranatine_agent/` | Lists, releases, and deletes files held in the quarantine directory. The directory name is intentionally spelled `quranatine_agent` in this repository. |

## Intended workflow

```text
Production files
  -> Detection agent scan
     -> clean: backup inbox -> Backup agent version store
     -> suspicious/malicious: quarantine directory -> Quarantine agent

Console -> FastAPI gateway -> VM-agent API
Console <- FastAPI gateway <- gateway SQLite records and agent health
```

The gateway keeps its own records for users, roles, backup metadata, restore requests, quarantine metadata, notifications, settings, and audit logs. The backup agent separately keeps `agents/backup_vm/meta.db` for physical backup versions.

## Technology

- Backend: Python, FastAPI, SQLAlchemy, SQLite, JWT (`python-jose`), `passlib`, `APScheduler`, and `requests`.
- Frontend: plain HTML, CSS, and browser JavaScript; no Node.js build or package install is expected.
- Agents: FastAPI-based detection, backup, and quarantine services. There are also older Flask/prototype scripts in the backup-agent directory.

## Entry points

- Gateway: `backend/app.py`, normally served on `127.0.0.1:8000`.
- Detection agent: `agents/detection_vm/detection_agent.py`, documented to run on port `8002`.
- Backup agent: `agents/backup_vm/backup_agent.py`, documented to run on port `8003`.
- Quarantine agent: `agents/quranatine_agent/quarantine_agent.py`, documented to run on port `8004`.
- Console: served as static files by the gateway from `dashboard/`.

## Authentication and roles

The gateway seeds Admin, Operator, and Auditor roles on startup, plus demo accounts `admin`, `operator`, and `auditor` with password `password123`. The console stores JWT access and refresh tokens in browser `localStorage` and uses the access-token claims only for client-side display gating; backend permissions remain the enforcement point.

## Data and configuration

- Gateway SQLite path: `backend/database/backup.db` when launched from `backend/`.
- Backup-agent SQLite path: `agents/backup_vm/meta.db`.
- Default gateway agent URLs are configured in `backend/config.py` and point to localhost ports `8001` through `8004`.
- Agent API-key defaults are read from `AGENT_API_KEY`; production deployment should supply real environment values instead of defaults.

## Current implementation status

The console and gateway route structure are substantially built, but the VM-agent contracts and gateway metadata ingestion are incomplete/inconsistent. As a result, agent-backed health, deletion, restore, quarantine operations, and live console data need integration work before the project can function end to end. See [non_functioning_code.md](non_functioning_code.md) for the static-review findings.

## Review scope

This document reflects a read-only code review performed on 2026-07-17. No application source, configuration, database, or runtime behavior was changed.
