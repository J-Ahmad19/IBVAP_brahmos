from fastapi import Header, HTTPException, Depends
from typing import Optional

# Roles:
# - VIEWER: read-only monitoring
# - OPERATOR: alert review, confirm, false alarm, needs review
# - ADMIN: camera management, fence management, watchlists, thresholds, configuration

class User:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

def get_current_user(x_user_role: Optional[str] = Header("VIEWER", alias="X-User-Role")) -> User:
    """Mock authentication dependency reading the role from headers."""
    # In a real app, this would decode a JWT or session token.
    valid_roles = ["VIEWER", "OPERATOR", "ADMIN"]
    role = x_user_role.upper() if x_user_role else "VIEWER"
    
    if role not in valid_roles:
        role = "VIEWER"
        
    return User(username=f"mock_user_{role.lower()}", role=role)

def require_role(allowed_roles: list[str]):
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return role_checker

def get_viewer(user: User = Depends(require_role(["VIEWER", "OPERATOR", "ADMIN"]))):
    return user

def get_operator(user: User = Depends(require_role(["OPERATOR", "ADMIN"]))):
    return user

def get_admin(user: User = Depends(require_role(["ADMIN"]))):
    return user
