"""Upcoming payment reminder email notifications"""
import logging
from typing import Dict, Any, List
from .email_sender import send_to_tenant_and_agent
from .templates import base_email_template, info_box, contact_box

logger = logging.getLogger(__name__)


def send_upcoming_payment_reminder(check: Dict[str, Any]) -> bool:
    """Send upcoming payment reminder to tenant and agent

    Args:
        check: Check dictionary with payment and tenant details

    Returns:
        True if emails sent successfully
    """
    days_until_due = check.get('days_until_due', 0)
    subject = f"Payment Reminder - {check['property_name']}"

    # Tenant email content
    tenant_content = f"""
        <p>Dear {check['tenant_name']},</p>
        <p>This is a friendly reminder that a payment is due soon.</p>

        {info_box("Payment Details", {
            "Property": check['property_name'],
            "Location": check['location'],
            "Check Number": check['check_no'],
            "Amount Due": f"AED {check['amount']:,.2f}",
            "Due Date": check['check_date'],
            "Days Until Due": f"{days_until_due} days"
        }, color="#3498db")}

        <p>Please ensure payment is made by the due date to avoid late fees.</p>

        {contact_box(check['agent_name'], check['agent_email'])}
    """

    # Agent email content
    agent_content = f"""
        <p>Dear {check['agent_name']},</p>
        <p>The following payment is due in {days_until_due} days:</p>

        {info_box("Payment Details", {
            "Property": check['property_name'],
            "Location": check['location'],
            "Tenant": check['tenant_name'],
            "Tenant Email": check['tenant_email'],
            "Tenant Phone": check['tenant_phone'],
            "Check Number": check['check_no'],
            "Amount": f"AED {check['amount']:,.2f}",
            "Due Date": check['check_date']
        }, color="#3498db")}

        <p>Tenant has been notified. Please follow up if needed.</p>
    """

    tenant_html = base_email_template("Payment Reminder", tenant_content, color="#3498db")
    agent_html = base_email_template("Upcoming Payment Reminder", agent_content, color="#3498db")

    return send_to_tenant_and_agent(
        tenant_email=check.get('tenant_email'),
        agent_email=check.get('agent_email'),
        subject=subject,
        tenant_html=tenant_html,
        agent_html=agent_html
    )


def send_batch_upcoming_payment_reminders(checks: List[Dict[str, Any]]) -> Dict[str, int]:
    """Send upcoming payment reminders for multiple checks

    Args:
        checks: List of check dictionaries

    Returns:
        Dictionary with success and failure counts
    """
    stats = {'total': len(checks), 'success': 0, 'failed': 0}

    for check in checks:
        if send_upcoming_payment_reminder(check):
            stats['success'] += 1
        else:
            stats['failed'] += 1

    logger.info(f"Upcoming payment reminders: {stats}")
    return stats
