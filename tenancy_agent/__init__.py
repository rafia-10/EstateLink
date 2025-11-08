"""EstateLink Tenancy Agent Package

A modular tenancy management system for handling contracts, payment checks, and expiry alerts.

Modules:
    - database: Supabase connection and cursor implementation
    - contracts: Contract-related operations
    - checks: Payment check operations
    - utils: Utility functions
    - config: Configuration settings
"""

from .database import SupabaseConnection
from .contracts import fetch_contracts, get_alerts, get_contract_summary
from .checks import generate_checks, get_overdue_checks, get_upcoming_checks

__all__ = [
    'SupabaseConnection',
    'fetch_contracts',
    'get_alerts',
    'get_contract_summary',
    'generate_checks',
    'get_overdue_checks',
    'get_upcoming_checks',
]
