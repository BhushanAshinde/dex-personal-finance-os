from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Budget, Goal, Transaction, User, Wallet
from ..schemas import BudgetCreate, BudgetOut, GoalContribution, GoalCreate, GoalOut
from ..services.finance import get_or_create_category

router = APIRouter(prefix="/planning", tags=["planning"])


def budget_output(budget: Budget, spent: Decimal):
    percent = (spent / budget.amount * 100) if budget.amount else Decimal("0")
    return BudgetOut(id=budget.id, category=budget.category.name if budget.category else "Other", month=budget.month, amount=budget.amount, spent=spent, remaining=max(budget.amount - spent, Decimal("0")), percent_used=percent, wallet_id=budget.wallet_id)


def goal_output(goal: Goal):
    progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount else Decimal("0")
    return GoalOut(id=goal.id, name=goal.name, target_amount=goal.target_amount, current_amount=goal.current_amount, target_date=goal.target_date, monthly_contribution=goal.monthly_contribution, priority=goal.priority, status=goal.status, progress_percent=min(progress, Decimal("100")), linked_wallet_id=goal.linked_wallet_id)


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    budgets = db.scalars(select(Budget).where(Budget.user_id == user.id).order_by(Budget.month.desc(), Budget.id)).all()
    result = []
    for budget in budgets:
        next_month = (budget.month.replace(day=28) + timedelta(days=4)).replace(day=1)
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.user_id == user.id, Transaction.kind == "expense", Transaction.category_id == budget.category_id, Transaction.transaction_date >= budget.month, Transaction.transaction_date < next_month)
        if budget.wallet_id is not None: query = query.where(Transaction.wallet_id == budget.wallet_id)
        spent = db.scalar(query) or Decimal("0")
        result.append(budget_output(budget, spent))
    return result


@router.post("/budgets", response_model=BudgetOut)
def create_budget(data: BudgetCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.amount <= 0: raise HTTPException(400, "Budget amount must be positive")
    if data.wallet_id is not None and not db.scalar(select(Wallet.id).where(Wallet.id == data.wallet_id, Wallet.user_id == user.id)):
        raise HTTPException(404, "Wallet not found")
    category = get_or_create_category(db, data.category)
    budget = Budget(user_id=user.id, category_id=category.id, wallet_id=data.wallet_id, month=data.month.replace(day=1), amount=data.amount, threshold_percent=data.threshold_percent)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget_output(budget, Decimal("0"))


@router.get("/goals", response_model=list[GoalOut])
def list_goals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [goal_output(goal) for goal in db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.status, Goal.target_date)).all()]


@router.post("/goals", response_model=GoalOut)
def create_goal(data: GoalCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.target_amount <= 0: raise HTTPException(400, "Goal target must be positive")
    if data.current_amount < 0: raise HTTPException(400, "Current amount cannot be negative")
    if data.linked_wallet_id is not None and not db.scalar(select(Wallet.id).where(Wallet.id == data.linked_wallet_id, Wallet.user_id == user.id)):
        raise HTTPException(404, "Wallet not found")
    goal = Goal(user_id=user.id, **data.model_dump())
    if goal.current_amount >= goal.target_amount: goal.status = "complete"
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal_output(goal)


@router.post("/goals/{goal_id}/contribute", response_model=GoalOut)
def contribute_to_goal(goal_id: int, data: GoalContribution, user: User = Depends(current_user), db: Session = Depends(get_db)):
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not goal: raise HTTPException(404, "Goal not found")
    if data.amount <= 0: raise HTTPException(400, "Contribution must be positive")
    goal.current_amount += data.amount
    if goal.current_amount >= goal.target_amount: goal.status = "complete"
    db.commit()
    db.refresh(goal)
    return goal_output(goal)
