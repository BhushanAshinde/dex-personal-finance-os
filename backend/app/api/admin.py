from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import admin_user
from ..models import Transaction, User, Wallet
from ..schemas import AdminUserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
def list_users(search: str | None = None, active: bool | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), _: User = Depends(admin_user), db: Session = Depends(get_db)):
    query = select(User).order_by(User.created_at.desc())
    if search:
        query = query.where((User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%")))
    if active is not None:
        query = query.where(User.is_active == active)
    users = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    result = []
    for user in users:
        result.append(AdminUserOut.model_validate({**user.__dict__, "wallet_count": db.scalar(select(func.count(Wallet.id)).where(Wallet.user_id == user.id)) or 0, "transaction_count": db.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user.id)) or 0}))
    return result


@router.get("/stats")
def stats(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "total_users": db.scalar(select(func.count(User.id))) or 0,
        "active_users": db.scalar(select(func.count(User.id)).where(User.is_active == True)) or 0,
        "inactive_users": db.scalar(select(func.count(User.id)).where(User.is_active == False)) or 0,
        "total_wallets": db.scalar(select(func.count(Wallet.id))) or 0,
        "total_transactions": db.scalar(select(func.count(Transaction.id))) or 0,
        "total_expenses": db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.kind == "expense")) or 0,
        "total_income": db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.kind.in_(["income", "refund"]))) or 0,
    }


@router.post("/users/{user_id}/activate")
def activate_user(user_id: int, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: return {"updated": False}
    user.is_active = True
    db.commit()
    return {"updated": True}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if user_id == admin.id:
        return {"updated": False, "reason": "An admin cannot deactivate their own account"}
    user = db.get(User, user_id)
    if not user: return {"updated": False}
    user.is_active = False
    db.commit()
    return {"updated": True}
