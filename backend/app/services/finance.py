from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Category, Wallet, Transaction

def get_or_create_category(db: Session, name: str):
    name = name.strip().title()
    cat = db.scalar(select(Category).where(Category.name == name))
    if not cat:
        cat = Category(name=name); db.add(cat); db.flush()
    return cat

def create_expense(db, user_id, wallet_id, amount, category, merchant=None, note=None, transaction_date=None):
    wallet = db.scalar(select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id, Wallet.active == True))
    if not wallet: raise ValueError("Wallet not found")
    amount = Decimal(str(amount))
    if amount <= 0: raise ValueError("Amount must be positive")
    cat = get_or_create_category(db, category)
    tx = Transaction(user_id=user_id, wallet_id=wallet.id, category_id=cat.id, kind="expense", amount=amount, merchant=merchant, note=note, transaction_date=transaction_date or datetime.utcnow())
    wallet.balance -= amount
    db.add(tx); db.commit(); db.refresh(tx)
    return tx

def create_transfer(db, user_id, source_wallet_id, destination_wallet_id, amount, note=None, transaction_date=None):
    if source_wallet_id == destination_wallet_id:
        raise ValueError("Source and destination wallets must be different")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("Amount must be positive")
    wallets = db.scalars(select(Wallet).where(Wallet.id.in_([source_wallet_id, destination_wallet_id]), Wallet.user_id == user_id, Wallet.active == True)).all()
    wallet_by_id = {wallet.id: wallet for wallet in wallets}
    source = wallet_by_id.get(source_wallet_id)
    destination = wallet_by_id.get(destination_wallet_id)
    if not source or not destination:
        raise ValueError("Wallet not found")
    if source.balance < amount:
        raise ValueError("Insufficient wallet balance")
    transfer_id = str(uuid4())
    transfer_date = transaction_date or datetime.utcnow()
    source.balance -= amount
    destination.balance += amount
    db.add_all([
        Transaction(user_id=user_id, wallet_id=source.id, kind="transfer", amount=amount, note=note, transfer_id=transfer_id, transfer_direction="out", transaction_date=transfer_date),
        Transaction(user_id=user_id, wallet_id=destination.id, kind="transfer", amount=amount, note=note, transfer_id=transfer_id, transfer_direction="in", transaction_date=transfer_date),
    ])
    db.commit()
    return transfer_id
