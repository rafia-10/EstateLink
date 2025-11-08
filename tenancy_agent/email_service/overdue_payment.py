"""Overdue payment email notifications"""
import logging
from typing import Dict, Any, List
from .email_sender import send_to_tenant_and_agent
from .templates import base_email_template, info_box, contact_box, alert_message

logger = logging.getLogger(__name__)


def send_overdue_payment_alert(check: Dict[str, Any]) -> bool:
    """Send overdue payment alert to tenant and agent

    Args:
        check: Check dictionary with payment and tenant details

    Returns:
        True if emails sent successfully
    """
    days_overdue = check.get('days_overdue', 0)
    subject = f"URGENT: Overdue Payment - {check['property_name']}"

    # Tenant email content
    tenant_content = f"""
        <p>Dear {check['tenant_name']},</p>

        {alert_message("This is an urgent notice regarding an overdue payment.", "danger")}

        {info_box("Payment Details", {
            "Property": check['property_name'],
            "Location": check['location'],
            "Check Number": check['check_no'],
            "Amount Due": f"AED {check['amount']:,.2f}",
            "Due Date": check['check_date'],
            "Days Overdue": f"{days_overdue} days"
        }, color="#c0392b")}

        <p>Please arrange payment immediately to avoid late fees and legal action.</p>

        {contact_box(check['agent_name'], check['agent_email'])}
    """

    # Agent email content
    agent_content = f"""
        <p>Dear {check['agent_name']},</p>

        {alert_message(f"The following payment is {days_overdue} days overdue.", "danger")}

        {info_box("Payment Details", {
            "Property": check['property_name'],
            "Location": check['location'],
            "Tenant": check['tenant_name'],
            "Tenant Email": check['tenant_email'],
            "Tenant Phone": check['tenant_phone'],
            "Check Number": check['check_no'],
            "Amount": f"AED {check['amount']:,.2f}",
            "Due Date": check['check_date'],
            "Days Overdue": f"{days_overdue} days"
        }, color="#c0392b")}

        <p>Please follow up with the tenant immediately.</p>
    """

    tenant_html = base_email_template("OVERDUE PAYMENT NOTICE", tenant_content, color="#c0392b")
    agent_html = base_email_template("Overdue Payment Alert", agent_content, color="#c0392b")

    return send_to_tenant_and_agent(
        tenant_email=check.get('tenant_email'),
        agent_email=check.get('agent_email'),
        subject=subject,
        tenant_html=tenant_html,
        agent_html=agent_html
    )


def send_batch_overdue_payment_alerts(checks: List[Dict[str, Any]]) -> Dict[str, int]:
    """Send overdue payment alerts for multiple checks

    Args:
        checks: List of check dictionaries

    Returns:
        Dictionary with success and failure counts
    """
    stats = {'total': len(checks), 'success': 0, 'failed': 0}

    for check in checks:
        if send_overdue_payment_alert(check):
            stats['success'] += 1
        else:
            stats['failed'] += 1

    logger.info(f"Overdue payment alerts: {stats}")
    return stats
