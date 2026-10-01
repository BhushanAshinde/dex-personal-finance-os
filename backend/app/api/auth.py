import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..deps import current_user
from ..models import User
from ..config import settings
from ..models import PasswordResetToken
from ..schemas import AuthIn, ForgotPasswordIn, ForgotPasswordOut, RegisterIn, ResetPasswordIn, Token, UserOut
from ..security import hash_password, verify_password, create_token

router=APIRouter(prefix="/auth", tags=["auth"])
@router.post("/register", response_model=Token)
def register(data: RegisterIn, db: Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)): raise HTTPException(409,"Email already registered")
    u=User(email=data.email,password_hash=hash_password(data.password),full_name=data.full_name); db.add(u); db.commit(); db.refresh(u)
    return Token(access_token=create_token(u.id))
@router.post("/login", response_model=Token)
def login(data: AuthIn, db: Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email == data.email))
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,"Invalid credentials")
    if not u.is_active: raise HTTPException(403,"Account is inactive")
    u.last_login = datetime.utcnow(); db.commit()
    return Token(access_token=create_token(u.id))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

@router.post("/forgot-password", response_model=ForgotPasswordOut)
def forgot_password(data: ForgotPasswordIn, db: Session = Depends(get_db)):
    message = "If an account exists for this email, you will receive password reset instructions shortly."
    user = db.scalar(select(User).where(User.email == data.email))
    if not user:
        return ForgotPasswordOut(message=message)
    now = datetime.utcnow()
    for previous in db.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))).all():
        previous.used_at = now
    raw_token = secrets.token_urlsafe(48)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes)))
    db.commit()
    reset_url = f"{settings.app_url}/reset-password?token={raw_token}"
    if settings.smtp_host and settings.smtp_username and settings.smtp_password:
        email = EmailMessage()
        email["Subject"] = "Reset your Dex password"
        email["From"] = settings.smtp_username
        email["To"] = user.email
        email.set_content(f"Reset your Dex password within {settings.password_reset_ttl_minutes} minutes:\n\n{reset_url}")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(email)
    if settings.environment.lower() != "production":
        return ForgotPasswordOut(message=message, reset_token=raw_token)
    return ForgotPasswordOut(message=message)

@router.post("/reset-password", response_model=Token)
def reset_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    reset = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None)))
    if not reset or reset.expires_at <= datetime.utcnow():
        raise HTTPException(400, "Reset link is invalid or expired")
    user = db.get(User, reset.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Reset link is invalid or expired")
    user.password_hash = hash_password(data.password)
    reset.used_at = datetime.utcnow()
    db.commit()
    return Token(access_token=create_token(user.id))
