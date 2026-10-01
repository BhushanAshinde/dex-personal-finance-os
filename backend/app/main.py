from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import auth, finance, ai, wallets, statements, reports, users, admin, transactions, planning
app=FastAPI(title="Dex Finance API",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(auth.router); app.include_router(finance.router); app.include_router(ai.router)
app.include_router(wallets.router); app.include_router(statements.router); app.include_router(reports.router); app.include_router(users.router); app.include_router(admin.router); app.include_router(transactions.router); app.include_router(planning.router)
@app.get("/health")
def health(): return {"status":"ok","service":"dex"}
