from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from ..database import get_db
from ..deps import current_user
from ..models import User, Wallet, Transaction, Category
from ..schemas import WalletCreate, WalletOut, WalletMoneyIn, ExpenseCreate, ExpenseOut
from ..services.finance import create_expense

router=APIRouter(prefix="/finance",tags=["finance"])
@router.get("/wallets",response_model=list[WalletOut])
def wallets(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return db.scalars(select(Wallet).where(Wallet.user_id==user.id).order_by(Wallet.id)).all()
@router.post("/wallets",response_model=WalletOut)
def add_wallet(data:WalletCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    w=Wallet(user_id=user.id,**data.model_dump()); db.add(w); db.commit(); db.refresh(w); return w
@router.post("/wallets/{wallet_id}/top-up",response_model=WalletOut)
def top_up_wallet(wallet_id:int,data:WalletMoneyIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    wallet=db.scalar(select(Wallet).where(Wallet.id==wallet_id,Wallet.user_id==user.id,Wallet.active==True))
    if not wallet: raise HTTPException(404,"Wallet not found")
    if data.amount <= 0: raise HTTPException(400,"Amount must be positive")
    wallet.balance += data.amount
    db.add(Transaction(user_id=user.id,wallet_id=wallet.id,kind="income",amount=data.amount,note="Wallet top-up"))
    db.commit(); db.refresh(wallet); return wallet
@router.post("/expenses",response_model=ExpenseOut)
def add_expense(data:ExpenseCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    try: tx=create_expense(db,user.id,**data.model_dump())
    except ValueError as e: raise HTTPException(400,str(e))
    return ExpenseOut(id=tx.id,amount=tx.amount,category=tx.category.name if tx.category else None,merchant=tx.merchant,note=tx.note,wallet_id=tx.wallet_id,transaction_date=tx.transaction_date)
@router.get("/expenses",response_model=list[ExpenseOut])
def expenses(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Transaction).where(Transaction.user_id==user.id,Transaction.kind=="expense").order_by(Transaction.transaction_date.desc()).limit(100)).all()
    return [ExpenseOut(id=x.id,amount=x.amount,category=x.category.name if x.category else None,merchant=x.merchant,note=x.note,wallet_id=x.wallet_id,transaction_date=x.transaction_date) for x in rows]
@router.delete("/expenses/{transaction_id}")
def delete_expense(transaction_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.user_id==user.id,Transaction.kind=="expense"))
    if not tx: raise HTTPException(404,"Expense not found")
    wallet=db.scalar(select(Wallet).where(Wallet.id==tx.wallet_id,Wallet.user_id==user.id))
    if wallet: wallet.balance += tx.amount
    db.delete(tx); db.commit(); return {"deleted":transaction_id}
@router.post("/reset")
def reset_finances(user:User=Depends(current_user),db:Session=Depends(get_db)):
    db.execute(delete(Transaction).where(Transaction.user_id==user.id))
    for wallet in db.scalars(select(Wallet).where(Wallet.user_id==user.id)).all(): wallet.balance=0
    db.commit(); return {"reset":True}
@router.get("/summary")
def summary(user:User=Depends(current_user),db:Session=Depends(get_db)):
    total=db.scalar(select(func.coalesce(func.sum(Transaction.amount),0)).where(Transaction.user_id==user.id,Transaction.kind=="expense"))
    wallets_total=db.scalar(select(func.coalesce(func.sum(Wallet.balance),0)).where(Wallet.user_id==user.id))
    return {"total_expenses":total,"wallet_balance":wallets_total}
