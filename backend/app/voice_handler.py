"""
Voice Handler - Twilio Gather-based AI Receptionist
Uses Twilio speech recognition + OpenAI for conversation
No WebSockets required - simple, reliable, production-ready
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime


class CallSession:
    """Represents an active call session"""

    def __init__(self, call_sid: str, caller_number: str):
        self.call_sid = call_sid
        self.caller_number = caller_number
        self.start_time = datetime.now()
        self.transcript = []
        self.is_active = True


class TwilioVoiceHandler:
    """
    Handles Twilio voice integration for the AI receptionist.
    Uses Twilio <Gather> for speech recognition and <Say> for responses.
    """

    def __init__(self):
        self.active_calls: Dict[str, CallSession] = {}
        self.studio_name = os.environ.get("STUDIO_NAME", "Lash Zone London")
        self._receptionist = None  # Set by startup via set_receptionist()
        self.base_url = os.environ.get("BASE_URL", "https://talented-fulfillment-production-8f33.up.railway.app")

    def get_incoming_call_twiml(self) -> str:
        """Generate TwiML for incoming calls - greets caller and starts gathering speech"""
        base_url = self.base_url.rstrip("/")
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy" language="en-GB">Thank you for calling Lash Zone London! How can I help you today?</Say>
    <Gather input="speech" action="{base_url}/webhook/gather" method="POST" speechTimeout="auto" language="en-GB" enhanced="true">
        <Say voice="Polly.Amy" language="en-GB">Please go ahead and speak.</Say>
    </Gather>
    <Say voice="Polly.Amy" language="en-GB">I didn't catch that. Please call back and I'll be happy to help. Goodbye!</Say>
</Response>"""
        return twiml

    def create_incoming_call_webhook_response(self) -> str:
        """Alias for get_incoming_call_twiml - called by routes.py webhook handler"""
        return self.get_incoming_call_twiml()

    def set_receptionist(self, receptionist):
        """Set the AI receptionist instance (called from startup)"""
        self._receptionist = receptionist

    def get_or_create_session(self, call_sid: str, caller_number: str) -> CallSession:
        if call_sid not in self.active_calls:
            self.active_calls[call_sid] = CallSession(call_sid, caller_number)
        return self.active_calls[call_sid]

    def end_session(self, call_sid: str):
        if call_sid in self.active_calls:
            self.active_calls[call_sid].is_active = False

    def get_gather_response_twiml(self, ai_response_text: str, call_sid: str, is_final: bool = False) -> str:
        """Generate TwiML to speak the AI response and gather next input"""
        base_url = self.base_url.rstrip("/")
        safe_text = ai_response_text.replace("&", "and").replace("<", "").replace(">", "").replace('"', "'")
        if is_final:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy" language="en-GB">{safe_text}</Say>
    <Hangup/>
</Response>"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy" language="en-GB">{safe_text}</Say>
    <Gather input="speech" action="{base_url}/webhook/gather" method="POST" speechTimeout="auto" language="en-GB" enhanced="true">
    </Gather>
    <Say voice="Polly.Amy" language="en-GB">Is there anything else I can help you with today?</Say>
    <Gather input="speech" action="{base_url}/webhook/gather" method="POST" speechTimeout="auto" language="en-GB" enhanced="true">
    </Gather>
    <Hangup/>
</Response>"""

    def _to_e164(self, number: str) -> str:
        """Best-effort normalise a phone number to E.164 (UK default)."""
        if not number:
            return number
        n = number.strip().replace(" ", "").replace("-", "")
        if n.startswith("+"):
            return n
        if n.startswith("00"):
            return "+" + n[2:]
        if n.startswith("0"):
            # Assume UK mobile/landline
            return "+44" + n[1:]
        return "+" + n

    def send_sms(self, to_number: str, message: str, from_number: Optional[str] = None) -> bool:
        """Send an SMS message via Twilio with detailed logging."""
        try:
            import os
            from twilio.rest import Client
            account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
            twilio_number = from_number or os.environ.get("TWILIO_PHONE_NUMBER")
            to_e164 = self._to_e164(to_number)
            print(f"SMS attempt -> to={to_e164} from={twilio_number} sid_set={bool(account_sid)} token_set={bool(auth_token)}")
            if not all([account_sid, auth_token, twilio_number]):
                print("SMS not sent: missing Twilio credentials/number env vars")
                return False
            client = Client(account_sid, auth_token)
            msg = client.messages.create(body=message, from_=twilio_number, to=to_e164)
            print(f"SMS sent OK: sid={msg.sid} status={msg.status} to={to_e164}")
            return True
        except Exception as e:
            print(f"SMS send error: {repr(e)}")
            return False


# Module-level singleton
voice_handler = TwilioVoiceHandler()
