"""Contract-related functions"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from .utils import rows_to_dicts

logger = logging.getLogger(__name__)


def fetch_contracts(conn) -> List[Dict[str, Any]]:
    """Fetch all contracts with tenant information

    Args:
        conn: Database connection object

    Returns:
        List of dictionaries containing contract and tenant details

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id as contract_id, c.tenant_id, c.property_name, c.location,
                   c.start_date, c.expiry_date, c.annual_rent, c.num_checks,
                   c.payment_method, c.agent_name, c.agent_email,
                   t.name as tenant_name, t.email as tenant_email, t.phone as tenant_phone
            FROM contracts c
            INNER JOIN tenants t ON c.tenant_id = t.id
            ORDER BY c.start_date DESC
        """)

        contracts = rows_to_dicts([d[0] for d in cursor.description], cursor.fetchall())
        cursor.close()
        logger.info(f"Fetched {len(contracts)} contracts from database")
        return contracts
    except Exception as e:
        logger.error(f"Error fetching contracts: {str(e)}")
        raise


def get_alerts(conn, alert_days: int = 100) -> List[Dict[str, Any]]:
    """Get contracts expiring within specified days

    Args:
        conn: Database connection object
        alert_days: Number of days before expiry to trigger alert (default: 100)

    Returns:
        List of dictionaries containing contract details for contracts nearing expiry

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()
        today = datetime.now().date()
        threshold = today + timedelta(days=alert_days)

        cursor.execute("""
            SELECT c.id as contract_id, c.property_name, c.location, c.start_date, c.expiry_date,
                   c.annual_rent, c.num_checks, c.payment_method, c.agent_name, c.agent_email,
                   t.name as tenant_name, t.email as tenant_email, t.phone as tenant_phone,
                   (c.expiry_date - %s) as days_until_expiry
            FROM contracts c
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE c.expiry_date BETWEEN %s AND %s
            ORDER BY c.expiry_date ASC
        """, (today, today, threshold))

        alerts = rows_to_dicts([d[0] for d in cursor.description], cursor.fetchall(), ['days_until_expiry'])
        cursor.close()
        logger.info(f"Found {len(alerts)} contracts expiring within {alert_days} days")
        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        raise


def get_contract_summary(conn, contract_id: int) -> Optional[Dict[str, Any]]:
    """Get complete summary of a contract including all checks

    Args:
        conn: Database connection object
        contract_id: ID of the contract to retrieve

    Returns:
        Dictionary containing contract details and list of associated checks,
        or None if contract not found

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.id as contract_id, c.tenant_id, c.property_name, c.location,
                   c.start_date, c.expiry_date, c.annual_rent, c.num_checks,
                   c.payment_method, c.agent_name, c.agent_email,
                   t.name as tenant_name, t.email as tenant_email, t.phone as tenant_phone
            FROM contracts c
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE c.id = %s
        """, (contract_id,))

        row = cursor.fetchone()
        if not row:
            cursor.close()
            return None

        contract = dict(zip([d[0] for d in cursor.description], row))

        cursor.execute("""
            SELECT id, check_no, check_date, amount
            FROM checks WHERE contract_id = %s ORDER BY check_date ASC
        """, (contract_id,))

        checks = rows_to_dicts([d[0] for d in cursor.description], cursor.fetchall())
        contract['checks'] = checks
        contract['total_checks_count'] = len(checks)

        cursor.close()
        logger.info(f"Retrieved contract {contract_id} with {len(checks)} checks")
        return contract
    except Exception as e:
        logger.error(f"Error fetching contract summary: {str(e)}")
        raise
