"""Email HTML templates for EstateLink notifications"""
from typing import Dict, Any


def base_email_template(title: str, content: str, color: str = "#667eea") -> str:
    """Base HTML template for all emails

    Args:
        title: Email title/heading
        content: Main content HTML
        color: Header color (default: purple)

    Returns:
        Complete HTML email
    """
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: {color};">{title}</h2>
                {content}
                <p style="margin-top: 30px; font-size: 0.9em; color: #666;">
                    This is an automated notification from EstateLink Property Management System.
                </p>
            </div>
        </body>
    </html>
    """


def info_box(title: str, items: Dict[str, Any], color: str = "#3498db") -> str:
    """Create an info box with key-value pairs

    Args:
        title: Box title
        items: Dictionary of label-value pairs
        color: Border color

    Returns:
        HTML info box
    """
    items_html = "".join([
        f"<p><strong>{label}:</strong> {value}</p>"
        for label, value in items.items()
    ])

    return f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid {color}; margin: 20px 0;">
        <h3 style="margin-top: 0;">{title}</h3>
        {items_html}
    </div>
    """


def contact_box(name: str, email: str, phone: str = None) -> str:
    """Create a contact information box

    Args:
        name: Contact name
        email: Contact email
        phone: Contact phone (optional)

    Returns:
        HTML contact box
    """
    phone_html = f"<p><strong>Phone:</strong> {phone}</p>" if phone else ""

    return f"""
    <div style="margin-top: 20px; padding: 15px; background-color: #e8f4f8; border-radius: 5px;">
        <h4 style="margin-top: 0;">Agent Contact:</h4>
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> {email}</p>
        {phone_html}
    </div>
    """


def alert_message(message: str, alert_type: str = "info") -> str:
    """Create an alert/warning message

    Args:
        message: Alert message
        alert_type: Type of alert (info, warning, danger, success)

    Returns:
        HTML alert box
    """
    colors = {
        "info": "#3498db",
        "warning": "#f59e0b",
        "danger": "#c0392b",
        "success": "#10b981"
    }
    bg_colors = {
        "info": "#dbeafe",
        "warning": "#fff3cd",
        "danger": "#fee",
        "success": "#d1fae5"
    }

    color = colors.get(alert_type, "#3498db")
    bg_color = bg_colors.get(alert_type, "#dbeafe")

    return f"""
    <div style="padding: 15px; background-color: {bg_color}; border-left: 4px solid {color}; margin: 20px 0; border-radius: 5px;">
        <p style="margin: 0;">{message}</p>
    </div>
    """
