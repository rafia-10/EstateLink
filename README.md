# EstateLink Tenancy Check & Alert Agent

Production-ready Python backend agent for managing tenancy contracts, payment checks, and expiry alerts.

## Overview

The EstateLink Agent provides three core functions:
1. **Contract Management** - Fetch and manage tenancy contracts
2. **Check Generation** - Automatically calculate and generate payment schedules
3. **Alert System** - Monitor contract expirations and overdue payments

## Architecture

```
estate_agent.py      → Core business logic (agent functions)
estate_api.py        → FastAPI REST API endpoints
estatelink_sample_data.sql → Sample data for testing
```

## Core Functions

### 1. `fetch_contracts(conn)`
Fetches all contracts with tenant information from the database.

**Returns:** List of contract dictionaries with tenant details

**Example:**
```python
import psycopg2
from estate_agent import fetch_contracts

conn = psycopg2.connect(
    dbname="estate_db",
    user="postgres",
    password="your_password",
    host="localhost"
)

contracts = fetch_contracts(conn)
for contract in contracts:
    print(f"Contract {contract['contract_id']}: {contract['property_name']}")
    print(f"Tenant: {contract['tenant_name']} ({contract['tenant_email']})")
    print(f"Expires: {contract['expiry_date']}")
```

### 2. `generate_checks(conn)`
Calculates payment check dates and amounts for all contracts, then inserts them into the database.

**Logic:**
- Divides contract period into equal intervals based on `num_checks`
- Calculates check amount: `annual_rent / num_checks`
- Generates unique check numbers: `CHK{contract_id:03d}{check_num:02d}`
- Skips checks that already exist

**Returns:** Dictionary with statistics
- `total_contracts`: Number of contracts processed
- `checks_generated`: New checks created
- `checks_skipped`: Existing checks found

**Example:**
```python
from estate_agent import generate_checks

result = generate_checks(conn)
print(f"Processed: {result['total_contracts']} contracts")
print(f"Generated: {result['checks_generated']} new checks")
print(f"Skipped: {result['checks_skipped']} existing checks")
```

### 3. `get_alerts(conn, alert_days=100)`
Retrieves contracts expiring within the specified number of days.

**Parameters:**
- `alert_days`: Number of days before expiry to trigger alert (default: 100)

**Returns:** List of contracts with expiry information including:
- Contract and property details
- Tenant contact information
- Days until expiry
- Agent details

**Example:**
```python
from estate_agent import get_alerts

# Get contracts expiring in next 100 days
alerts = get_alerts(conn, alert_days=100)

for alert in alerts:
    print(f"⚠️  Contract {alert['contract_id']} expiring in {alert['days_until_expiry']} days")
    print(f"   Property: {alert['property_name']}")
    print(f"   Tenant: {alert['tenant_name']} - {alert['tenant_email']}")
    print(f"   Agent: {alert['agent_name']} - {alert['agent_email']}")
```

## Additional Utility Functions

### `get_overdue_checks(conn)`
Returns checks where `check_date < today`.

```python
from estate_agent import get_overdue_checks

overdue = get_overdue_checks(conn)
for check in overdue:
    print(f"Overdue: {check['check_no']} - {check['days_overdue']} days")
    print(f"Amount: AED {check['amount']}")
    print(f"Tenant: {check['tenant_name']} - {check['tenant_phone']}")
```

### `get_upcoming_checks(conn, days_ahead=30)`
Returns checks due within specified days.

```python
from estate_agent import get_upcoming_checks

upcoming = get_upcoming_checks(conn, days_ahead=30)
for check in upcoming:
    print(f"{check['check_no']}: AED {check['amount']} due in {check['days_until_due']} days")
```

### `get_contract_summary(conn, contract_id)`
Returns complete contract details with all associated checks.

```python
from estate_agent import get_contract_summary

contract = get_contract_summary(conn, contract_id=1)
print(f"Contract ID: {contract['contract_id']}")
print(f"Total Checks: {contract['total_checks_count']}")
for check in contract['checks']:
    print(f"  - {check['check_no']}: AED {check['amount']} on {check['check_date']}")
```

## Database Setup

### 1. Create Database
```bash
createdb estate_db
```

### 2. Load Sample Data
```bash
psql -U postgres -d estate_db -f estatelink_sample_data.sql
```

This creates:
- **100 tenants** with realistic UAE names, emails, and phone numbers
- **100 contracts** across Dubai, Abu Dhabi, Sharjah, etc.
- **397 payment checks** automatically calculated

## FastAPI Integration

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Database
Create a `.env` file:
```env
DB_NAME=estate_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### Run API Server
```bash
python estate_api.py
```

Or with uvicorn:
```bash
uvicorn estate_api:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Get All Contracts
```bash
curl http://localhost:8000/api/v1/contracts
```

