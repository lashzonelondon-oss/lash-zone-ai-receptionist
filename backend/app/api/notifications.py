"""
Follow-up / callback notification sender.
Sends a plain-text email notification (via Resend API)
when a caller requests a follow-up, callback, or more information.
This module is intentionally self-contained and defensive: send_followup_email
NEVER raises. All errors are caught and logged so that a notification failure
can never affect a live phone call.
Required environment variables:
    RESEND_API_KEY     - API key from resend.com
    FOLLOWUP_EMAIL_TO  - recipient inbox for follow-up notifications
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_FROM = "Lash Zone Receptionist <onboarding@resend.dev>"

def _val(data: Dict[str, Any], key: str) -> str:
    """Return a human-friendly value, or 'Not provided' when missing/empty."""
    v = data.get(key)
    if v is None:
        return "Not provided"
    v = str(v).strip()
    return v if v else "Not provided"

def _build_body(followup: Dict[str, Any]) -> str:
    """Build the plain-text email body."""
    name = _val(followup, "caller_name")
    request_type = _val(followup, "request_type")
    if request_type == "Not provided":
        request_type = "callback"

    received = followup.get("created_at") or datetime.now().isoformat()

    return (
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

def send_followup_email(followup: Dict[str, Any]) -> bool:
    """
    Send a plain-text follow-up notification email via Resend.
    Returns True on success, False on any failure. Never raises.
    The API key is never logged.
    """
    try:
        api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
        recipient = (os.environ.get("FOLLOWUP_EMAIL_TO") or "").strip()

        if not api_key:
            print("Follow-up email NOT sent: RESEND_API_KEY not configured")
            return False
        if not recipient:
            print("Follow-up email NOT sent: FOLLOWUP_EMAIL_TO not configured")
            return False

        name = _val(followup, "caller_name")
        request_type = _val(followup, "request_type")
        if request_type == "Not provided":
            request_type = "callback"

        payload = json.dumps({
            "from": RESEND_FROM,
            "to": [recipient],
            "subject": f"New follow-up request from {name} \u2014 {request_type}",
            "text": _build_body(followup),
        }).encode("utf-8")

        req = urllib.request.Request(
            RESEND_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Follow-up email sent to {recipient} (status {resp.status})")
            return True

    except Exception as e:
        print(f"Follow-up email error: {repr(e)}")
        return False


def send_call_transcript_email(call_data: Dict[str, Any]) -> bool:
    """
    Send a plain-text transcript email after a completed call.
    Includes: caller number, date/time, duration, and full conversation.
    Returns True on success, False on any failure. Never raises.
    Uses the same RESEND_API_KEY and FOLLOWUP_EMAIL_TO env vars.
    """
    try:
        api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
        recipient = (os.environ.get("FOLLOWUP_EMAIL_TO") or "").strip()

        if not api_key:
            print("Transcript email NOT sent: RESEND_API_KEY not configured")
            return False
        if not recipient:
            print("Transcript email NOT sent: FOLLOWUP_EMAIL_TO not configured")
            return False

        caller = call_data.get("caller_number") or "Unknown"
        duration_secs = call_data.get("duration_seconds") or 0
        mins = duration_secs // 60
        secs = duration_secs % 60
        duration_str = f"{mins}m {secs}s"
        created_at = call_data.get("created_at") or datetime.now().isoformat()
        outcome = (call_data.get("outcome") or "unknown").replace("_", " ")

        # Format transcript as readable conversation
        transcript = call_data.get("transcript") or []
        if isinstance(transcript, str):
            try:
                transcript = json.loads(transcript)
            except Exception:
                transcript = []

        if transcript:
            lines = []
            for msg in transcript:
                role = msg.get("role", "")
                content = msg.get("content", "")
                label = "Caller" if role == "user" else "AI"
                lines.append(f"{label}: {content}")
            transcript_text = "\n".join(lines)
        else:
            transcript_text = "(No transcript recorded)"

        body = (
            f"Call transcript from Lash Zone London AI Receptionist\n"
            f"{'=' * 50}\n\n"
            f"Caller: {caller}\n"
            f"Date/time: {created_at}\n"
            f"Duration: {duration_str}\n"
            f"Outcome: {outcome}\n\n"
            f"Conversation\n"
            f"{'-' * 30}\n"
            f"{transcript_text}\n"
        )

        subject = f"Call transcript — {caller} ({duration_str})"

        payload = json.dumps({
            "from": RESEND_FROM,
            "to": [recipient],
            "subject": subject,
            "text": body,
        }).encode("utf-8")

        req = urllib.request.Request(
            RESEND_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Transcript email sent to {recipient} (status {resp.status})")
            print(f"TRANSCRIPT_EMAIL_BODY_START")
            print(body)
            print(f"TRANSCRIPT_EMAIL_BODY_END")
            return True

    except Exception as e:
        print(f"Transcript email error: {repr(e)}")
        return False
