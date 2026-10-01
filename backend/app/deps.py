from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer()
def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try: user_id = int(decode_token(creds.credentials)["sub"])
    except Exception: raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, "User not found")
    if not user.is_active: raise HTTPException(403, "Account is inactive")
    return user

def admin_user(user: User = Depends(current_user)):
    if user.role != "ADMIN":
        raise HTTPException(403, "Admin access required")
    return user
