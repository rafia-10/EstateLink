"""
EstateLink Tenancy Check & Alert Agent
Production-ready agent for managing tenancy contracts, check schedules, and expiry alerts.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_contracts(conn) -> List[Dict[str, Any]]:
    """
    Fetch all contracts with tenant information from the database.

    Args:
        conn: PostgreSQL database connection object

    Returns:
        List of dictionaries containing contract and tenant details

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()

        query = """
            SELECT
                c.id as contract_id,
                c.tenant_id,
                c.property_name,
                c.location,
                c.start_date,
                c.expiry_date,
                c.annual_rent,
                c.num_checks,
                c.payment_method,
                c.agent_name,
                c.agent_email,
                t.name as tenant_name,
                t.email as tenant_email,
                t.phone as tenant_phone
            FROM contracts c
            INNER JOIN tenants t ON c.tenant_id = t.id
            ORDER BY c.start_date DESC
        """

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        contracts = []
        for row in results:
            contract = dict(zip(columns, row))
            contracts.append(contract)

        cursor.close()
        logger.info(f"Fetched {len(contracts)} contracts from database")

        return contracts

    except Exception as e:
        logger.error(f"Error fetching contracts: {str(e)}")
        raise


def generate_checks(conn) -> Dict[str, Any]:
    """
    Generate payment checks for all contracts and insert them into the checks table.

    Calculates check dates evenly distributed between start_date and expiry_date,
    and check amounts as annual_rent / num_checks.

    Args:
        conn: PostgreSQL database connection object

    Returns:
        Dictionary with generation statistics:
            - total_contracts: Number of contracts processed
            - checks_generated: Number of checks created
            - checks_skipped: Number of checks already existing

    Raises:
        Exception: If database operations fail
    """
    try:
        cursor = conn.cursor()

        # Fetch all contracts
        cursor.execute("""
            SELECT id, start_date, expiry_date, annual_rent, num_checks
            FROM contracts
            ORDER BY id
        """)

        contracts = cursor.fetchall()
        total_contracts = len(contracts)
        checks_generated = 0
        checks_skipped = 0

        for contract in contracts:
            contract_id, start_date, expiry_date, annual_rent, num_checks = contract

            # Check if checks already exist for this contract
            cursor.execute(
                "SELECT COUNT(*) FROM checks WHERE contract_id = %s",
                (contract_id,)
            )
            existing_count = cursor.fetchone()[0]

            if existing_count >= num_checks:
                checks_skipped += existing_count
                logger.debug(f"Contract {contract_id} already has {existing_count} checks, skipping")
                continue

            # Calculate check amount
            check_amount = Decimal(str(annual_rent)) / Decimal(str(num_checks))
            check_amount = round(check_amount, 2)

            # Calculate total contract days
            total_days = (expiry_date - start_date).days
            interval_days = total_days / num_checks

            # Generate checks
            for i in range(num_checks):
                # Calculate check date (evenly distributed)
                days_offset = int(interval_days * i)
                check_date = start_date + timedelta(days=days_offset)

                # Generate check number
                check_no = f"CHK{contract_id:03d}{i+1:02d}"

                # Check if this specific check already exists
                cursor.execute(
                    "SELECT id FROM checks WHERE check_no = %s",
                    (check_no,)
                )

                if cursor.fetchone():
                    checks_skipped += 1
                    continue

                # Insert check
                cursor.execute(
                    """
                    INSERT INTO checks (contract_id, check_no, check_date, amount)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (contract_id, check_no, check_date, check_amount)
                )

                checks_generated += 1

        # Commit all inserts
        conn.commit()
        cursor.close()

        result = {
            "total_contracts": total_contracts,
            "checks_generated": checks_generated,
            "checks_skipped": checks_skipped
        }

        logger.info(f"Check generation complete: {result}")
        return result

    except Exception as e:
        conn.rollback()
        logger.error(f"Error generating checks: {str(e)}")
        raise


def get_alerts(conn, alert_days: int = 100) -> List[Dict[str, Any]]:
    """
    Get contracts that are expiring within the specified alert period.

    Args:
        conn: PostgreSQL database connection object
        alert_days: Number of days before expiry to trigger alert (default: 100)

    Returns:
        List of dictionaries containing contract details for contracts nearing expiry:
            - contract_id
            - tenant details (name, email, phone)
            - property details (name, location)
            - expiry_date
            - days_until_expiry
            - agent details (name, email)

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()

        # Calculate alert date threshold
        today = datetime.now().date()
        alert_threshold = today + timedelta(days=alert_days)

        query = """
            SELECT
                c.id as contract_id,
                c.property_name,
                c.location,
                c.start_date,
                c.expiry_date,
                c.annual_rent,
                c.num_checks,
                c.payment_method,
                c.agent_name,
                c.agent_email,
                t.name as tenant_name,
                t.email as tenant_email,
                t.phone as tenant_phone,
                (c.expiry_date - %s) as days_until_expiry
            FROM contracts c
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE c.expiry_date BETWEEN %s AND %s
            ORDER BY c.expiry_date ASC
        """

        cursor.execute(query, (today, today, alert_threshold))
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        alerts = []
        for row in results:
            alert = dict(zip(columns, row))
            # Convert days_until_expiry from timedelta to integer
            if isinstance(alert.get('days_until_expiry'), timedelta):
                alert['days_until_expiry'] = alert['days_until_expiry'].days
            alerts.append(alert)

        cursor.close()
        logger.info(f"Found {len(alerts)} contracts expiring within {alert_days} days")

        return alerts

    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        raise


def get_overdue_checks(conn) -> List[Dict[str, Any]]:
    """
    Get all checks that are overdue (check_date has passed but not marked as paid).

    Note: This assumes you'll add a 'paid' status field later. Currently returns
    checks where check_date < today for monitoring purposes.

    Args:
        conn: PostgreSQL database connection object

    Returns:
        List of dictionaries containing overdue check details with contract and tenant info

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()
        today = datetime.now().date()

        query = """
            SELECT
                ch.id as check_id,
                ch.check_no,
                ch.check_date,
                ch.amount,
                c.id as contract_id,
                c.property_name,
                c.location,
                t.name as tenant_name,
                t.email as tenant_email,
                t.phone as tenant_phone,
                c.agent_name,
                c.agent_email,
                (%s - ch.check_date) as days_overdue
            FROM checks ch
            INNER JOIN contracts c ON ch.contract_id = c.id
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE ch.check_date < %s
            ORDER BY ch.check_date ASC
        """

        cursor.execute(query, (today, today))
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        overdue_checks = []
        for row in results:
            check = dict(zip(columns, row))
            # Convert days_overdue from timedelta to integer
            if isinstance(check.get('days_overdue'), timedelta):
                check['days_overdue'] = check['days_overdue'].days
            overdue_checks.append(check)

        cursor.close()
        logger.info(f"Found {len(overdue_checks)} overdue checks")

        return overdue_checks

    except Exception as e:
        logger.error(f"Error fetching overdue checks: {str(e)}")
        raise


def get_contract_summary(conn, contract_id: int) -> Optional[Dict[str, Any]]:
    """
    Get complete summary of a specific contract including all checks.

    Args:
        conn: PostgreSQL database connection object
        contract_id: ID of the contract to retrieve

    Returns:
        Dictionary containing contract details and list of associated checks,
        or None if contract not found

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()

        # Fetch contract with tenant info
        cursor.execute("""
            SELECT
                c.id as contract_id,
                c.tenant_id,
                c.property_name,
                c.location,
                c.start_date,
                c.expiry_date,
                c.annual_rent,
                c.num_checks,
                c.payment_method,
                c.agent_name,
                c.agent_email,
                t.name as tenant_name,
                t.email as tenant_email,
                t.phone as tenant_phone
            FROM contracts c
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE c.id = %s
        """, (contract_id,))

        contract_row = cursor.fetchone()

        if not contract_row:
            cursor.close()
            return None

        columns = [desc[0] for desc in cursor.description]
        contract = dict(zip(columns, contract_row))

        # Fetch all checks for this contract
        cursor.execute("""
            SELECT id, check_no, check_date, amount
            FROM checks
            WHERE contract_id = %s
            ORDER BY check_date ASC
        """, (contract_id,))

        check_columns = [desc[0] for desc in cursor.description]
        check_rows = cursor.fetchall()

        checks = []
        for row in check_rows:
            checks.append(dict(zip(check_columns, row)))

        contract['checks'] = checks
        contract['total_checks_count'] = len(checks)

        cursor.close()
        logger.info(f"Retrieved contract {contract_id} with {len(checks)} checks")

        return contract

    except Exception as e:
        logger.error(f"Error fetching contract summary: {str(e)}")
        raise


# Additional utility functions

def get_upcoming_checks(conn, days_ahead: int = 30) -> List[Dict[str, Any]]:
    """
    Get checks that are due within the specified number of days.

    Args:
        conn: PostgreSQL database connection object
        days_ahead: Number of days to look ahead (default: 30)

    Returns:
        List of dictionaries containing upcoming check details

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()
        today = datetime.now().date()
        future_date = today + timedelta(days=days_ahead)

        query = """
            SELECT
                ch.id as check_id,
                ch.check_no,
                ch.check_date,
                ch.amount,
                c.id as contract_id,
                c.property_name,
                c.location,
                t.name as tenant_name,
                t.email as tenant_email,
                t.phone as tenant_phone,
                c.agent_name,
                c.agent_email,
                (ch.check_date - %s) as days_until_due
            FROM checks ch
            INNER JOIN contracts c ON ch.contract_id = c.id
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE ch.check_date BETWEEN %s AND %s
            ORDER BY ch.check_date ASC
        """

        cursor.execute(query, (today, today, future_date))
        columns = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()

        upcoming = []
        for row in results:
            check = dict(zip(columns, row))
            if isinstance(check.get('days_until_due'), timedelta):
                check['days_until_due'] = check['days_until_due'].days
            upcoming.append(check)

        cursor.close()
        logger.info(f"Found {len(upcoming)} checks due within {days_ahead} days")

        return upcoming

    except Exception as e:
        logger.error(f"Error fetching upcoming checks: {str(e)}")
        raise


if __name__ == "__main__":
    """
    Example usage (for testing purposes)
    """
    import psycopg2

    # Example connection parameters
    # Replace with your actual database credentials
    conn_params = {
        "dbname": "estate_db",
        "user": "postgres",
        "password": "your_password",
        "host": "localhost",
        "port": 5432
    }

    try:
        # Establish connection
        conn = psycopg2.connect(**conn_params)

        print("=" * 60)
        print("EstateLink Tenancy Check & Alert Agent - Test Run")
        print("=" * 60)

        # Test 1: Fetch all contracts
        print("\n[1] Fetching all contracts...")
        contracts = fetch_contracts(conn)
        print(f"    Found {len(contracts)} contracts")

        # Test 2: Generate checks
        print("\n[2] Generating payment checks...")
        check_stats = generate_checks(conn)
        print(f"    Contracts processed: {check_stats['total_contracts']}")
        print(f"    Checks generated: {check_stats['checks_generated']}")
        print(f"    Checks skipped: {check_stats['checks_skipped']}")

        # Test 3: Get expiry alerts
        print("\n[3] Getting expiry alerts (100 days)...")
        alerts = get_alerts(conn)
        print(f"    Found {len(alerts)} contracts expiring soon")
        if alerts:
            print(f"    Next expiry: {alerts[0]['property_name']} on {alerts[0]['expiry_date']}")

        # Test 4: Get upcoming checks
        print("\n[4] Getting upcoming checks (30 days)...")
        upcoming = get_upcoming_checks(conn, days_ahead=30)
        print(f"    Found {len(upcoming)} upcoming checks")

        # Test 5: Get overdue checks
        print("\n[5] Getting overdue checks...")
        overdue = get_overdue_checks(conn)
        print(f"    Found {len(overdue)} overdue checks")

        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)

        conn.close()

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
