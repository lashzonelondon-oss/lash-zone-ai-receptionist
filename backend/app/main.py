"""
Twilio Voice Integration for AI Receptionist
Handles incoming calls, media streams, and call management
"""

import os
import json
import asyncio
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Start, Stream, Connect

# Lazy initialization of Twilio client
_twilio_client = None

def get_twilio_client():
    global _twilio_client
    if _twilio_client is None:
        from twilio.rest import Client as TwilioClient
        twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        if twilio_account_sid and twilio_auth_token:
            _twilio_client = TwilioClient(twilio_account_sid, twilio_auth_token)
        else:
            _twilio_client = None
    return _twilio_client


@dataclass
class CallSession:
    """Represents an active call session"""
    call_sid: str
    caller_number: str
    start_time: datetime = field(default_factory=datetime.now)
    stream_sid: Optional[str] = None
    transcript: list = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


class TwilioVoiceHandler:
    """
    Handles Twilio voice integration for the AI receptionist
    Manages incoming calls, media streams, and call lifecycle
    """

    def __init__(self):
        self.active_calls: Dict[str, CallSession] = {}
        self.base_url = os.environ.get("BASE_URL", "https://your-domain.com")
        self.receptionist = None  # Will be set by main app

    def set_receptionist(self, receptionist):
        """Set the AI receptionist instance"""
        self.receptionist = receptionist

    def create_incoming_call_webhook_response(self) -> str:
        """
        Generate TwiML response for incoming calls
        Connects caller to AI voice stream
        """
        response = VoiceResponse()

        # Add greeting
        response.say(
            "Connecting you to our AI assistant. Please wait a moment.",
            voice="alice",
            language="en-GB"
        )

        # Connect to media stream
        connect = Connect()
        stream = Stream(
            name="ai-receptionist",
            url=f"wss://{self.base_url.replace('https://', '').replace('http://', '')}/ws/voice"
        )
        connect.append(stream)
        response.append(connect)

        return str(response)

    def create_call_status_webhook_response(self) -> str:
        """Generate response for call status callbacks"""
        response = VoiceResponse()
        response.say("Call ended.", voice="alice")
        return str(response)

    async def handle_stream_audio(self, audio_data: bytes, call_sid: str) -> Optional[str]:
        """
        Process incoming audio from call
        Returns AI response text if generated
        """
        if call_sid not in self.active_calls:
            return None

        session = self.active_calls[call_sid]

        try:
            # Transcribe audio
            if self.receptionist:
                transcript = await self.receptionist.transcribe_audio(audio_data)

                if transcript and transcript.strip():
                    session.transcript.append({
                        "role": "user",
                        "content": transcript,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Generate AI response
                    from .ai.receptionist import CallContext
                    call_context = CallContext(
                        caller_number=session.caller_number,
                        conversation_history=[
                            {"role": msg["role"], "content": msg["content"]}
                            for msg in session.transcript[:-1]
                        ]
                    )

                    response_text = await self.receptionist.generate_response(
                        call_context,
                        transcript
                    )

                    # Store context updates
                    session.context_data.update({
                        "last_response": response_text,
                        "context": call_context.to_json()
                    })

                    return response_text

        except Exception as e:
            print(f"Error handling stream audio: {e}")

        return None

    def get_or_create_session(self, call_sid: str, caller_number: str) -> CallSession:
        """Get existing session or create new one"""
        if call_sid not in self.active_calls:
            self.active_calls[call_sid] = CallSession(
                call_sid=call_sid,
                caller_number=caller_number
            )
        return self.active_calls[call_sid]

    def end_session(self, call_sid: str) -> Optional[CallSession]:
        """End a call session"""
        if call_sid in self.active_calls:
            session = self.active_calls[call_sid]
            session.is_active = False
            return session
        return None

    async def generate_voice_response(self, text: str) -> bytes:
        """
        Generate audio response for AI text
        Returns audio in format suitable for Twilio stream
        """
        if self.receptionist:
            return await self.receptionist.generate_speech(text)
        return b""

    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS message
        """
        try:
            client = get_twilio_client()
            if not client:
                return {"success": False, "error": "Twilio not configured"}

            twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
            sent_message = client.messages.create(
                body=message,
                from_=twilio_phone,
                to=to_number
            )

            return {
                "success": True,
                "message_sid": sent_message.sid,
                "status": sent_message.status
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def forward_to_human(self, to_number: str, caller_number: str) -> Dict[str, Any]:
        """
        Forward call to human receptionist/owner
        """
        try:
            client = get_twilio_client()
            if not client:
                return {"success": False, "error": "Twilio not configured"}

            twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
            call = client.calls.create(
                to=to_number,
                from_=twilio_phone,
                url=f"{self.base_url}/webhook/forward-call"
            )

            return {
                "success": True,
                "call_sid": call.sid,
                "status": call.status
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_call_recording_url(self, call_sid: str) -> Optional[str]:
        """Get recording URL if call was recorded"""
        try:
            client = get_twilio_client()
            if not client:
                return None

            recordings = client.recordings.list(
                call_sid=call_sid,
                limit=1
            )

            if recordings:
                recording = recordings[0]
                return f"https://api.twilio.com{recording.uri.replace('.json', '')}"

        except Exception as e:
            print(f"Error fetching recording: {e}")

        return None


# Singleton instance
voice_handler = TwilioVoiceHandler()


def get_audio_from_stream(stream_data: Dict) -> Optional[bytes]:
    """Extract raw audio from Twilio stream event data"""
    try:
        if stream_data.get("event") == "media":
            media = stream_data.get("media", {})
            payload = media.get("payload", "")

            # Decode base64 ulaw audio
            audio_bytes = base64.b64decode(payload)
            return audio_bytes

    except Exception as e:
        print(f"Error extracting audio from stream: {e}")

    return None


def convert_ulaw_to_wav(ulaw_bytes: bytes) -> bytes:
    """Convert ulaw audio to WAV format for Whisper"""
    # This is a simplified version - in production, use proper audio conversion
    # For now, we'll just return the raw bytes as Whisper can handle various formats
    return ulaw_bytes
