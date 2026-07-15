from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from database import get_db
from config import settings
from models.models import User, Permission
from schemas.schemas import TokenPayload

# Point OAuth2 scheme to our explicit auth login endpoint route
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Decodes the JWT payload, checks user existence, and verifies they are 
    active and unlocked prior to providing API workspace entry.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenPayload(sub=username)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user session")
    if user.is_locked:
        raise HTTPException(status_code=403, detail="This security console user account is locked")
        
    return user

class PermissionChecker:
    """
    Reusable Role-Based Access Control dependency.
    Validates granular capabilities mapped explicitly via role_permissions.
    """
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        # Admin bypasses explicit checks and receives access authorization
        if current_user.role.name == "Admin":
            return True
            
        # Extract explicit string matching permissions belonging to the specific role
        has_perm = db.query(Permission).join(Permission.roles).filter(
            Permission.name == self.required_permission,
            Permission.roles.any(id=current_user.role_id)
        ).first()
        
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Required capability '{self.required_permission}' missing for current workspace role."
            )
        return True

# Utility dependency shortcuts
def require_permission(permission_name: str):
    return Depends(PermissionChecker(permission_name))