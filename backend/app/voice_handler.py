"""
Voice Handler - Twilio Media Stream Integration
Processes audio streams and generates AI responses
"""

import os
import json
import base64
from typing import Optional, Dict, Any
from datetime import datetime

from twilio.rest import Client as TwilioClient

# Twilio client
twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")

twilio_client = TwilioClient(twilio_account_sid, twilio_auth_token)


class CallSession:
    """Represents an active call session"""

    def __init__(self, call_sid: str, caller_number: str):
        self.call_sid = call_sid
        self.caller_number = caller_number
        self.start_time = datetime.now()
        self.stream_sid: Optional[str] = None
        self.transcript = []
        self.context_data = {}
        self.is_active = True
        self.client_name: Optional[str] = None
        self.service_interest: Optional[str] = None
        self.needs_booking: bool = False
        self.needs_escalation: bool = False


class VoiceHandler:
    """Handles Twilio voice integration and audio processing"""

    def __init__(self):
        self.active_calls: Dict[str, CallSession] = {}
        self.base_url = os.environ.get("BASE_URL", "https://your-domain.com")
        self.studio_name = os.environ.get("STUDIO_NAME", "Lash Zone London")
        self.owner_phone = os.environ.get("OWNER_PHONE", "")
        self.booking_url = os.environ.get("BOOKING_URL", "")

    def get_incoming_call_twiml(self) -> str:
        """Generate TwiML for incoming calls - connects to WebSocket stream"""
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alloy" language="en-GB" style="friendly">
        Please wait while I connect you to our AI assistant.
    </Say>
    <Connect>
        <Stream url="wss://{self.base_url}/ws/voice" name="ai-receptionist" track="inbound_track">
            <Parameter name="studioName" value="{self.studio_name}"/>
        </Stream>
    </Connect>
</Response>"""
        return twiml

    def get_or_create_session(self, call_sid: str, caller_number: str) -> CallSession:
        """Get existing session or create new"""
        if call_sid not in self.active_calls:
            self.active_calls[call_sid] = CallSession(call_sid, caller_number)
        return self.active_calls[call_sid]

    def end_session(self, call_sid: str) -> Optional[CallSession]:
        """End and return session data"""
        if call_sid in self.active_calls:
            session = self.active_calls[call_sid]
            session.is_active = False
            return session
        return None

    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        try:
            # Format number if needed
            if not to_number.startswith("+"):
                to_number = f"+{to_number}"

            sent = twilio_client.messages.create(
                body=message,
                from_=twilio_phone,
                to=to_number
            )

            return {
                "success": True,
                "message_sid": sent.sid,
                "status": sent.status
            }
        except Exception as e:
            print(f"SMS error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def send_booking_link(self, phone_number: str) -> Dict[str, Any]:
        """Send booking link via SMS"""
        if self.booking_url:
            message = (
                f"Thanks for calling {self.studio_name}! "
                f"Ready to book your appointment? Click here: {self.booking_url} "
                f"We look forward to seeing you soon!"
            )
        else:
            message = (
                f"Thanks for calling {self.studio_name}! "
                f"Visit our website to book your appointment online. "
                f"We look forward to seeing you soon!"
            )

        return self.send_sms(phone_number, message)

    def send_escalation_alert(self, client_name: str, client_phone: str,
                             issue_summary: str, priority: str = "normal") -> Dict[str, Any]:
        """Alert owner about escalation"""
        if not self.owner_phone:
            return {"success": False, "error": "No owner phone configured"}

        message = (
            f"ESCALATION ALERT - {self.studio_name}\n"
            f"Client: {client_name}\n"
            f"Phone: {client_phone}\n"
            f"Issue: {issue_summary}\n"
            f"Priority: {priority.upper()}\n"
            f"Please callback ASAP."
        )

        return self.send_sms(self.owner_phone, message)

    def forward_to_human(self, call_sid: str) -> Optional[str]:
        """Forward active call to human"""
        try:
            if not self.owner_phone:
                return None

            # Create a new call to owner
            call = twilio_client.calls.create(
                to=self.owner_phone,
                from_=twilio_phone,
                status_callback=f"{self.base_url}/webhook/forward-status",
                status_callback_method="POST"
            )

            return call.sid

        except Exception as e:
            print(f"Forward error: {e}")
            return None

    def get_call_recording(self, call_sid: str) -> Optional[str]:
        """Get recording URL for a call"""
        try:
            recordings = twilio_client.recordings.list(call_sid=call_sid)

            if recordings:
                recording = recordings[0]
                return f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"

        except Exception as e:
            print(f"Recording fetch error: {e}")

        return None


# Singleton instance
voice_handler = VoiceHandler()
