"""
Security Audit Log Middleware
Intersects transactions dynamically to record comprehensive administrative footprints.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import datetime
from jose import jwt, JWTError
from config import settings
from database import SessionLocal
from models.models import AuditLog

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract metadata from incoming socket environment
        ip_address = request.client.host if request.client else "127.0.0.1"
        action = request.method
        target = str(request.url.path)
        
        # Don't create recursive logs for basic auth loops or structural health sweeps
        if "/api/auth/login" in target or "/api/health" in target:
            return await call_next(request)

        # Attempt to decode user context via Authorization header
        user_name = "Anonymous"
        user_role = "Unauthenticated"
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_name = payload.get("sub", "Anonymous")
                user_role = payload.get("role", "Unauthenticated")
            except JWTError:
                pass # Expired or tampered tokens fall through to anonymous auditing

        # Proceed down the execution loop to gather responses
        status_label = "SUCCESS"
        try:
            response: Response = await call_next(request)
            if response.status_code >= 400:
                status_label = f"FAILURE ({response.status_code})"
            return response
        except Exception as e:
            status_label = f"CRITICAL EXCEPTION: {str(e)}"
            raise e
        finally:
            # Commit the audit metric asynchronously to SQLite database session
            db = SessionLocal()
            try:
                audit_entry = AuditLog(
                    timestamp=datetime.datetime.utcnow(),
                    user=user_name,
                    role=user_role,
                    action=action,
                    target=target,
                    ip_address=ip_address,
                    status=status_label
                )
                db.add(audit_entry)
                db.commit()
            except Exception:
                db.rollback() # Never let audit engine failures crash the user transaction
            finally:
                db.close()