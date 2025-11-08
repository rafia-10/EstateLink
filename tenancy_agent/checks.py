"""Check-related functions"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import logging
from .utils import rows_to_dicts

logger = logging.getLogger(__name__)


def generate_checks(conn) -> Dict[str, Any]:
    """Generate payment checks for all contracts

    Args:
        conn: Database connection object

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
        cursor.execute("SELECT id, start_date, expiry_date, annual_rent, num_checks FROM contracts ORDER BY id")
        contracts = cursor.fetchall()

        stats = {"total_contracts": len(contracts), "checks_generated": 0, "checks_skipped": 0}

        for cid, start, end, rent, num in contracts:
            # Check existing
            cursor.execute("SELECT COUNT(*) FROM checks WHERE contract_id = %s", (cid,))
            existing = cursor.fetchone()[0]

            if existing >= num:
                stats["checks_skipped"] += existing
                logger.debug(f"Contract {cid} already has {existing} checks, skipping")
                continue

            # Calculate and insert
            amount = round(Decimal(str(rent)) / Decimal(str(num)), 2)
            interval = (end - start).days / num

            for i in range(num):
                check_no = f"CHK{cid:03d}{i+1:02d}"
                cursor.execute("SELECT id FROM checks WHERE check_no = %s", (check_no,))

                if cursor.fetchone():
                    stats["checks_skipped"] += 1
                    continue

                check_date = start + timedelta(days=int(interval * i))
                cursor.execute(
                    "INSERT INTO checks (contract_id, check_no, check_date, amount) VALUES (%s, %s, %s, %s)",
                    (cid, check_no, check_date, amount)
                )
                stats["checks_generated"] += 1

        conn.commit()
        cursor.close()
        logger.info(f"Check generation complete: {stats}")
        return stats
    except Exception as e:
        conn.rollback()
        logger.error(f"Error generating checks: {str(e)}")
        raise


def get_overdue_checks(conn) -> List[Dict[str, Any]]:
    """Get all overdue checks

    Args:
        conn: Database connection object

    Returns:
        List of dictionaries containing overdue check details with contract and tenant info

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()
        today = datetime.now().date()

        cursor.execute("""
            SELECT ch.id as check_id, ch.check_no, ch.check_date, ch.amount,
                   c.id as contract_id, c.property_name, c.location,
                   t.name as tenant_name, t.email as tenant_email, t.phone as tenant_phone,
                   c.agent_name, c.agent_email, (%s - ch.check_date) as days_overdue
            FROM checks ch
            INNER JOIN contracts c ON ch.contract_id = c.id
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE ch.check_date < %s
            ORDER BY ch.check_date ASC
        """, (today, today))

        checks = rows_to_dicts([d[0] for d in cursor.description], cursor.fetchall(), ['days_overdue'])
        cursor.close()
        logger.info(f"Found {len(checks)} overdue checks")
        return checks
    except Exception as e:
        logger.error(f"Error fetching overdue checks: {str(e)}")
        raise


def get_upcoming_checks(conn, days_ahead: int = 30) -> List[Dict[str, Any]]:
    """Get checks due within specified days

    Args:
        conn: Database connection object
        days_ahead: Number of days to look ahead (default: 30)

    Returns:
        List of dictionaries containing upcoming check details

    Raises:
        Exception: If database query fails
    """
    try:
        cursor = conn.cursor()
        today = datetime.now().date()
        future = today + timedelta(days=days_ahead)

        cursor.execute("""
            SELECT ch.id as check_id, ch.check_no, ch.check_date, ch.amount,
                   c.id as contract_id, c.property_name, c.location,
                   t.name as tenant_name, t.email as tenant_email, t.phone as tenant_phone,
                   c.agent_name, c.agent_email, (ch.check_date - %s) as days_until_due
            FROM checks ch
            INNER JOIN contracts c ON ch.contract_id = c.id
            INNER JOIN tenants t ON c.tenant_id = t.id
            WHERE ch.check_date BETWEEN %s AND %s
            ORDER BY ch.check_date ASC
        """, (today, today, future))

        checks = rows_to_dicts([d[0] for d in cursor.description], cursor.fetchall(), ['days_until_due'])
        cursor.close()
        logger.info(f"Found {len(checks)} checks due within {days_ahead} days")
        return checks
    except Exception as e:
        logger.error(f"Error fetching upcoming checks: {str(e)}")
        raise
