"""
FastAPI Application - AI Receptionist Backend
Handles Twilio webhooks, API endpoints, and WebSocket for real-time voice
"""

import os
import asyncio
import json
import base64
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from starlette.responses import PlainTextResponse
from pydantic import BaseModel
import uvicorn

# Import our modules
from ..ai.receptionist import receptionist, CallContext, CallOutcome
from ..database.supabase_client import db
from ..voice_handler import voice_handler
from .notifications import send_followup_email

# Create FastAPI app
app = FastAPI(
    title="Lash Zone London AI Receptionist",
    description="24/7 AI-powered phone receptionist for beauty studio",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== TWILIO WEBHOOKS ====================

@app.post("/webhook/incoming-call")
async def incoming_call(request: Request):
    """
    Handle incoming Twilio calls
    Returns TwiML to connect caller to AI stream
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    caller_number = form_data.get("From", "")

    print(f"Incoming call from {caller_number}, SID: {call_sid}")

    # Get TwiML response
    twiml_response = voice_handler.create_incoming_call_webhook_response()

    return Response(content=twiml_response, media_type="application/xml")


@app.post("/webhook/gather-retry")
async def gather_retry(request: Request):
    """
    Second-chance gather: called when initial Gather times out with no speech.
    Plays a prompt and opens one more Gather back to /webhook/gather.
    """
    base = voice_handler.base_url.rstrip("/")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy-Neural" language="en-GB">Sorry, I didn't catch that. How can I help you today?</Say>
    <Gather input="speech" action="{base}/webhook/gather" method="POST" speechTimeout="3" timeout="10" language="en-GB" enhanced="true"></Gather>
    <Say voice="Polly.Amy-Neural" language="en-GB">I'm having trouble hearing you. Please call back and we'll be happy to help. Goodbye!</Say>
    <Hangup/>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.post("/webhook/gather")
async def gather_response(request: Request):
    """
    Handle speech gathered by Twilio - process with AI and respond.
    Core conversation loop for the AI receptionist.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    caller_number = form_data.get("ForwardedFrom") or form_data.get("From", "unknown")
    speech_result = (form_data.get("SpeechResult") or "").strip()
    confidence = form_data.get("Confidence", "0")

    print(f"Gather from {caller_number} (SID: {call_sid}): '{speech_result}' (confidence: {confidence})")

    base = voice_handler.base_url.rstrip("/")
    session = voice_handler.get_or_create_session(call_sid, caller_number)

    if not speech_result:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy-Neural" language="en-GB">I'm sorry, I didn't quite catch that. Could you please repeat that for me?</Say>
    <Gather input="speech" action="{base}/webhook/gather" method="POST" speechTimeout="3" timeout="10" language="en-GB" enhanced="true"></Gather>
    <Say voice="Polly.Amy-Neural" language="en-GB">I'm having trouble hearing you. Please call back and we'll be happy to help. Goodbye!</Say>
    <Hangup/>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    try:
        from ..ai.receptionist import CallContext

        # Build a CallContext carrying the full conversation history for this call.
        # generate_response() appends the user + assistant messages to this list,
        # so we persist it back onto the session afterwards.
        call_context = CallContext(
            caller_number=caller_number,
            conversation_history=list(session.transcript),
        )

        # generate_response signature: (call_context, user_message) -> str
        ai_response = await receptionist.generate_response(call_context, speech_result)

        # Persist updated conversation history back to the session
        session.transcript = call_context.conversation_history

        if not ai_response or not ai_response.strip():
            ai_response = "I'm so sorry, could you say that again for me?"

        # Send SMS booking link if the AI flagged it
        # NOTE: SMS sending is currently disabled. We are online-booking only and the
        # receptionist verbally directs callers to the website instead of texting a link.
        # Set BOOKING_SMS_ENABLED = True to re-enable the SMS booking link.
        BOOKING_SMS_ENABLED = True
        try:
            wants = BOOKING_SMS_ENABLED and getattr(call_context, "needs_booking_link", False)
            already = getattr(session, "booking_link_sent", False)
            print(f"Booking-link check: needs={wants} already_sent={already} caller={caller_number}")
            if wants and not already and caller_number not in ("unknown", ""):
                booking_url = os.environ.get("BOOKING_URL", "")
                if booking_url:
                    sent_ok = voice_handler.send_sms(
                        to_number=caller_number,
                    message="Thank you for contacting Lash Zone London.\n\nTo view availability and make a booking, please visit:\nhttps://www.lashzonelondon.com\n\nWe look forward to seeing you."
                    )
                    print(f"Booking-link SMS send result: {sent_ok}")
                    if sent_ok:
                        call_context.booking_link_sent = True
                        session.booking_link_sent = True
                        ai_response += " We're often busy with clients, so all bookings are made online. I've just sent the booking link directly to your phone."
                else:
                    print("Booking-link SMS NOT sent: BOOKING_URL env var is empty")
        except Exception as sms_err:
            print(f"SMS booking link error: {repr(sms_err)}")

        # Save & email a follow-up / callback request if the AI flagged it.
        # NOTE: This feature is disabled by default. Set FOLLOWUP_ENABLED = True
        # (and configure the follow_ups table + Gmail env vars) to activate it.
        # All logic is wrapped so it can never affect the live call.
        FOLLOWUP_ENABLED = True
        try:
            wants_followup = FOLLOWUP_ENABLED and getattr(call_context, "needs_followup", False)
            already_followup = getattr(session, "followup_saved", False)
            print(f"Follow-up check: needs={wants_followup} already_saved={already_followup} caller={caller_number}")
            if wants_followup and not already_followup:
                # Mark immediately so we only ever create one record per call.
                session.followup_saved = True
                followup_record = {
                    "caller_name": getattr(call_context.client_info, "name", None),
                    "caller_phone": caller_number if caller_number not in ("unknown", "") else None,
                    "summary": getattr(call_context, "followup_summary", None) or speech_result,
                    "service_interest": getattr(call_context, "followup_service", None),
                    "preferred_callback_time": getattr(call_context, "preferred_callback_time", None),
                    "request_type": "callback",
                    "call_sid": call_sid,
                    "status": "pending",
                    "email_sent": False,
                }
                # Save to Supabase FIRST so the request is durable even if email fails.
                saved = await db.create_followup(followup_record)
                print(f"Follow-up saved to Supabase: {bool(saved)}")
                # Then send the email notification (failure here never breaks the call).
                email_ok = send_followup_email(followup_record)
                print(f"Follow-up email result: {email_ok}")
        except Exception as followup_err:
            print(f"Follow-up handling error: {repr(followup_err)}")

        # Decide whether the call should end
        outcome = getattr(call_context, "outcome", None)
        lower = ai_response.lower()
        is_final = bool(getattr(outcome, "value", None) in ("escalated",)) or any(
            p in lower for p in ["goodbye", "take care", "have a wonderful day", "have a lovely day", "bye for now"]
        )

        twiml = voice_handler.get_gather_response_twiml(ai_response, call_sid, is_final=is_final)
        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        print(f"Error processing gather for {call_sid}: {e}")
        import traceback
        traceback.print_exc()
        fallback = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Amy" language="en-GB">I'm so sorry, I'm having a little trouble at the moment. Please call back shortly and one of the team will be happy to help. Goodbye!</Say>
    <Hangup/>
</Response>"""
        return Response(content=fallback, media_type="application/xml")


@app.post("/webhook/call-status")
async def call_status(request: Request):
    """
    Handle call status updates from Twilio
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")

    print(f"Call {call_sid} status: {call_status}")

    if call_status in ["completed", "failed", "busy", "no-answer"]:
        session = voice_handler.end_session(call_sid)

        if session:
            # Save call to database
            await db.create_call({
                "caller_number": session.caller_number,
                "duration_seconds": (datetime.now() - session.start_time).seconds,
                "outcome": session.context_data.get("outcome", "unknown"),
                "transcript": session.transcript,
                "recording_url": voice_handler.get_call_recording_url(call_sid)
            })

    return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")


@app.post("/webhook/sms-received")
async def sms_received(request: Request):
    """
    Handle incoming SMS messages
    """
    form_data = await request.form()
    from_number = form_data.get("From", "")
    message_body = form_data.get("Body", "")

    print(f"SMS from {from_number}: {message_body}")

    # Could implement SMS-based booking here
    # For now, just acknowledge
    response = voice_handler.send_sms(
        to_number=from_number,
        message="Thanks for texting Lash Zone London! For appointments, please call us or book online. We look forward to seeing you soon!"
    )

    return Response(content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>", media_type="application/xml")


# ==================== WEBSOCKET FOR VOICE ====================

class ConnectionManager:
    """Manages WebSocket connections for voice streaming"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.call_contexts: Dict[str, CallContext] = {}

    async def connect(self, websocket: WebSocket, call_sid: str):
        await websocket.accept()
        self.active_connections[call_sid] = websocket

        # Create call context
        self.call_contexts[call_sid] = CallContext(caller_number="unknown")

        # Generate greeting through AI for comprehensive response
        greeting_context = CallContext(caller_number="unknown")
        greeting = await receptionist.generate_response(
            greeting_context,
            "Hello, introduce yourself and offer help"
        )

        # Generate greeting audio
        audio_response = await receptionist.generate_speech(greeting)

        # Send as base64 encoded audio
        await websocket.send_json({
            "type": "audio",
            "data": base64.b64encode(audio_response).decode()
        })

    def disconnect(self, call_sid: str):
        if call_sid in self.active_connections:
            del self.active_connections[call_sid]
        if call_sid in self.call_contexts:
            del self.call_contexts[call_sid]

    async def send_audio(self, call_sid: str, audio_data: bytes):
        if call_sid in self.active_connections:
            await self.active_connections[call_sid].send_json({
                "type": "audio",
                "data": base64.b64encode(audio_data).decode()
            })


manager = ConnectionManager()


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice conversation
    """
    call_sid = str(uuid.uuid4())

    await manager.connect(websocket, call_sid)

    try:
        while True:
            # Receive audio from client
            data = await websocket.receive_json()

            if data.get("type") == "audio":
                # Decode audio
                audio_bytes = base64.b64decode(data.get("data", ""))

                if audio_bytes:
                    # Process through AI
                    response_text = await voice_handler.handle_stream_audio(audio_bytes, call_sid)

                    if response_text:
                        # Generate audio response
                        audio_response = await receptionist.generate_speech(response_text)

                        # Send response
                        await manager.send_audio(call_sid, audio_response)

            elif data.get("type") == "hangup":
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(call_sid)


# ==================== REST API ENDPOINTS ====================

# Pydantic models
class AppointmentCreate(BaseModel):
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    service: str
    requested_date: str
    requested_time: str
    notes: Optional[str] = None


class EscalationCreate(BaseModel):
    call_id: Optional[str] = None
    client_name: str
    client_phone: str
    issue_summary: str
    priority: str = "normal"


class ConfigUpdate(BaseModel):
    key: str
    value: str


class FAQCreate(BaseModel):
    question_pattern: str
    answer: str
    category: str = "general"


class SMSRequest(BaseModel):
    to_number: str
    message: str


# Calls API
@app.get("/api/calls")
async def get_calls(limit: int = 50, offset: int = 0):
    """Get call history"""
    calls = await db.get_calls(limit=limit, offset=offset)
    return {"success": True, "data": calls}


@app.get("/api/calls/{call_id}")
async def get_call(call_id: str):
    """Get call details"""
    call = await db.get_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"success": True, "data": call}


@app.get("/api/calls/search")
async def search_calls(q: str):
    """Search calls"""
    calls = await db.search_calls(q)
    return {"success": True, "data": calls}


# Appointments API
@app.get("/api/appointments")
async def get_appointments(date: Optional[str] = None, status: Optional[str] = None):
    """Get appointments"""
    appointments = await db.get_appointments(date=date, status=status)
    return {"success": True, "data": appointments}


@app.post("/api/appointments")
async def create_appointment(appointment: AppointmentCreate):
    """Create new appointment"""
    result = await db.create_appointment(appointment.dict())

    if result:
        # Send confirmation SMS
        voice_handler.send_sms(
            to_number=appointment.client_phone,
            message=f"Thanks {appointment.client_name}! Your appointment at Lash Zone London for {appointment.service} on {appointment.requested_date} at {appointment.requested_time} is confirmed. See you soon!"
        )

        return {"success": True, "data": result}

    raise HTTPException(status_code=500, detail="Failed to create appointment")


@app.get("/api/availability")
async def check_availability(date: str, time: str, duration: int = 60):
    """Check appointment availability"""
    available = await db.check_availability(date, time, duration)
    return {"success": True, "available": available}


# Escalations API
@app.get("/api/escalations")
async def get_escalations(status: Optional[str] = None):
    """Get escalation requests"""
    escalations = await db.get_escalations(status=status)
    return {"success": True, "data": escalations}


@app.post("/api/escalations")
async def create_escalation(escalation: EscalationCreate):
    """Create escalation request"""
    result = await db.create_escalation(escalation.dict())

    if result:
        # Alert owner
        owner_phone = os.environ.get("OWNER_PHONE", "")
        if owner_phone:
            voice_handler.send_sms(
                to_number=owner_phone,
                message=f"ESCALATION ALERT from Lash Zone AI: {escalation.issue_summary}. Client: {escalation.client_name} ({escalation.client_phone}). Priority: {escalation.priority}"
            )

        return {"success": True, "data": result}

    raise HTTPException(status_code=500, detail="Failed to create escalation")


@app.put("/api/escalations/{escalation_id}")
async def resolve_escalation(escalation_id: str, notes: str = ""):
    """Mark escalation as resolved"""
    success = await db.resolve_escalation(escalation_id, notes)
    return {"success": success}


# Configuration API
@app.get("/api/config")
async def get_config():
    """Get all configuration"""
    config = await db.get_all_config()
    return {"success": True, "data": config}


@app.get("/api/config/{key}")
async def get_config_value(key: str):
    """Get configuration value"""
    value = await db.get_config(key)
    return {"success": True, "data": {"key": key, "value": value}}


@app.put("/api/config")
async def update_config(config: ConfigUpdate):
    """Update configuration"""
    success = await db.set_config(config.key, config.value)
    return {"success": success}


# FAQs API
@app.get("/api/faqs")
async def get_faqs():
    """Get FAQ knowledge base"""
    faqs = await db.get_faqs()
    return {"success": True, "data": faqs}


@app.post("/api/faqs")
async def create_faq(faq: FAQCreate):
    """Create new FAQ"""
    result = await db.create_faq(faq.dict())
    return {"success": True, "data": result}


@app.put("/api/faqs/{faq_id}")
async def update_faq(faq_id: str, faq: FAQCreate):
    """Update FAQ"""
    success = await db.update_faq(faq_id, faq.dict())
    return {"success": success}


@app.delete("/api/faqs/{faq_id}")
async def delete_faq(faq_id: str):
    """Delete FAQ"""
    success = await db.delete_faq(faq_id)
    return {"success": success}


# SMS API
@app.post("/api/sms/send")
async def send_sms(sms: SMSRequest):
    """Send SMS message"""
    result = voice_handler.send_sms(sms.to_number, sms.message)
    return result


# Health check
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Lash Zone London AI Receptionist"
    }


# ==================== MAIN ====================

# Initialize on startup
@app.on_event("startup")
async def startup():
    print("Starting Lash Zone London AI Receptionist...")
    # Load AI config from database
    await receptionist.load_config()
    print(f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ AI Model: {receptionist.model}")
    print(f"ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ AI Voice: {receptionist.voice}")
    voice_handler.set_receptionist(receptionist)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
