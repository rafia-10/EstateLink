"""FastAPI Application for EstateLink Tenancy Management System"""
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import sys
from pathlib import Path

# Add parent directory to path to import tenancy_agent
sys.path.append(str(Path(__file__).parent.parent))

from tenancy_agent.database import SupabaseConnection
from tenancy_agent.contracts import fetch_contracts, get_alerts, get_contract_summary
from tenancy_agent.checks import generate_checks, get_overdue_checks, get_upcoming_checks

app = FastAPI(title="EstateLink Tenancy Management System")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    conn = SupabaseConnection()

    try:
        contracts = fetch_contracts(conn)
        alerts = get_alerts(conn, alert_days=100)
        upcoming = get_upcoming_checks(conn, days_ahead=30)
        overdue = get_overdue_checks(conn)

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "total_contracts": len(contracts),
            "expiring_contracts": len(alerts),
            "upcoming_payments": len(upcoming),
            "overdue_payments": len(overdue)
        })
    finally:
        conn.close()


@app.get("/contracts", response_class=HTMLResponse)
async def contracts_page(request: Request):
    """Contracts listing page"""
    conn = SupabaseConnection()

    try:
        contracts = fetch_contracts(conn)
        return templates.TemplateResponse("contracts.html", {
            "request": request,
            "contracts": contracts
        })
    finally:
        conn.close()


@app.get("/contracts/{contract_id}", response_class=HTMLResponse)
async def contract_detail(request: Request, contract_id: int):
    """Contract detail page"""
    conn = SupabaseConnection()

    try:
        contract = get_contract_summary(conn, contract_id)
        return templates.TemplateResponse("contract_detail.html", {
            "request": request,
            "contract": contract
        })
    finally:
        conn.close()


@app.get("/expiring", response_class=HTMLResponse)
async def expiring_contracts(request: Request):
    """Expiring contracts page"""
    conn = SupabaseConnection()

    try:
        alerts = get_alerts(conn, alert_days=100)
        return templates.TemplateResponse("expiring.html", {
            "request": request,
            "contracts": alerts
        })
    finally:
        conn.close()


@app.get("/payments/upcoming", response_class=HTMLResponse)
async def upcoming_payments(request: Request):
    """Upcoming payments page"""
    conn = SupabaseConnection()

    try:
        upcoming = get_upcoming_checks(conn, days_ahead=30)
        return templates.TemplateResponse("upcoming_payments.html", {
            "request": request,
            "checks": upcoming
        })
    finally:
        conn.close()


@app.get("/payments/overdue", response_class=HTMLResponse)
async def overdue_payments(request: Request):
    """Overdue payments page"""
    conn = SupabaseConnection()

    try:
        overdue = get_overdue_checks(conn)
        return templates.TemplateResponse("overdue_payments.html", {
            "request": request,
            "checks": overdue
        })
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
