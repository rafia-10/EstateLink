"""Contract expiry email notifications"""
import logging
from typing import Dict, Any, List
from .email_sender import send_to_tenant_and_agent
from .templates import base_email_template, info_box, contact_box

logger = logging.getLogger(__name__)


def send_contract_expiry_alert(contract: Dict[str, Any]) -> bool:
    """Send contract expiry alert to tenant and agent

    Args:
        contract: Contract dictionary with tenant and expiry details

    Returns:
        True if emails sent successfully
    """
    days_until_expiry = contract.get('days_until_expiry', 0)
    subject = f"Contract Expiry Alert - {contract['property_name']}"

    # Tenant email content
    tenant_content = f"""
        <p>Dear {contract['tenant_name']},</p>
        <p>This is to inform you that your tenancy contract is expiring soon.</p>

        {info_box("Contract Details", {
            "Property": contract['property_name'],
            "Location": contract['location'],
            "Expiry Date": contract['expiry_date'],
            "Days Until Expiry": f"{days_until_expiry} days",
            "Annual Rent": f"AED {contract['annual_rent']:,.2f}"
        }, color="#e74c3c")}

        <p>Please contact your agent to discuss renewal or move-out arrangements.</p>

        {contact_box(contract['agent_name'], contract['agent_email'])}
    """

    # Agent email content
    agent_content = f"""
        <p>Dear {contract['agent_name']},</p>
        <p>The following contract is expiring in {days_until_expiry} days:</p>

        {info_box("Contract Details", {
            "Property": contract['property_name'],
            "Location": contract['location'],
            "Tenant": contract['tenant_name'],
            "Tenant Email": contract['tenant_email'],
            "Tenant Phone": contract['tenant_phone'],
            "Expiry Date": contract['expiry_date'],
            "Annual Rent": f"AED {contract['annual_rent']:,.2f}"
        }, color="#e74c3c")}

        <p>Please follow up with the tenant regarding renewal or move-out.</p>
    """

    tenant_html = base_email_template("Contract Expiry Notice", tenant_content, color="#e74c3c")
    agent_html = base_email_template("Contract Expiry Alert", agent_content, color="#e74c3c")

    return send_to_tenant_and_agent(
        tenant_email=contract.get('tenant_email'),
        agent_email=contract.get('agent_email'),
        subject=subject,
        tenant_html=tenant_html,
        agent_html=agent_html
    )


def send_batch_contract_expiry_alerts(contracts: List[Dict[str, Any]]) -> Dict[str, int]:
    """Send expiry alerts for multiple contracts

    Args:
        contracts: List of contract dictionaries

    Returns:
        Dictionary with success and failure counts
    """
    stats = {'total': len(contracts), 'success': 0, 'failed': 0}

    for contract in contracts:
        if send_contract_expiry_alert(contract):
            stats['success'] += 1
        else:
            stats['failed'] += 1

    logger.info(f"Contract expiry alerts: {stats}")
    return stats
