# CUSTODY

**Ransomware-Resilient Backup Orchestrator — Gateway Console**

CUSTODY is the operator console for a backup orchestration system built to survive ransomware: every file version is hashed and tracked, suspicious payloads are isolated in a sandbox before they ever touch production, and restores require an explicit human approval step. This repo contains the frontend — a vanilla HTML/CSS/JS single-page console — wired to the FastAPI gateway.

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Demo accounts](#demo-accounts)
- [Roles & permissions](#roles--permissions)
- [Architecture](#architecture)
- [API reference](#api-reference)
- [Known gaps / assumptions](#known-gaps--assumptions)

---

## Features

- **Authentication** — JWT-based login/register, session persisted in `localStorage`, auto-redirect on expiry.
- **Overview** — live system stats (total backups, quarantine count, unread alerts, system status), hypervisor health summary, recent restore activity.
- **Backup vault** — every tracked file and its full version history, each version shown with its SHA-256 fingerprint, size, and capture date. Admins can purge individual versions.
- **Restore queue** — submit restore requests against a specific backup version; Admins/Operators with approval rights can approve (triggers VM-to-VM transport) or reject with a reason.
- **Quarantine sandbox** — isolated/suspicious payloads with detection reason, release-to-path workflow, and permanent purge.
- **Infrastructure health** — live reachability check across the four backend VM agents (Production, Detection, Backup, Quarantine).
- **User access (Admin only)** — create operators, lock/unlock accounts, reset passwords.
- **Audit log** — immutable, read-only feed of every authenticated request against the gateway.
- **System settings** — global thresholds (scan delay, max retained versions, quarantine retention, alerting), editable by Admins.
- Every section is gated client-side against the signed-in user's role, mirroring the backend's permission checks — the UI simply hides what a role can't do; the API is the actual enforcement layer.

## Tech stack

- **Frontend:** vanilla HTML/CSS/JS, no build step, no framework. Hash-based routing over a single-page shell (`index.html`).
- **Backend:** FastAPI + SQLAlchemy + SQLite, JWT auth (`python-jose`), bcrypt password hashing (`passlib`), served from the same origin via `StaticFiles`.
- **Fonts:** IBM Plex Sans (UI) / IBM Plex Mono (data, hashes, headers).

## Project structure

```
dashboard/
├── css/
│   ├── style.css        # design tokens, reset, base primitives
│   ├── components.css   # buttons, badges, tables, modals, toasts
│   ├── dashboard.css    # console shell — sidebar, topbar, grid
│   ├── login.css        # auth shell + hero
│   └── register.css     # role picker, password strength
├── js/
│   ├── api.js            # fetch wrapper, JWT storage, all endpoint calls, role/permission matrix
│   ├── components.js      # toasts, modals, formatters, badge rendering
│   ├── auth.js            # login.html / register.html logic
│   ├── app.js              # dashboard shell — sidebar, routing, topbar
│   └── modules.js          # one render() function per console section
├── index.html            # console shell (requires auth)
├── login.html
└── register.html
```

## Getting started

CUSTODY is a static frontend meant to be served by the FastAPI backend directly.

1. Make sure the backend directory structure matches what `app.py` expects, with this folder mounted one level up:
   ```
   backend/
   ├── app.py
   ├── ...
   dashboard/          ← this folder
   ├── index.html
   ├── ...
   ```
2. From the backend directory, install dependencies and run:
   ```bash
   pip install -r requirements.txt   # fastapi, uvicorn, sqlalchemy, python-jose, passlib[bcrypt], pydantic-settings
   python app.py
   ```
3. Open **http://127.0.0.1:8000** — the FastAPI app serves `dashboard/index.html` (and `login.html` / `register.html`) directly from `/`, while the console talks to the API under `/api`.
4. Interactive API docs are available at **http://127.0.0.1:8000/api/docs**.

No build tooling, bundler, or `npm install` is required — the frontend is plain static assets.

## Demo accounts

Seeded automatically on first boot (`app.py` → `seed_system_data`):

| Username   | Password      | Role     |
|------------|---------------|----------|
| `admin`    | `password123` | Admin    |
| `operator` | `password123` | Operator |
| `auditor`  | `password123` | Auditor  |

The login page has one-click "Use" buttons for all three.

## Roles & permissions

Mirrors the permission matrix seeded server-side — the frontend uses this purely to decide what to render; the API enforces it independently on every request.

| Capability             | Admin | Operator | Auditor |
|-------------------------|:---:|:---:|:---:|
| View backups             | ✅ | ✅ | ✅ |
| Delete backup versions   | ✅ | — | — |
| View restore queue       | ✅ | ✅ | ✅ |
| Submit restore request   | ✅ | ✅ | — |
| Approve / reject restore | ✅ | — | — |
| View quarantine          | ✅ | ✅ | ✅ |
| Release / purge quarantine | ✅ | — | — |
| View users               | ✅ | — | — |
| Create / edit / lock users | ✅ | — | — |
| View settings            | ✅ | — | ✅ |
| Edit settings            | ✅ | — | — |
| View audit log           | ✅ | ✅ | ✅ |

Infrastructure health and the overview stats are visible to any authenticated user regardless of role.

## Architecture

```
 ┌──────────────┐        ┌───────────────────────┐        ┌──────────────────┐
 │  CUSTODY UI   │  /api  │   FastAPI Gateway      │        │  VM Agents        │
 │  (this repo)  │ ─────► │   auth · RBAC · audit  │ ─────► │  Production        │
 │  static HTML   │        │   SQLite (SQLAlchemy) │        │  Detection         │
 │  vanilla JS    │        │   AuditLogMiddleware  │        │  Backup            │
 └──────────────┘        └───────────────────────┘        │  Quarantine        │
                                                             └──────────────────┘
```

- Every request (except `/auth/login` and `/health`) is captured by `AuditLogMiddleware` and written to the audit log — visible to Admins, Operators, and Auditors.
- Backup purge, restore, and quarantine release/purge actions are proxied through `services/vm_client.py` to the relevant isolated VM agent; the gateway never touches disk directly.
- JWT access tokens carry `sub` (username) and `role`; the frontend decodes (not verifies) this client-side purely to decide what UI to show.

## API reference

Base path: `/api`

| Method | Path | Purpose | Required capability |
|---|---|---|---|
| POST | `/auth/register` | Create account | — |
| POST | `/auth/login` | Get access/refresh tokens | — |
| POST | `/auth/logout` | Invalidate session | authenticated |
| GET | `/dashboard/summary` | Overview stats | authenticated |
| GET | `/health/vms` | Ping all four VM agents | — |
| GET | `/backups` | List tracked files + versions | `backups.view` |
| GET | `/backups/{file_id}/versions` | Version history for a file | `backups.view` |
| DELETE | `/backups/versions/{version_id}` | Purge a version | `backups.delete` |
| GET | `/restore/requests` | List restore requests | `restore.view` |
| POST | `/restore/requests` | Submit a restore request | `restore.request` |
| POST | `/restore/requests/{id}/approve` | Approve + execute | `restore.approve` |
| POST | `/restore/requests/{id}/reject` | Reject with reason | `restore.approve` |
| GET | `/quarantine` | List isolated payloads | `quarantine.view` |
| POST | `/quarantine/{id}/release` | Release to a path | `quarantine.manage` |
| DELETE | `/quarantine/{id}/purge` | Permanently delete | `quarantine.manage` |
| GET | `/users` | List accounts | `users.view` |
| POST | `/users` | Create account | `users.create` |
| PATCH | `/users/{id}` | Update account | `users.edit` |
| POST | `/users/{id}/lock` / `/unlock` | Lock/unlock account | `users.lock` |
| POST | `/users/{id}/reset-password` | Force password reset | `users.edit` |
| GET | `/settings` | Read global config | `settings.view` |
| PUT | `/settings` | Update global config | `settings.edit` |
| GET | `/logs/audit` | Full audit trail | `logs.view` |

## Known gaps / assumptions

- There's no `GET /roles` endpoint on the backend, so the register page hardcodes `Admin(1) / Operator(2) / Auditor(3)` based on the fixed seed order in `app.py`. If roles are ever reseeded in a different order, update `KNOWN_ROLES` in `js/api.js`.
- `routers/notifications.py` is currently an empty stub on the backend — there's no dedicated notifications feed in the UI yet; unread count surfaces via the overview's "Unread Alerts" stat only.
- Tokens are stored in `localStorage` for simplicity. For a production deployment behind HTTPS, consider moving to an `httpOnly` cookie-based session instead.