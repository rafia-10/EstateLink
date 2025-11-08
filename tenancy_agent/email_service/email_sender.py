"""Base email sender module using SMTP"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from ..config import EMAIL_CONFIG

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
    """Send an email using SMTP

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text fallback (optional)

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['from_email']
        msg['To'] = to_email

        # Add plain text version
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))

        # Add HTML version
        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['smtp_username'], EMAIL_CONFIG['smtp_password'])
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def send_to_tenant_and_agent(tenant_email: str, agent_email: str, subject: str,
                              tenant_html: str, agent_html: str) -> bool:
    """Send emails to both tenant and agent

    Args:
        tenant_email: Tenant's email address
        agent_email: Agent's email address
        subject: Email subject
        tenant_html: HTML content for tenant
        agent_html: HTML content for agent

    Returns:
        True if at least one email sent successfully
    """
    tenant_sent = False
    agent_sent = False

    if tenant_email:
        tenant_sent = send_email(tenant_email, subject, tenant_html)

    if agent_email:
        agent_sent = send_email(agent_email, subject, agent_html)

    return tenant_sent or agent_sent
