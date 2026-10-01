from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from .config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGO = "HS256"

def hash_password(password: str): return pwd.hash(password)
def verify_password(password: str, hashed: str): return pwd.verify(password, hashed)
def create_token(user_id: int):
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm=ALGO)
def decode_token(token: str): return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
