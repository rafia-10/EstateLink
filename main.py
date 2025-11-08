"""
EstateLink FastAPI Application
Production-ready API endpoints for tenancy management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the estate agent functions
from tenancy_agent.tenancy_agent import (
    fetch_contracts,
    generate_checks,
    get_alerts,
    get_overdue_checks,
    get_upcoming_checks,
    get_contract_summary
)

# Initialize FastAPI app
app = FastAPI(
    title="EstateLink API",
    description="Real Estate Tenancy Management System",
    version="1.0.0"
)

# Database configuration - loads from .env file with proper quote stripping
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "estate_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres").strip('"'),
    "host": os.getenv("DB_HOST", "localhost").strip('"'),
    "port": int(os.getenv("DB_PORT", "5432"))
}


# Pydantic models for request/response validation
class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+971[0-9]{9}$')


class ContractCreate(BaseModel):
    tenant_id: int
    property_name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    start_date: date
    expiry_date: date
    annual_rent: float = Field(..., gt=0)
    num_checks: int = Field(..., ge=1, le=12)
    payment_method: str = Field(..., pattern=r'^(Bank Transfer|Cheque|Cash)$')
    agent_name: str = Field(..., min_length=1, max_length=255)
    agent_email: EmailStr


class AlertResponse(BaseModel):
    contract_id: int
    tenant_name: str
    tenant_email: str
    tenant_phone: str
    property_name: str
    location: str
    expiry_date: date
    days_until_expiry: int
    agent_name: str
    agent_email: str


class CheckResponse(BaseModel):
    check_id: int
    check_no: str
    check_date: date
    amount: float
    contract_id: int
    property_name: str
    tenant_name: str
    tenant_email: str


# Database connection manager
@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Ensures connections are properly closed after use.
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        yield conn
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
    finally:
        if conn:
            conn.close()


def get_db():
    """
    Dependency for FastAPI endpoints to get database connection.
    """
    with get_db_connection() as conn:
        yield conn


# Health check endpoint
@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "service": "EstateLink API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Database health check"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")


# Contract endpoints
@app.get("/api/v1/contracts", response_model=List[Dict[str, Any]])
def get_contracts():
    """
    Retrieve all contracts with tenant information.
    """
    try:
        with get_db_connection() as conn:
            contracts = fetch_contracts(conn)
            return contracts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/contracts/{contract_id}")
def get_contract(contract_id: int):
    """
    Retrieve a specific contract with all its checks.
    """
    try:
        with get_db_connection() as conn:
            contract = get_contract_summary(conn, contract_id)
            if not contract:
                raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
            return contract
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/contracts", status_code=201)
def create_contract(contract: ContractCreate):
    """
    Create a new tenancy contract.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Validate tenant exists
            cursor.execute("SELECT id FROM tenants WHERE id = %s", (contract.tenant_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Tenant {contract.tenant_id} not found")

            # Validate dates
            if contract.expiry_date <= contract.start_date:
                raise HTTPException(status_code=400, detail="Expiry date must be after start date")

            # Insert contract
            cursor.execute("""
                INSERT INTO contracts (
                    tenant_id, property_name, location, start_date, expiry_date,
                    annual_rent, num_checks, payment_method, agent_name, agent_email
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                contract.tenant_id, contract.property_name, contract.location,
                contract.start_date, contract.expiry_date, contract.annual_rent,
                contract.num_checks, contract.payment_method, contract.agent_name,
                contract.agent_email
            ))

            contract_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()

            return {
                "message": "Contract created successfully",
                "contract_id": contract_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Check generation endpoint
@app.post("/api/v1/checks/generate")
def generate_payment_checks():
    """
    Generate payment checks for all contracts.
    Calculates check dates and amounts based on contract terms.
    """
    try:
        with get_db_connection() as conn:
            result = generate_checks(conn)
            return {
                "message": "Check generation completed",
                "statistics": result
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/checks/upcoming")
def get_upcoming_payment_checks(days: int = 30):
    """
    Get checks that are due within the specified number of days.

    Args:
        days: Number of days to look ahead (default: 30, max: 365)
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

    try:
        with get_db_connection() as conn:
            checks = get_upcoming_checks(conn, days_ahead=days)
            return {
                "count": len(checks),
                "days_ahead": days,
                "checks": checks
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/checks/overdue")
def get_overdue_payment_checks():
    """
    Get all checks that are past their due date.
    """
    try:
        with get_db_connection() as conn:
            checks = get_overdue_checks(conn)
            return {
                "count": len(checks),
                "checks": checks
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Alert endpoints
@app.get("/api/v1/alerts/expiring")
def get_expiring_contracts(days: int = 100):
    """
    Get contracts that are expiring within the specified number of days.

    Args:
        days: Number of days before expiry to alert (default: 100, max: 365)
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")

    try:
        with get_db_connection() as conn:
            alerts = get_alerts(conn, alert_days=days)
            return {
                "count": len(alerts),
                "alert_threshold_days": days,
                "expiring_contracts": alerts
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Tenant endpoints
@app.post("/api/v1/tenants", status_code=201)
def create_tenant(tenant: TenantCreate):
    """
    Create a new tenant.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if email already exists
            cursor.execute("SELECT id FROM tenants WHERE email = %s", (tenant.email,))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Email already exists")

            # Insert tenant
            cursor.execute("""
                INSERT INTO tenants (name, email, phone)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (tenant.name, tenant.email, tenant.phone))

            tenant_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()

            return {
                "message": "Tenant created successfully",
                "tenant_id": tenant_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tenants")
def get_tenants():
    """
    Retrieve all tenants.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, phone FROM tenants ORDER BY name")
            tenants = cursor.fetchall()
            cursor.close()
            return {"count": len(tenants), "tenants": tenants}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tenants/{tenant_id}")
def get_tenant(tenant_id: int):
    """
    Retrieve a specific tenant with their contracts.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get tenant info
            cursor.execute(
                "SELECT id, name, email, phone FROM tenants WHERE id = %s",
                (tenant_id,)
            )
            tenant = cursor.fetchone()

            if not tenant:
                raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")

            # Get tenant's contracts
            cursor.execute("""
                SELECT id, property_name, location, start_date, expiry_date,
                       annual_rent, num_checks, payment_method
                FROM contracts
                WHERE tenant_id = %s
                ORDER BY start_date DESC
            """, (tenant_id,))

            contracts = cursor.fetchall()
            cursor.close()

            return {
                "tenant": tenant,
                "contracts_count": len(contracts),
                "contracts": contracts
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Statistics endpoint
@app.get("/api/v1/statistics")
def get_statistics():
    """
    Get overall system statistics.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total tenants
            cursor.execute("SELECT COUNT(*) FROM tenants")
            stats['total_tenants'] = cursor.fetchone()[0]

            # Total contracts
            cursor.execute("SELECT COUNT(*) FROM contracts")
            stats['total_contracts'] = cursor.fetchone()[0]

            # Active contracts (not expired)
            cursor.execute("SELECT COUNT(*) FROM contracts WHERE expiry_date >= CURRENT_DATE")
            stats['active_contracts'] = cursor.fetchone()[0]

            # Expired contracts
            cursor.execute("SELECT COUNT(*) FROM contracts WHERE expiry_date < CURRENT_DATE")
            stats['expired_contracts'] = cursor.fetchone()[0]

            # Total checks
            cursor.execute("SELECT COUNT(*) FROM checks")
            stats['total_checks'] = cursor.fetchone()[0]

            # Overdue checks
            cursor.execute("SELECT COUNT(*) FROM checks WHERE check_date < CURRENT_DATE")
            stats['overdue_checks'] = cursor.fetchone()[0]

            # Upcoming checks (next 30 days)
            cursor.execute("""
                SELECT COUNT(*) FROM checks
                WHERE check_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
            """)
            stats['upcoming_checks_30days'] = cursor.fetchone()[0]

            # Expiring contracts (next 100 days)
            cursor.execute("""
                SELECT COUNT(*) FROM contracts
                WHERE expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '100 days'
            """)
            stats['expiring_contracts_100days'] = cursor.fetchone()[0]

            cursor.close()

            return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
