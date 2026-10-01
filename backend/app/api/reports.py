from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Transaction, User, Wallet

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/wallets")
def wallet_report(user: User = Depends(current_user), db: Session = Depends(get_db)):
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.execute(
        select(
            Wallet.id,
            Wallet.name,
            Wallet.bank_name,
            Wallet.currency,
            Wallet.balance,
            func.coalesce(func.sum(case((Transaction.kind.in_(["income", "refund"]), Transaction.amount), else_=0)), 0).label("income"),
            func.coalesce(func.sum(case((Transaction.kind == "expense", Transaction.amount), else_=0)), 0).label("expense"),
            func.count(Transaction.id).label("transactions"),
        )
        .outerjoin(Transaction, (Transaction.wallet_id == Wallet.id) & (Transaction.transaction_date >= month_start))
        .where(Wallet.user_id == user.id)
        .group_by(Wallet.id)
        .order_by(Wallet.id)
    ).all()
    return [{"wallet_id": row.id, "wallet": row.name, "bank": row.bank_name, "currency": row.currency, "balance": row.balance, "income_this_month": row.income, "expense_this_month": row.expense, "net_cash_flow": row.income - row.expense, "transaction_count": row.transactions} for row in rows]
