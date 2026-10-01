from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Transaction, User, Wallet
from ..schemas import TransferCreate, WalletCreate, WalletOut, WalletSelect, WalletUpdate
from ..services.finance import create_transfer

router = APIRouter(prefix="/wallets", tags=["wallets"])


def get_owned_wallet(wallet_id: int, user_id: int, db: Session, include_archived: bool = False):
    query = select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id)
    if not include_archived:
        query = query.where(Wallet.active == True)
    return db.scalar(query)


@router.get("", response_model=list[WalletOut])
def list_wallets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Wallet).where(Wallet.user_id == user.id).order_by(Wallet.id)).all()


@router.post("", response_model=WalletOut)
def create_wallet(data: WalletCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.scalar(select(Wallet).where(Wallet.user_id == user.id, func.lower(Wallet.name) == data.name.lower())):
        raise HTTPException(409, "A wallet with this name already exists")
    opening_balance = data.opening_balance if data.opening_balance else data.balance
    wallet = Wallet(user_id=user.id, **data.model_dump(exclude={"balance", "opening_balance"}), balance=opening_balance, opening_balance=opening_balance)
    if data.is_default or not db.scalar(select(Wallet.id).where(Wallet.user_id == user.id, Wallet.active == True)):
        db.execute(update(Wallet).where(Wallet.user_id == user.id).values(is_default=False))
        wallet.is_default = True
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


@router.get("/{wallet_id}", response_model=WalletOut)
def get_wallet(wallet_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallet = get_owned_wallet(wallet_id, user.id, db, include_archived=True)
    if not wallet:
        raise HTTPException(404, "Wallet not found")
    return wallet


@router.put("/{wallet_id}", response_model=WalletOut)
def update_wallet(wallet_id: int, data: WalletUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallet = get_owned_wallet(wallet_id, user.id, db, include_archived=True)
    if not wallet:
        raise HTTPException(404, "Wallet not found")
    values = data.model_dump(exclude_unset=True)
    if "account_last4" in values and values["account_last4"] is not None and (len(values["account_last4"]) != 4 or not values["account_last4"].isdigit()):
        raise HTTPException(422, "Account last 4 digits must contain exactly four digits")
    if "name" in values and db.scalar(select(Wallet).where(Wallet.user_id == user.id, Wallet.id != wallet_id, func.lower(Wallet.name) == values["name"].lower())):
        raise HTTPException(409, "A wallet with this name already exists")
    for key, value in values.items():
        setattr(wallet, key, value)
    db.commit()
    db.refresh(wallet)
    return wallet


@router.post("/{wallet_id}/archive", response_model=WalletOut)
def archive_wallet(wallet_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallet = get_owned_wallet(wallet_id, user.id, db, include_archived=True)
    if not wallet:
        raise HTTPException(404, "Wallet not found")
    wallet.active = False
    wallet.is_default = False
    db.commit()
    db.refresh(wallet)
    return wallet


@router.post("/{wallet_id}/set-default", response_model=WalletOut)
def set_default_wallet(wallet_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallet = get_owned_wallet(wallet_id, user.id, db)
    if not wallet:
        raise HTTPException(404, "Wallet not found")
    db.execute(update(Wallet).where(Wallet.user_id == user.id).values(is_default=False))
    wallet.is_default = True
    db.commit()
    db.refresh(wallet)
    return wallet


@router.post("/select", response_model=WalletOut)
def select_wallet(data: WalletSelect, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return set_default_wallet(data.wallet_id, user, db)


@router.post("/transfers")
def transfer(data: TransferCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        transfer_id = create_transfer(db, user.id, **data.model_dump())
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return {"transfer_id": transfer_id, "type": "transfer"}


@router.get("/{wallet_id}/transactions")
def wallet_transactions(wallet_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not get_owned_wallet(wallet_id, user.id, db, include_archived=True):
        raise HTTPException(404, "Wallet not found")
    rows = db.scalars(select(Transaction).where(Transaction.user_id == user.id, Transaction.wallet_id == wallet_id).order_by(Transaction.transaction_date.desc())).all()
    return [{"id": row.id, "amount": row.amount, "kind": row.kind, "merchant": row.merchant, "description": row.note, "date": row.transaction_date, "transfer_id": row.transfer_id, "transfer_direction": row.transfer_direction} for row in rows]


@router.get("/{wallet_id}/summary")
def wallet_summary(wallet_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not get_owned_wallet(wallet_id, user.id, db, include_archived=True):
        raise HTTPException(404, "Wallet not found")
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    income = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == user.id, Transaction.wallet_id == wallet_id, Transaction.kind.in_(["income", "refund"]), Transaction.transaction_date >= month_start))
    expenses = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == user.id, Transaction.wallet_id == wallet_id, Transaction.kind == "expense", Transaction.transaction_date >= month_start))
    count = db.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user.id, Transaction.wallet_id == wallet_id))
    wallet = get_owned_wallet(wallet_id, user.id, db, include_archived=True)
    return {"balance": wallet.balance, "income_this_month": income, "expense_this_month": expenses, "transaction_count": count}
