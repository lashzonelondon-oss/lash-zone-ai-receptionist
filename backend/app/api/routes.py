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

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from starlette.responses import PlainTextResponse
from pydantic import BaseModel
import uvicorn

# Import our modules
from ..ai.receptionist import receptionist, CallContext, CallOutcome
from ..database.supabase_client import db
from ..voice_handler import voice_handler
from .notifications import send_followup_email, send_call_transcript_email

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

# Global session store shared between WebSocket and webhooks
CALL_SESSIONS: Dict[str, Dict] = {}

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

    # Store caller number for WebSocket and call-status webhook
    if call_sid:
        CALL_SESSIONS[call_sid] = {
            "caller_number": caller_number,
            "start_time": datetime.now(),
            "transcript": [],
            "context_data": {}
        }

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
async def gather_response(request: Request, background_tasks: BackgroundTasks):
    """
    Handle speech gathered by Twilio - process with AI and respond.
    Core conversation loop for the AI receptionist.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    twilio_from = form_data.get("From", "")
    twilio_forwarded_from = form_data.get("ForwardedFrom", "")
    caller_number = twilio_from or twilio_forwarded_from or "unknown"
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

    call_context = None  # initialised before try so finally: can always reference it
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

        if not ai_response or not ai_response.strip():
            ai_response = "I'm so sorry, could you say that again for me?"

        # Send SMS booking link in background (non-blocking).
        #
        # PRIMARY signal: the AI's own [[SEND_BOOKING_LINK]] marker, extracted
        # in receptionist.generate_response() into call_context.send_booking_link_marker.
        # SECONDARY (legacy) signal: the keyword-based _wants_booking_link()
        # check (call_context.needs_booking_link), consulted ONLY on a turn
        # where the model emitted neither a booking-link marker nor a
        # staff-followup marker — i.e. an otherwise unclassified turn. This
        # prevents the legacy keyword match (e.g. "appointment", "booking")
        # from overriding or duplicating a turn the model already classified
        # as needing staff follow-up rather than a booking link.
        _marker_wants_link = getattr(call_context, "send_booking_link_marker", False)
        _marker_staff_followup_this_turn = getattr(call_context, "staff_followup_type", None)
        _legacy_wants_link = getattr(call_context, "needs_booking_link", False)

        def _send_booking_sms_bg():
            try:
                BOOKING_SMS_ENABLED = True
                if _marker_wants_link:
                    wants = True
                elif not _marker_staff_followup_this_turn:
                    wants = BOOKING_SMS_ENABLED and _legacy_wants_link
                else:
                    wants = False
                already = getattr(session, "booking_link_sent", False)
                print(f"[BG] Booking-link check: marker={_marker_wants_link} legacy={_legacy_wants_link} "
                      f"staff_followup_this_turn={_marker_staff_followup_this_turn} resolved={wants} already_sent={already}")
                if wants and not already and caller_number not in ("unknown", ""):
                    booking_url = os.environ.get("BOOKING_URL", "")
                    if booking_url:
                        sent_ok = voice_handler.send_sms(
                            to_number=caller_number,
                            message="Thank you for contacting Lash Zone London.\n\nTo view availability and make a booking, please visit:\nhttps://www.lashzonelondon.com\n\nWe look forward to seeing you."
                        )
                        print(f"[BG] Booking-link SMS send result: {sent_ok}")
                        if sent_ok:
                            session.booking_link_sent = True
                    else:
                        print("[BG] Booking-link SMS NOT sent: BOOKING_URL not set")
            except Exception as sms_err:
                print(f"[BG] SMS booking link error: {repr(sms_err)}")
        background_tasks.add_task(_send_booking_sms_bg)

        # ------------------------------------------------------------------
        # UNIFIED STAFF FOLLOW-UP ACCUMULATION (replaces per-turn notification)
        #
        # Primary signal: the hidden [[STAFF_FOLLOWUP:type]] marker extracted
        # in receptionist.generate_response() (see call_context.staff_followup_type).
        # Fallback signals (kept working, never removed): the legacy keyword
        # detectors _wants_followup() (-> call_context.needs_followup) and
        # _should_escalate() (-> call_context.escalation). If the model fails
        # to emit a marker but a legacy detector fires, the call is still
        # marked for staff follow-up rather than silently dropped.
        #
        # State accumulates on the long-lived CallSession (session), which
        # persists across all turns of this call, and is read once by
        # call_status() after the call ends to send exactly one notification
        # using the highest-priority type seen during the whole call.
        # ------------------------------------------------------------------
        _STAFF_FOLLOWUP_PRIORITY = {
            "reaction": 3, "complaint": 3, "refund": 2, "retention": 2,
            "reschedule": 1, "cancel": 1, "running_late": 1,
            "appointment_query": 1, "speak_to_studio": 1, "other": 1,
        }

        def _record_staff_followup(followup_type: Optional[str], source: str):
            """Update the session's accumulated staff-follow-up state, keeping
            whichever type/priority is highest across the whole call."""
            if not followup_type:
                return
            rank = _STAFF_FOLLOWUP_PRIORITY.get(followup_type, 1)
            if rank >= getattr(session, "staff_followup_priority", 0):
                session.staff_followup_type = followup_type
                session.staff_followup_priority = rank
            print(f"[BG] Staff follow-up recorded (source={source}): type={followup_type} rank={rank} "
                  f"-> session now type={session.staff_followup_type} priority={session.staff_followup_priority}")

        # Primary: hidden marker parsed out of the AI's own reply.
        _record_staff_followup(getattr(call_context, "staff_followup_type", None), source="marker")

        # Fallback: legacy caller-wording detectors. These must keep working
        # even if the model never emits a marker for this turn/call.
        if getattr(call_context, "needs_followup", False):
            _record_staff_followup("other", source="legacy_needs_followup")
        if getattr(call_context, "escalation", None) is not None:
            _record_staff_followup("complaint", source="legacy_escalation")

        # NOTE: the previous mid-call _save_followup_bg() (which saved a
        # follow_ups row and sent an email on the very first matching turn)
        # has been removed. Its job is now done once, at call completion, by
        # call_status() below — using the accumulated highest-priority state
        # captured above — so the same call can no longer generate more than
        # one staff notification.

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

    finally:
        # Always persist the transcript and outcome back to the voice_handler session
        # so call_status can save them to the database even if an OpenAI error occurred.
        try:
            if call_context is not None:
                session.transcript = call_context.conversation_history
                outcome_val = getattr(getattr(call_context, "outcome", None), "value", None)
                if call_sid in CALL_SESSIONS and outcome_val:
                    CALL_SESSIONS[call_sid].setdefault("context_data", {})["outcome"] = outcome_val
        except Exception:
            pass  # Never let finally block errors suppress the original exception


@app.post("/webhook/call-status")
async def call_status(request: Request):
    """
    Handle call status updates from Twilio
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status_val = form_data.get("CallStatus", "")

    print(f"Call {call_sid} status: {call_status_val}")

    if call_status_val in ["completed", "failed", "busy", "no-answer"]:
        # Check global session store first
        session = CALL_SESSIONS.get(call_sid)

        if session:
            # Calculate duration
            duration = (datetime.now() - session["start_time"]).seconds

            # Make sure outcome is set even if empty
            outcome = session.get("context_data", {}).get("outcome", "unknown")
            if not outcome:
                outcome = "info_provided"  # Default outcome for calls without bookings/escalations

            # Bridge to voice_handler session to get the full conversation transcript.
            # The active conversation (caller + AI turns) lives in voice_handler.active_calls,
            # not in CALL_SESSIONS, so we read it from there.
            vh_session = voice_handler.active_calls.get(call_sid)
            transcript = vh_session.transcript if vh_session else session.get("transcript", [])

            # Save call to database
            await db.create_call({
                "caller_number": session["caller_number"],
                "duration_seconds": duration,
                "outcome": outcome,
                "transcript": transcript,
                "recording_url": None
            })

            print(f"✅ Call logged to database: {session['caller_number']}, duration: {duration}s, outcome: {outcome}")

            # Send transcript email (wrapped so it can never affect call logging)
            try:
                send_call_transcript_email({
                    "caller_number": session["caller_number"],
                    "duration_seconds": duration,
                    "outcome": outcome,
                    "transcript": transcript,
                    "created_at": session["start_time"].isoformat(),
                })
            except Exception as email_err:
                print(f"Transcript email error (non-fatal): {repr(email_err)}")

            # ------------------------------------------------------------
            # UNIFIED STAFF FOLLOW-UP: single notification per call, sent
            # once here at call completion, using the highest-priority
            # type accumulated during the call (see gather_response()).
            # Wrapped so it can never affect call logging above.
            # ------------------------------------------------------------
            try:
                followup_type = getattr(vh_session, "staff_followup_type", None) if vh_session else None
                if followup_type:
                    priority_rank = getattr(vh_session, "staff_followup_priority", 1)
                    is_urgent = priority_rank >= 2

                    # Resolved Twilio caller number for this call. If it was
                    # genuinely never available (e.g. withheld caller ID),
                    # store/render "unknown" rather than inventing a number.
                    resolved_phone = session["caller_number"] if session["caller_number"] not in ("unknown", "", None) else "unknown"

                    # Build a concise, human-useful summary from the actual
                    # conversation already collected for this call — no
                    # additional OpenAI call. Use the caller's own turns,
                    # since that is where the reason for contact lives.
                    caller_lines = [
                        (m.get("content") or "").strip()
                        for m in (transcript or [])
                        if m.get("role") == "user" and (m.get("content") or "").strip()
                    ]
                    if caller_lines:
                        # Most calls are short; a couple of the caller's own
                        # lines is normally enough context for staff without
                        # dumping the entire transcript into the summary.
                        context_snippet = " / ".join(caller_lines[:3])
                        if len(context_snippet) > 400:
                            context_snippet = context_snippet[:400].rstrip() + "..."
                    else:
                        context_snippet = "(no further detail captured in this call)"

                    type_label = followup_type.replace("_", " ")
                    summary = (
                        f"{'URGENT — ' if is_urgent else ''}Staff follow-up needed ({type_label}). "
                        f"Caller said: {context_snippet}"
                    )

                    followup_record = {
                        "caller_name": None,  # not reliably captured anywhere in the current call flow
                        "caller_phone": resolved_phone,
                        "summary": summary,
                        "service_interest": None,
                        "preferred_callback_time": None,
                        "request_type": followup_type,
                        "call_sid": call_sid,
                        "status": "pending",
                        "email_sent": False,
                    }

                    saved = await db.create_followup(followup_record)
                    print(f"Staff follow-up saved to Supabase: {bool(saved)} (type={followup_type}, urgent={is_urgent})")

                    email_ok = send_followup_email(followup_record)
                    print(f"Staff follow-up email result: {email_ok}")
            except Exception as staff_followup_err:
                print(f"Staff follow-up notification error (non-fatal): {repr(staff_followup_err)}")

            # Clean up session
            del CALL_SESSIONS[call_sid]
        else:
            print(f"⚠️ No session found for call {call_sid}")

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
    Twilio sends CallSid in the stream event data
    """
    call_sid = None
    caller_number = "unknown"

    # Wait for first message with call metadata
    try:
        init_data = await websocket.receive_json()
        if init_data.get("event") == "start":
            stream = init_data.get("stream", {})
            call_sid = stream.get("callSid") or init_data.get("callSid")
            caller_number = stream.get("caller", caller_number)
    except:
        pass

    # Fallback: generate a new call_sid if not provided
    if not call_sid:
        call_sid = str(uuid.uuid4())
        # Create session
        CALL_SESSIONS[call_sid] = {
            "caller_number": caller_number,
            "start_time": datetime.now(),
            "transcript": [],
            "context_data": {}
        }

    await websocket.accept()

    # Update the stored session with caller_number if we have it
    if call_sid in CALL_SESSIONS:
        CALL_SESSIONS[call_sid]["caller_number"] = caller_number

    try:
        while True:
            # Receive messages from Twilio
            data = await websocket.receive_json()

            if isinstance(data, dict):
                event = data.get("event")

                if event == "start":
                    # Stream started
                    stream = data.get("stream", {})
                    call_sid = stream.get("callSid") or call_sid
                    caller_number = stream.get("caller", caller_number)

                    if call_sid not in CALL_SESSIONS:
                        CALL_SESSIONS[call_sid] = {
                            "caller_number": caller_number,
                            "start_time": datetime.now(),
                            "transcript": [],
                            "context_data": {}
                        }
                    else:
                        CALL_SESSIONS[call_sid]["caller_number"] = caller_number

                    # Generate greeting through AI
                    greeting_context = CallContext(caller_number=caller_number)
                    greeting = await receptionist.generate_response(
                        greeting_context,
                        "Hello, introduce yourself and offer help"
                    )
                    audio_response = await receptionist.generate_speech(greeting)
                    await websocket.send_json({
                        "event": "media",
                        "media": {
                            ".payload": base64.b64encode(audio_response).decode()
                        }
                    })

                elif event == "media":
                    # Process audio
                    media = data.get("media", {})
                    payload = media.get("payload", "")

                    if payload:
                        audio_bytes = base64.b64decode(payload)

                        # Process through AI
                        response_text = await voice_handler.handle_stream_audio(audio_bytes, call_sid)

                        if response_text and call_sid in CALL_SESSIONS:
                            # Store transcript
                            CALL_SESSIONS[call_sid]["transcript"].append({
                                "role": "user",
                                "content": "voice_input"
                            })
                            CALL_SESSIONS[call_sid]["transcript"].append({
                                "role": "assistant",
                                "content": response_text
                            })

                            # Generate audio response
                            audio_response = await receptionist.generate_speech(response_text)
                            await websocket.send_json({
                                "event": "media",
                                "media": {
                                    "payload": base64.b64encode(audio_response).decode()
                                }
                            })

                elif event == "stop":
                    # Stream ended
                    break

    except WebSocketDisconnect:
        pass
    finally:
        if call_sid in CALL_SESSIONS:
            del CALL_SESSIONS[call_sid]


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
