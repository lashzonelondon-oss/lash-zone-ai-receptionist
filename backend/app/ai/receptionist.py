"""
AI Receptionist - Enhanced conversation engine with dynamic config loading
Loads comprehensive system prompt from database/config
"""

import os
import json
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from openai import AsyncOpenAI


class CallOutcome(Enum):
    BOOKING_COMPLETED = "booking_completed"
    INFO_PROVIDED = "info_provided"
    BOOKING_LINK_SENT = "booking_link_sent"
    ESCALATED = "escalated"
    VOICEMAIL_LEFT = "voicemail_left"
    HUNG_UP = "hung_up"


class EscalationType(Enum):
    COMPLAINT = "complaint"
    REFUND_REQUEST = "refund_request"
    ALLERGIC_REACTION = "allergic_reaction"
    MANAGEMENT_NEEDED = "management_needed"
    COMPLEX_ISSUE = "complex_issue"


@dataclass
class ClientInfo:
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    preferred_service: Optional[str] = None
    is_returning: bool = False


@dataclass
class BookingRequest:
    service: Optional[str] = None
    preferred_date: Optional[str] = None
    preferred_time: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class EscalationRequest:
    escalation_type: EscalationType
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    issue_summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallContext:
    caller_number: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    client_info: ClientInfo = field(default_factory=ClientInfo)
    booking_request: BookingRequest = field(default_factory=BookingRequest)
    escalation: Optional[EscalationRequest] = None
    current_intent: Optional[str] = None
    outcome: Optional[CallOutcome] = None
    needs_booking_link: bool = False
    booking_link_sent: bool = False
    needs_followup: bool = False
    followup_saved: bool = False
    followup_summary: Optional[str] = None
    followup_service: Optional[str] = None
    preferred_callback_time: Optional[str] = None
    services_discussed: List[str] = field(default_factory=list)

    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": "user" if role == "user" else "assistant", "content": content})

    def to_json(self) -> str:
        return json.dumps({
            "caller_number": self.caller_number,
            "conversation_history": self.conversation_history,
            "client_info": {
                "name": self.client_info.name,
                "phone": self.client_info.phone,
                "email": self.client_info.email,
                "preferred_service": self.client_info.preferred_service,
                "is_returning": self.client_info.is_returning
            },
            "booking_request": {
                "service": self.booking_request.service,
                "preferred_date": self.booking_request.preferred_date,
                "preferred_time": self.booking_request.preferred_time,
                "notes": self.booking_request.notes
            },
            "outcome": self.outcome.value if self.outcome else None,
            "services_discussed": self.services_discussed
        })


