from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator

class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class RegisterIn(AuthIn):
    full_name: str = Field(default="User", min_length=1, max_length=120)
    password_confirmation: str | None = None

    @field_validator("password_confirmation")
    @classmethod
    def passwords_match(cls, value, info):
        if value is not None and value != info.data.get("password"):
            raise ValueError("Passwords do not match")
        return value

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    profile_picture: str | None
    currency: str
    timezone: str
    date_format: str
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    profile_picture: str | None = None
    currency: str | None = None
    timezone: str | None = None
    date_format: str | None = None

class AdminUserOut(UserOut):
    wallet_count: int = 0
    transaction_count: int = 0

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ForgotPasswordOut(BaseModel):
    message: str
    reset_token: str | None = None

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=32)
    password: str = Field(min_length=8)
    password_confirmation: str

    @field_validator("password_confirmation")
    @classmethod
    def reset_passwords_match(cls, value, info):
        if value != info.data.get("password"):
            raise ValueError("Passwords do not match")
        return value

class WalletCreate(BaseModel):
    name: str
    wallet_type: str = "bank"
    bank_name: str | None = None
    account_last4: str | None = None
    account_holder_name: str | None = None
    currency: str = "INR"
    description: str | None = None
    opening_balance: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    is_default: bool = False

    @field_validator("account_last4")
    @classmethod
    def validate_account_last4(cls, value):
        if value is not None and (len(value) != 4 or not value.isdigit()):
            raise ValueError("Account last 4 digits must contain exactly four digits")
        return value

class WalletOut(WalletCreate):
    id: int
    active: bool = True
    is_default: bool = False
    model_config = ConfigDict(from_attributes=True)

class WalletUpdate(BaseModel):
    name: str | None = None
    wallet_type: str | None = None
    bank_name: str | None = None
    account_last4: str | None = None
    account_holder_name: str | None = None
    currency: str | None = None
    description: str | None = None

class TransferCreate(BaseModel):
    source_wallet_id: int
    destination_wallet_id: int
    amount: Decimal
    note: str | None = None
    transaction_date: datetime | None = None

class WalletSelect(BaseModel):
    wallet_id: int

class WalletMoneyIn(BaseModel):
    amount: Decimal

class ExpenseCreate(BaseModel):
    wallet_id: int
    amount: Decimal
    category: str
    merchant: str | None = None
    note: str | None = None
    transaction_date: datetime | None = None

class TransactionCreate(BaseModel):
    wallet_id: int
    amount: Decimal
    kind: str = "expense"
    category: str | None = None
    merchant: str | None = None
    note: str | None = None
    reference_number: str | None = None
    transaction_date: datetime | None = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value):
        allowed = {"expense", "income", "refund", "adjustment"}
        if value.lower() not in allowed:
            raise ValueError(f"Transaction type must be one of: {', '.join(sorted(allowed))}")
        return value.lower()

class ExpenseOut(BaseModel):
    id: int
    amount: Decimal
    category: str | None
    merchant: str | None
    note: str | None
    wallet_id: int
    transaction_date: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatIn(BaseModel):
    message: str

class ChatOut(BaseModel):
    reply: str

class BudgetCreate(BaseModel):
    category: str
    month: date
    amount: Decimal
    wallet_id: int | None = None
    threshold_percent: int = Field(default=75, ge=1, le=100)

class BudgetOut(BaseModel):
    id: int
    category: str
    month: date
    amount: Decimal
    spent: Decimal
    remaining: Decimal
    percent_used: Decimal
    wallet_id: int | None

class GoalCreate(BaseModel):
    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    target_date: date | None = None
    monthly_contribution: Decimal = Decimal("0")
    priority: str = "normal"
    linked_wallet_id: int | None = None

class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date | None
    monthly_contribution: Decimal
    priority: str
    status: str
    progress_percent: Decimal
    linked_wallet_id: int | None

class GoalContribution(BaseModel):
    amount: Decimal
