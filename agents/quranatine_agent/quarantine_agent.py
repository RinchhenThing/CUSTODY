"""
Quarantine VM Agent
-------------------

Responsible for managing suspicious files isolated from Detection VM.

Architecture:

Detection VM
      |
      | suspicious files
      v
Quarantine VM
      |
      | HTTP API
      v
Dashboard Backend


Local testing:

uvicorn quarantine_agent:app --host 0.0.0.0 --port 8003


Environment:

AGENT_API_KEY=my_secure_shared_key

QUARANTINE_DIR=/path/to/test/quarantine

BACKUP_INBOX_DIR=/path/to/test/backup_inbox
"""


import os
import shutil
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


# -------------------------------------------------
# Load environment
# -------------------------------------------------

load_dotenv()


# -------------------------------------------------
# Configuration
# -------------------------------------------------

API_KEY = os.getenv("AGENT_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "Missing AGENT_API_KEY environment variable"
    )


QUARANTINE_DIR = Path(
    os.getenv(
        "QUARANTINE_DIR",
        "/mnt/quarantine"
    )
)


BACKUP_INBOX_DIR = Path(
    os.getenv(
        "BACKUP_INBOX_DIR",
        "/mnt/backup_inbox"
    )
)


QUARANTINE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


BACKUP_INBOX_DIR.mkdir(
    parents=True,
    exist_ok=True
)



# -------------------------------------------------
# FastAPI Application
# -------------------------------------------------

app = FastAPI(
    title="Quarantine VM Agent",
    version="1.0"
)



# -------------------------------------------------
# Authentication
# -------------------------------------------------

def check_auth(
    x_api_key: str
):

    if x_api_key != API_KEY:

        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )



# -------------------------------------------------
# Helpers
# -------------------------------------------------

def sha256sum(
    path: Path,
    blocksize=65536
):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for chunk in iter(
            lambda: f.read(blocksize),
            b""
        ):

            h.update(chunk)

    return h.hexdigest()



def safe_filename(
    filename: str
):

    filename = os.path.basename(filename)

    if not filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    return filename



# -------------------------------------------------
# Schemas
# -------------------------------------------------

class ReleaseRequest(BaseModel):

    filename: str



class PurgeRequest(BaseModel):

    filename: str



# -------------------------------------------------
# Health
# -------------------------------------------------

@app.get("/health")
@app.get("/api/health")
def health():

    return {

        "status": "ONLINE",

        "service": "quarantine-agent"

    }



# -------------------------------------------------
# List files
# New API
# -------------------------------------------------

@app.get(
    "/api/quarantine/files"
)
def list_files(
    x_api_key: str = Header(...)
):

    check_auth(
        x_api_key
    )


    files = []


    for item in QUARANTINE_DIR.iterdir():

        if item.is_file():

            files.append(
                {

                    "filename": item.name,

                    "size": item.stat().st_size,

                    "sha256": sha256sum(item)

                }
            )


    return {

        "count": len(files),

        "files": files

    }



# -------------------------------------------------
# Dashboard compatibility endpoint
# Existing dashboard expects:
# GET /api/quarantine
# -------------------------------------------------

@app.get(
    "/api/quarantine"
)
def dashboard_list_files(
    x_api_key: str = Header(...)
):

    check_auth(
        x_api_key
    )


    files = []


    for item in QUARANTINE_DIR.iterdir():

        if item.is_file():

            files.append(
                {

                    "filename": item.name,

                    "size": item.stat().st_size,

                    "sha256": sha256sum(item)

                }
            )


    return files



# -------------------------------------------------
# Release file
# -------------------------------------------------

@app.post(
    "/api/quarantine/release"
)
def release_file(
    req: ReleaseRequest,
    x_api_key: str = Header(...)
):

    check_auth(
        x_api_key
    )


    filename = safe_filename(
        req.filename
    )


    source = (
        QUARANTINE_DIR /
        filename
    )


    if not source.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found in quarantine"
        )


    destination = (
        BACKUP_INBOX_DIR /
        filename
    )


    shutil.move(
        str(source),
        str(destination)
    )


    return {

        "status": "RELEASED",

        "filename": filename,

        "destination": str(destination)

    }



# -------------------------------------------------
# Purge file
# Dashboard compatibility
# POST /api/quarantine/purge
# -------------------------------------------------

@app.post(
    "/api/quarantine/purge"
)
def purge_file(
    req: PurgeRequest,
    x_api_key: str = Header(...)
):

    check_auth(
        x_api_key
    )


    filename = safe_filename(
        req.filename
    )


    target = (
        QUARANTINE_DIR /
        filename
    )


    if not target.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )


    target.unlink()


    return {

        "status": "PURGED",

        "filename": filename

    }



# -------------------------------------------------
# Delete file
# New API
# -------------------------------------------------

@app.delete(
    "/api/quarantine/files/{filename}"
)
def delete_file(
    filename: str,
    x_api_key: str = Header(...)
):

    check_auth(
        x_api_key
    )


    filename = safe_filename(
        filename
    )


    target = (
        QUARANTINE_DIR /
        filename
    )


    if not target.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )


    target.unlink()


    return {

        "status": "DELETED",

        "filename": filename

    }



# -------------------------------------------------
# Local execution
# -------------------------------------------------

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(
        "quarantine_agent:app",
        host="0.0.0.0",
        port=8003
    )
