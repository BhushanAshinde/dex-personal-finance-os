from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Transaction, User, Wallet
from ..schemas import TransactionCreate
from ..services.finance import get_or_create_category

router = APIRouter(prefix="/transactions", tags=["transactions"])


def serialize(transaction: Transaction, wallet: Wallet):
    return {"id": transaction.id, "user_id": transaction.user_id, "wallet_id": wallet.id, "wallet": wallet.name, "bank": wallet.bank_name, "amount": transaction.amount, "kind": transaction.kind, "category": transaction.category.name if transaction.category else None, "merchant": transaction.merchant, "description": transaction.note, "reference_number": transaction.reference_number, "transaction_date": transaction.transaction_date, "transfer_id": transaction.transfer_id}


@router.get("")
def list_transactions(wallet_id: int | None = None, kind: str | None = None, category: str | None = None, merchant: str | None = None, search: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None, amount: Decimal | None = None, limit: int = Query(100, ge=1, le=500), user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Transaction, Wallet).join(Wallet, Wallet.id == Transaction.wallet_id).where(Transaction.user_id == user.id)
    if wallet_id is not None: query = query.where(Transaction.wallet_id == wallet_id)
    if kind: query = query.where(Transaction.kind == kind.lower())
    if category: query = query.where(Transaction.category.has(name=category))
    if merchant: query = query.where(Transaction.merchant.ilike(f"%{merchant}%"))
    if search: query = query.where(or_(Transaction.merchant.ilike(f"%{search}%"), Transaction.note.ilike(f"%{search}%"), Transaction.reference_number.ilike(f"%{search}%"), Wallet.name.ilike(f"%{search}%"), Wallet.bank_name.ilike(f"%{search}%")))
    if date_from: query = query.where(Transaction.transaction_date >= date_from)
    if date_to: query = query.where(Transaction.transaction_date <= date_to)
    if amount is not None: query = query.where(Transaction.amount == amount)
    return [serialize(transaction, wallet) for transaction, wallet in db.execute(query.order_by(Transaction.transaction_date.desc()).limit(limit)).all()]


@router.post("")
def create_transaction(data: TransactionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.id == data.wallet_id, Wallet.user_id == user.id, Wallet.active == True))
    if not wallet: raise HTTPException(404, "Wallet not found")
    if data.amount <= 0: raise HTTPException(400, "Amount must be positive")
    category = get_or_create_category(db, data.category) if data.category else None
    transaction = Transaction(user_id=user.id, wallet_id=wallet.id, category_id=category.id if category else None, kind=data.kind, amount=data.amount, merchant=data.merchant, note=data.note, reference_number=data.reference_number, transaction_date=data.transaction_date or datetime.utcnow())
    if data.kind == "expense": wallet.balance -= data.amount
    else: wallet.balance += data.amount
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return serialize(transaction, wallet)


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    transaction = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id))
    if not transaction: raise HTTPException(404, "Transaction not found")
    wallet = db.scalar(select(Wallet).where(Wallet.id == transaction.wallet_id, Wallet.user_id == user.id))
    if wallet and transaction.kind != "transfer":
        wallet.balance += transaction.amount if transaction.kind == "expense" else -transaction.amount
    db.delete(transaction)
    db.commit()
    return {"deleted": transaction_id}
