from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import current_user
from ..models import User
from ..schemas import ChatIn, ChatOut
from ..services.ai import parse_message
from ..services.finance import create_expense

router=APIRouter(prefix="/ai",tags=["ai"])
@router.post("/chat",response_model=ChatOut)
def chat(data:ChatIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    parsed=parse_message(data.message)
    if parsed.get("intent") in {"create_expense", "create_expenses"}:
        wallets=[wallet for wallet in user.wallets if wallet.active]
        if not wallets: return ChatOut(reply="You don't have a wallet yet. Create one first.")
        wallets.sort(key=lambda wallet: (not wallet.is_default, wallet.id))
        items = parsed.get("items") or [parsed]
        transactions = []
        for item in items:
            amount=item.get("amount")
            if not amount: return ChatOut(reply="What amount did you spend?")
            transactions.append(create_expense(db,user.id,wallets[0].id,amount,item.get("category","Other"),item.get("merchant"),item.get("note")))
        if len(transactions) == 1:
            tx = transactions[0]
            return ChatOut(reply=f"✅ Added ₹{tx.amount} for {tx.category.name}. Wallet balance is now ₹{wallets[0].balance}.")
        total = sum((tx.amount for tx in transactions), 0)
        return ChatOut(reply=f"✅ Added {len(transactions)} expenses totaling ₹{total}. Wallet balance is now ₹{wallets[0].balance}.")
    return ChatOut(reply=parsed.get("reply","I couldn't understand that yet. Try: 'Spent 450 on petrol'."))
