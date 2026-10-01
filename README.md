# Dex — Personal Finance OS

A full-stack starter for a conversational personal finance platform.

## Current MVP
- FastAPI backend
- PostgreSQL
- JWT authentication
- Wallets and balances
- Expense ledger
- Categories
- Dashboard summary
- Natural-language expense entry through an AI endpoint
- Next.js frontend
- Docker Compose

## Run

1. Install Docker Desktop.
2. In this directory create `.env` with:

```env
OPENAI_API_KEY=your_key_here
```

3. Run:

```bash
docker compose up --build
```

4. Open http://localhost:3000
5. API docs: http://localhost:8000/docs

## GitHub Pages

The frontend is configured for GitHub Pages at:

https://bhushanashinde.github.io/dex-personal-finance-os/

The workflow in `.github/workflows/deploy-pages.yml` deploys the static Next.js frontend on every push to `main`. In the repository settings, set **Pages → Source** to **GitHub Actions**. For login and financial actions to work on the hosted page, add the repository variable `NEXT_PUBLIC_API_URL` with the public URL of a deployed Dex backend. GitHub Pages cannot host the FastAPI/PostgreSQL services.

## Wallets and statements

The dashboard supports multiple wallets, wallet selection, transfers, budgets, savings goals, and CSV/Excel/PDF statement downloads. For an existing database, run the additive migrations from `backend` after the database is available:

```bash
alembic upgrade head
```

Wallet APIs are available under `/wallets`; transaction APIs under `/transactions`; planning APIs under `/planning/budgets` and `/planning/goals`; statement exports are available under `/statements/export/csv`, `/statements/export/excel`, and `/statements/export/pdf`.

If no valid OpenAI key is configured, Dex uses its deterministic offline expense parser for common messages such as `Spent 450 on petrol`. A real OpenAI key enables richer natural-language interpretation.

## Important
This is an MVP foundation, not production financial software. Before handling real financial data, add migrations, stronger secrets, CSRF/session hardening as appropriate, audit logging, encryption, rate limiting, backups, monitoring, tests, and a proper transaction/idempotency model.
