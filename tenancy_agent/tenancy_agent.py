"""EstateLink Tenancy Check & Alert Agent - Main Module

This is the main entry point for the tenancy management system.
It orchestrates all tenancy-related operations including:
- Contract management and expiry alerts
- Payment check generation and tracking
- Overdue and upcoming payment notifications
"""
import logging
from .database import SupabaseConnection
from .contracts import fetch_contracts, get_alerts, get_contract_summary
from .checks import generate_checks, get_overdue_checks, get_upcoming_checks

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main execution function"""
    logger.info("Starting EstateLink Tenancy Agent")

    # Initialize connection
    conn = SupabaseConnection()

    try:
        # Fetch all contracts
        logger.info("\n=== FETCHING CONTRACTS ===")
        contracts = fetch_contracts(conn)
        logger.info(f"Total contracts: {len(contracts)}")

        # Generate payment checks
        logger.info("\n=== GENERATING CHECKS ===")
        check_stats = generate_checks(conn)
        logger.info(f"Generation stats: {check_stats}")

        # Get expiry alerts
        logger.info("\n=== CHECKING CONTRACT EXPIRY ALERTS ===")
        alerts = get_alerts(conn, alert_days=100)
        logger.info(f"Contracts expiring soon: {len(alerts)}")

        # Get upcoming checks
        logger.info("\n=== CHECKING UPCOMING PAYMENTS ===")
        upcoming = get_upcoming_checks(conn, days_ahead=30)
        logger.info(f"Upcoming checks (30 days): {len(upcoming)}")

        # Get overdue checks
        logger.info("\n=== CHECKING OVERDUE PAYMENTS ===")
        overdue = get_overdue_checks(conn)
        logger.info(f"Overdue checks: {len(overdue)}")

        # Sample contract summary
        if contracts:
            logger.info("\n=== SAMPLE CONTRACT SUMMARY ===")
            summary = get_contract_summary(conn, contracts[0]['contract_id'])
            if summary:
                logger.info(f"Contract ID: {summary['contract_id']}")
                logger.info(f"Property: {summary['property_name']}")
                logger.info(f"Total checks: {summary['total_checks_count']}")

        logger.info("\n=== AGENT EXECUTION COMPLETE ===")

        return {
            'total_contracts': len(contracts),
            'check_stats': check_stats,
            'expiry_alerts': len(alerts),
            'upcoming_checks': len(upcoming),
            'overdue_checks': len(overdue)
        }

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    results = main()
    print("\n" + "="*50)
    print("FINAL SUMMARY")
    print("="*50)
    for key, value in results.items():
        print(f"{key}: {value}")
