"""
Follow-up / callback notification sender.

Sends a plain-text email notification (via Gmail SMTP using an App Password)
when a caller requests a follow-up, callback, or more information.

This module is intentionally self-contained and defensive: send_followup_email
NEVER raises. All errors are caught and logged so that a notification failure
can never affect a live phone call.

Required environment variables:
    GMAIL_ADDRESS        - the Gmail account used to authenticate / send
    GMAIL_APP_PASSWORD   - 16-char Gmail App Password (spaces removed)
    FOLLOWUP_EMAIL_TO    - recipient inbox for follow-up notifications
"""

import os
import ssl
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import Dict, Any


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _val(data: Dict[str, Any], key: str) -> str:
    """Return a human-friendly value, or 'Not provided' when missing/empty."""
    v = data.get(key)
    if v is None:
        return "Not provided"
    v = str(v).strip()
    return v if v else "Not provided"


def _build_message(followup: Dict[str, Any], sender: str, recipient: str) -> EmailMessage:
    """Build the plain-text follow-up notification email."""
    name = _val(followup, "caller_name")
    request_type = _val(followup, "request_type")
    if request_type == "Not provided":
        request_type = "callback"

    subject = f"New follow-up request from {name} — {request_type}"

    received = followup.get("created_at") or datetime.now().isoformat()

    body = (
        "A caller has requested a follow-up.\n\n"
        f"Name: {name}\n"
        f"Phone: {_val(followup, 'caller_phone')}\n"
        f"Request type: {request_type}\n"
        f"Service or course of interest: {_val(followup, 'service_interest')}\n"
        f"Preferred callback time: {_val(followup, 'preferred_callback_time')}\n"
        f"Summary: {_val(followup, 'summary')}\n\n"
        f"Received: {received}\n"
        f"Call reference: {_val(followup, 'call_sid')}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)
    return msg


def send_followup_email(followup: Dict[str, Any]) -> bool:
    """
    Send a plain-text follow-up notification email.

    Returns True on success, False on any failure. Never raises.
    The Gmail App Password is never logged.
    """
    try:
        sender = (os.environ.get("GMAIL_ADDRESS") or "").strip()
        password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
        recipient = (os.environ.get("FOLLOWUP_EMAIL_TO") or sender).strip()

        if not sender or not password:
            print("Follow-up email NOT sent: GMAIL_ADDRESS or GMAIL_APP_PASSWORD not configured")
            return False
        if not recipient:
            print("Follow-up email NOT sent: no recipient configured")
            return False

        msg = _build_message(followup, sender, recipient)

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, password)
            server.send_message(msg)

        print(f"Follow-up email sent to {recipient}")
        return True

    except Exception as e:
        # Never let an email failure propagate into the call flow.
        print(f"Follow-up email error: {repr(e)}")
        return False