#### Get Specific Contract
```bash
curl http://localhost:8000/api/v1/contracts/1
```

#### Generate Checks
```bash
curl -X POST http://localhost:8000/api/v1/checks/generate
```

#### Get Expiry Alerts (100 days)
```bash
curl "http://localhost:8000/api/v1/alerts/expiring?days=100"
```

#### Get Upcoming Checks (30 days)
```bash
curl "http://localhost:8000/api/v1/checks/upcoming?days=30"
```

#### Get Overdue Checks
```bash
curl http://localhost:8000/api/v1/checks/overdue
```

#### Get System Statistics
```bash
curl http://localhost:8000/api/v1/statistics
```

#### Create New Tenant
```bash
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ahmed Al-Mansouri",
    "email": "ahmed.mansouri@example.com",
    "phone": "+971501234567"
  }'
```

#### Create New Contract
```bash
curl -X POST http://localhost:8000/api/v1/contracts \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "property_name": "2 Bedroom Apartment in Dubai Marina",
    "location": "Dubai Marina",
    "start_date": "2025-01-01",
    "expiry_date": "2026-01-01",
    "annual_rent": 85000,
    "num_checks": 4,
    "payment_method": "Cheque",
    "agent_name": "John Smith - Skyline Properties",
    "agent_email": "sales@skylineproperties.ae"
  }'
```

## API Documentation

Once the server is running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Payment Check Calculation Logic

For a 1-year contract with 4 checks:
```
Start Date: 2025-01-01
Expiry Date: 2026-01-01
Annual Rent: 100,000 AED
Num Checks: 4

Check Dates:
- Check 1: 2025-01-01 (0 months)   → 25,000 AED
- Check 2: 2025-04-01 (3 months)   → 25,000 AED
- Check 3: 2025-07-01 (6 months)   → 25,000 AED
- Check 4: 2025-10-01 (9 months)   → 25,000 AED
```

Calculation:
```python
total_days = (expiry_date - start_date).days  # 365 days
interval_days = total_days / num_checks       # 91.25 days
check_amount = annual_rent / num_checks       # 25,000 AED

for i in range(num_checks):
    check_date = start_date + timedelta(days=int(interval_days * i))
```

## Alert Logic

### Expiry Alerts
Triggered when: `today <= expiry_date <= today + alert_days`

Default: 100 days before expiry

### Overdue Checks
Any check where: `check_date < today`

## Production Deployment

### Environment Variables
```bash
export DB_NAME=estate_db
export DB_USER=postgres
export DB_PASSWORD=secure_password
export DB_HOST=db.production.com
export DB_PORT=5432
```

### Using Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY estate_agent.py estate_api.py .

CMD ["uvicorn", "estate_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### With Gunicorn (Production)
```bash
pip install gunicorn
gunicorn estate_api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Security Best Practices

1. **SQL Injection Prevention**: All queries use parameterized statements
2. **Environment Variables**: Never hardcode database credentials
3. **Input Validation**: Pydantic models validate all API inputs
4. **Error Handling**: Proper exception handling with logging
5. **Connection Management**: Context managers ensure proper cleanup

## Testing

### Test Check Generation
```python
import psycopg2
from estate_agent import generate_checks

conn = psycopg2.connect(dbname="estate_db", user="postgres", password="password")
result = generate_checks(conn)
print(result)
conn.close()
```

### Test Alert System
```python
from estate_agent import get_alerts

conn = psycopg2.connect(dbname="estate_db", user="postgres", password="password")
alerts = get_alerts(conn, alert_days=100)
print(f"Found {len(alerts)} expiring contracts")
conn.close()
```

## Logging

All functions use Python's logging module:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

Production logs include:
- Number of contracts fetched
- Check generation statistics
- Alert counts
- Error messages with stack traces

## Error Handling

All functions properly handle errors and rollback transactions on failure:
```python
try:
    result = generate_checks(conn)
except Exception as e:
    conn.rollback()
    logger.error(f"Error: {str(e)}")
    raise
```

## Data Validation

### Phone Number Format
Must match UAE format: `+971XXXXXXXXX`

### Payment Methods
Only accepts: `Bank Transfer`, `Cheque`, `Cash`

### Date Validation
- `expiry_date` must be after `start_date`
- Typically 1 year (365 days) contract period

### Number of Checks
Valid range: 1-12 checks per contract (typically 2, 4, or 6)

## Support

For issues or questions:
- Check logs for error details
- Verify database connection parameters
- Ensure sample data is loaded correctly
- Review PostgreSQL permissions

## License

Production-ready code for EstateLink platform.