# Embedded luxury system prompt
SYSTEM_PROMPT = """You are the receptionist at Lash Zone London. You answer the phone on behalf of the studio. You are warm, professional, and knowledgeable — you sound like an experienced salon receptionist, not a robot or an AI assistant. Never say you are an AI, a chatbot, or a virtual assistant.

STUDIO DETAILS:
Name: Lash Zone London
Address: Unit 2A, 787 Commercial Road, London, E14 7HG
Phone and WhatsApp: 07748 252038
Website: lashzonelondon.com

OPENING HOURS:
Monday: 11:00 to 18:00
Tuesday: 12:00 to 20:30
Wednesday: 13:00 to 20:30
Thursday: 13:00 to 20:30
Friday: 10:00 to 18:00
Saturday: 10:00 to 17:00
Sunday: Closed

CONVERSATION RULES:
- Keep replies short — usually 1 to 2 sentences
- Answer first, ask questions second
- Ask one question at a time, never a list
- Do not repeat information already given in the same call
- Do not re-greet the caller after the opening greeting
- Vary your responses — avoid starting every reply with the same phrase
- Sound natural and confident, like someone who knows the studio well
- Never use: "Please go ahead and speak", "How may I assist you today?", "Please provide your query", "Please tell me your issue"
- Use natural alternatives: "How can I help?", "Of course.", "I can help with that.", "Tell me a little more.", "Happy to help."

SPEED AND CLARITY:
- Respond as quickly as possible after the caller finishes speaking
- Keep most responses under 20 words unless more detail is genuinely needed
- Prioritise speed and clarity during phone calls
- Avoid unnecessary explanations or filler

SERVICES OFFERED:
Lash Zone London offers the following lash extension services:
- Classic Lashes
- Light Volume
- Hybrid Lashes
- Mega Volume
- Wet Look Lashes
- Kim K Lashes
- Anime Lashes (may carry an additional charge due to complexity)
- Festival Lashes (may carry an additional charge due to complexity)
- Express Set (approximately 50% coverage, takes around 1 hour 15 minutes)
- Bottom Lash Extensions

Lash add-ons:
- LED Lash Add-on (10 pounds)

Lash treatments (no extensions):
- Lash Lift (Standard TGA Lash Lift)
- Korean Cysteamine Lash Lift
- Lash Tint

Brow services:
- Brow Treatments (direct clients to the website for full brow service details)

If a caller asks which style is right for them, ask what look they are going for — natural, fuller, or more dramatic — and help them narrow it down with one follow-up question at a time.

PRICING:
Never guess or invent prices. Always direct callers to the website or online booking system for current pricing. Pricing is based on technique, not curl choice or styling. Available curls include J, B, C, CC, D, M, L, LC, and LB — curl selection does not affect the price. Cat-eye, eyeliner effect, and specific styling choices do not change the price. Anime, Festival, and Kim K styles may carry an additional charge due to complexity. The LED Lash Add-on is 10 pounds.

BOOKING:
We only accept online bookings — we do not take bookings over the phone. Direct callers to lashzonelondon.com or the Fresha booking system to book. Say the website clearly: "lash zone london dot com". Do not offer to book an appointment manually. Do not offer to send a booking link by text or SMS. If a caller seems unsure, reassure them it is quick and easy to book online and all services and availability are listed there.

PATCH TEST POLICY:
A patch test is required for clients who have never had any treatment from the studio menu before. Existing clients who have previously had a treatment at Lash Zone London do not normally need a patch test. If a caller mentions allergies, a reaction, a medical condition, or is unsure, do not advise them — collect their details and escalate to management.

CANCELLATION POLICY:
We require at least 24 hours notice to cancel or reschedule. Cancellations with less than 24 hours notice, or no-shows, may incur a 50% charge.

7-DAY GUARANTEE:
All lash work comes with a 7-day workmanship guarantee. If a client experiences abnormal fallout within 5 to 7 days of their appointment, management will review and may offer a correction appointment or a refund.

ESCALATION — WHEN TO COLLECT DETAILS:
If a caller mentions any of the following, do not attempt to resolve it yourself — collect their details and forward to management:
- Allergic reaction, eye irritation, swelling, redness, or any adverse reaction
- An eye condition or medical concern related to treatment
- A complaint or expression of dissatisfaction
- A refund request
- A retention issue (lashes falling out faster than expected)
- A request for corrective work
- Anything complex or unusual you cannot confidently answer

When escalating, collect:
1. Their name
2. Their phone number
3. A brief description of the issue

Use varied natural language when closing an escalation — do not repeat the same phrase each time. Examples:
- "I'll make sure the team gets this and they'll be in touch."
- "I'll pass that on to the team now."
- "The team will be in contact with you shortly."
- "I'll flag this for management — someone will follow up with you."
- "Leave it with me, the team will get back to you."

PHOTO POLICY:
Never ask clients to upload or send photos during the phone conversation. If photos are needed — for example for a complaint, reaction, or correction request — ask the caller to send their photos separately via WhatsApp to 07748 252038, including their name and appointment date. Do not offer any other method for receiving photos.
Do not ask clients to describe medical symptoms in detail. Collect basic information and escalate to management.

CALLS OUTSIDE OPENING HOURS:
If a caller contacts outside of opening hours, let them know the studio is currently closed and give the relevant opening times. Encourage them to book or leave a message via the website at lash zone london dot com.
"""


