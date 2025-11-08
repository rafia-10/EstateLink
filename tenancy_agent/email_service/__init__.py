"""Email Service Package for EstateLink Tenancy Management

This package handles all email notifications including:
- Contract expiry alerts
- Overdue payment notifications
- Upcoming payment reminders

Each email type sends to both tenant and agent.
"""

from .contract_expiry import (
    send_contract_expiry_alert,
    send_batch_contract_expiry_alerts
)
from .overdue_payment import (
    send_overdue_payment_alert,
    send_batch_overdue_payment_alerts
)
from .upcoming_payment import (
    send_upcoming_payment_reminder,
    send_batch_upcoming_payment_reminders
)

__all__ = [
    # Contract expiry
    'send_contract_expiry_alert',
    'send_batch_contract_expiry_alerts',

    # Overdue payments
    'send_overdue_payment_alert',
    'send_batch_overdue_payment_alerts',

    # Upcoming payments
    'send_upcoming_payment_reminder',
    'send_batch_upcoming_payment_reminders',
]