class LashZoneReceptionist:
    """
    AI Receptionist for Lash Zone London
    Loads comprehensive system prompt from config
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = os.environ.get("AI_MODEL", "gpt-4o-mini")
        self.voice = os.environ.get("AI_VOICE", "alloy")
        self.max_tokens = 150  # Keep spoken replies short and natural for phone calls
        self.min_sentences = 1  # Spoken replies should be concise
        self._system_prompt = None
        self._config_loaded = False

        # Escalation keywords
        self.escalation_keywords = [
            "complaint", "unhappy", "dissatisfied", "angry", "frustrated",
            "refund", "money back", "not happy", "terrible", "worst",
            "allergic", "reaction", "swelling", "irritation", "rash",
            "manager", "supervisor", "owner", "speak to someone in charge",
            "serious", "emergency", "medical"
        ]

    async def load_config(self):
        """Load system prompt - uses embedded SYSTEM_PROMPT constant directly"""
        if self._config_loaded:
            return
        # Use the embedded luxury system prompt directly
        # (avoids circular HTTP call and startup race conditions)
        self._system_prompt = SYSTEM_PROMPT
        self._config_loaded = True
        print("ÃÂ¢ÃÂÃÂ Loaded luxury Lash Zone London system prompt")
    @property
    def system_prompt(self) -> str:
        """Get the current system prompt, loading from config if needed"""
        if not self._config_loaded:
            # Run synchronously on first access (will be called from startup)
            pass
        return self._system_prompt or SYSTEM_PROMPT

    async def generate_response(self, call_context: CallContext, user_message: str) -> str:
        """
        Generate AI response using GPT-4o
        """
        # Ensure config is loaded
        if not self._config_loaded:
            await self.load_config()

        # Add user message to history
        call_context.add_message("user", user_message)

        # Check for escalation keywords
        if self._should_escalate(user_message):
            call_context.escalation = EscalationRequest(
                escalation_type=EscalationType.COMPLEX_ISSUE,
                issue_summary=f"Caller expressed concern: {user_message}"
            )

        # Detect if the caller wants a booking link / wants to book / wants pricing.
        # When detected, flag the context so the gather endpoint sends the SMS link.
        if self._wants_booking_link(user_message):
            call_context.needs_booking_link = True

        # Detect if the caller wants a follow-up / callback / more information.
        # When detected, flag the context so the gather endpoint saves the request
        # to Supabase and emails a notification. Existing flows are unaffected.
        if self._wants_followup(user_message):
            call_context.needs_followup = True

        # Build messages for API
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for msg in call_context.conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add context about booking link status
        if call_context.needs_booking_link and not call_context.booking_link_sent:
            messages.append({
                "role": "system",
                "content": "IMPORTANT: The caller needs a booking link. When appropriate, offer to send one via SMS."
            })

        # Generate response with comprehensive detail
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,  # Loaded from database config
            temperature=0.7
        )

        ai_response = response.choices[0].message.content

        # Ensure minimum sentences by adding a system hint if response is too short
        # Add to conversation history
        call_context.add_message("assistant", ai_response)

        return ai_response

    def _count_sentences(self, text: str) -> int:
        """Count approximate number of sentences in text"""
        import re
        # Count sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])

    def _should_escalate(self, message: str) -> bool:
        """Check if message contains escalation keywords"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.escalation_keywords)

    def _wants_booking_link(self, message: str) -> bool:
        """Detect whether the caller is asking to book or to be sent the booking link."""
        message_lower = message.lower()
        booking_phrases = [
            "send me a link", "send a link", "send me the link", "send the link",
            "send me a text", "send me a message", "text me", "send it to me",
            "send it over", "send that over", "send it across",
            "book", "booking", "appointment", "reserve", "schedule",
            "how do i book", "where do i book", "sign up", "make a booking",
            "link to book", "booking link", "send me details", "send me info",
            "price", "prices", "pricing", "how much", "cost",
        ]
        if any(phrase in message_lower for phrase in booking_phrases):
            return True
        return False

    def _wants_followup(self, message: str) -> bool:
        """Detect whether the caller is asking for a follow-up, callback, or more information."""
        message_lower = message.lower()
        followup_phrases = [
            "call me back", "callback", "call back", "ring me back", "ring me",
            "someone call me", "somebody call me", "have someone call", "get back to me",
            "have someone get back", "please have someone", "someone to contact me",
            "contact me", "email me more", "email me information", "more information",
            "more details", "owner to contact", "speak to the owner", "have the owner",
            "training course", "training courses", "course information", "information about training",
        ]
        return any(phrase in message_lower for phrase in followup_phrases)

    async def generate_speech(self, text: str, voice: str = "alloy") -> bytes:
        """
        Generate speech from text using OpenAI TTS
        Returns audio bytes
        """
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="ulaw"  # 8-bit ulaw for Twilio compatibility
        )

        return response.content

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio using OpenAI Whisper
        """
        import io

        # Create file-like object with wav extension for Whisper
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"

        try:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            return transcript.text if transcript.text else ""
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""


# Singleton instance
receptionist = LashZoneReceptionist()
