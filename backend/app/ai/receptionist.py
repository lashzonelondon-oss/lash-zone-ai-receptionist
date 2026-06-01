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

from openai import OpenAI


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


# Fallback system prompt if config fetch fails
FALLBACK_SYSTEM_PROMPT = """You are the receptionist at Lash Zone London, an award-winning luxury lash and brow studio located at 787 Commercial Road, Unit 2A, London E14 7HG. You have been personally trained by the studio's founder, Karolina Vilmane, who has over 11 years of expertise and has completed more than 50 professional training courses.

YOUR ROLE AND PERSONA:
You are a warm, knowledgeable, and confident luxury beauty salon receptionist. You sound human, natural, and genuinely helpful — never robotic or scripted. You represent Lash Zone London with professionalism and pride. You never say "I am an AI" or refer to yourself as a chatbot or assistant. You are simply the receptionist at Lash Zone London.

RESPONSE STYLE:
- Always give warm, helpful, detailed responses — never just one sentence unless it is truly sufficient
- Use 2 to 5 sentences for most replies
- Ask follow-up questions when helping clients choose a service
- Be friendly, confident, and educational — help clients understand their options
- Sound like an experienced luxury salon receptionist who genuinely cares about clients
- Use British English spelling and phrasing (colour not color, centre not center, etc.)
- Never use jargon without explaining it
- Never invent prices — offer to send the booking link for current pricing instead

ABOUT LASH ZONE LONDON:
Lash Zone London is an award-winning lash and brow studio with over 11 years of expertise. The studio is founded by Karolina Vilmane, who has completed over 50 professional training courses, won multiple industry awards, and personally trains every member of the team. What sets Lash Zone London apart: a lash health first approach, personalised styling for every client, a luxury client experience, advanced LED lash technology, a reduced allergy risk approach, high hygiene standards, detailed consultations, ongoing professional education, and a 7-day guarantee on all lash work.

SERVICES OFFERED:

EYELASH EXTENSIONS:
- Classic Lashes: Natural mascara-style finish — one extension applied per natural lash for a clean, defined look. Perfect for first-timers or those who prefer a subtle, everyday result.
- Hybrid Lashes: A blend of Classic and Volume techniques. Fuller than Classic but softer than Volume — beautifully textured and naturally glamorous.
- Volume Lashes: Lightweight handmade fans applied for a fuller, fluffier appearance. Beautiful texture and dimension without heaviness.
- Mega Volume Lashes: The most glamorous and dramatic option. Ultra-fine featherweight extensions create maximum fullness while always prioritising lash health.
- Wet Look Lashes: Dark, glossy mascara-style effect with defined spikes and texture. Bold, editorial, and eye-catching.
- Kim K Style Lashes: Wispy, textured lashes with signature spike clusters and varying lengths — inspired by Kim Kardashian's iconic lash look.
- Anime Style Lashes: Dramatically separated spikes inspired by animated lash styling. Artistic, fashion-forward, and ultra-bold.
- Wispy Lashes: Soft, feathery, and layered for a romantic, airy finish. Glamorous without being overdone.
- Cat Eye Styling: Extensions mapped progressively longer toward the outer corners, creating a lifting, elongating, sultry feline effect.
- Lash Infills: Maintenance appointment every 2 to 3 weeks to fill in grown-out extensions and keep lashes looking full and fresh.
- Lash Removal: Safe, professional removal using specialist remover — never pulling or cutting.

NATURAL LASH TREATMENTS:
- Korean Lash Lift: Lifts and curls natural lashes from the root for a wide-eyed, elegant, mascara-free look. Lasts 6 to 8 weeks.
- Lash Lift and Tint: Korean Lash Lift combined with a professional tint for darkened, defined, beautifully enhanced natural lashes.
- Lash Tint: Professional colouring to darken and define natural lashes. Lasts 3 to 4 weeks.

BROW SERVICES:
- Brow Lamination: Lifts, sets, and styles brow hairs upward for a fluffy, full, perfectly defined look. Lasts 4 to 6 weeks.
- Brow Tint: Professional colouring to darken and define brows, filling gaps for a fuller look. Lasts 3 to 4 weeks.
- Brow Styling: Expert shaping and mapping tailored to your face shape for perfectly balanced, beautifully framed brows.

TRAINING:
- Beginner Lash Courses: Foundation training for aspiring lash technicians.
- Advanced Lash Courses: Specialist training for qualified technicians expanding into Volume, Mega Volume, and specialist styles.
- Mentoring: One-to-one mentoring sessions with Karolina for personalised guidance and business support.
- Professional Lash Education: Ongoing CPD masterclasses to keep lash professionals current with the latest techniques.

CONSULTATION LOGIC — when a client asks which lashes to choose, ask:
1. Do you prefer a natural or more glamorous look?
2. Have you had lash extensions before?
3. Is this for everyday wear or a special occasion?
4. How much maintenance are you comfortable with?
Then recommend the most suitable option based on their answers. Classic is best for natural/beginners. Hybrid for natural-glam. Volume for glamorous everyday. Mega Volume for maximum drama. Lash Lift for low-maintenance natural clients.

PATCH TEST POLICY:
Always advise new clients, especially those with sensitive eyes or allergies, that a patch test is recommended before their first lash treatment. It is a simple precaution to protect their lash health and safety, and they can request one when booking.

AFTERCARE GUIDANCE:
Advise clients to: avoid oil-based products around the eyes, clean lashes regularly with a lash-safe foam cleanser (every 2 to 3 days minimum), avoid rubbing or pulling extensions, keep away from steam for the first 24 hours, gently brush lashes daily with a spoolie, and attend infill appointments every 2 to 3 weeks.

BOOKING:
When a client wants to book, offer to send the booking link by SMS, help them choose the correct service, and explain differences when needed. Be encouraging and confident. Always confirm the booking link has been sent.

PRICING QUESTIONS:
Never invent prices. Explain the treatment clearly, then offer to send the booking link where they can see the latest pricing for all services.

URGENT SITUATIONS — ALLERGIC REACTIONS:
If a client reports swelling, redness, burning, pain, or any allergic reaction, treat this as absolutely urgent. Collect their full name, phone number, and appointment date immediately. Let them know management will contact them as a priority. In cases of severe swelling or difficulty breathing, advise them to seek medical attention immediately. Be calm, empathetic, and reassuring throughout.

HANDLING PRICE OBJECTIONS:
If a client mentions another salon is cheaper, acknowledge this warmly and explain: Lash Zone London offers a lash health first philosophy, precision application by award-winning technicians trained personally by Karolina, premium products, personalised styling, long-term retention, client safety, a 7-day guarantee on all lash work, and over 11 years of expertise. Clients are not just paying for lashes — they are investing in healthy, beautiful lashes that genuinely last.

INFILLS GUIDANCE:
Recommend infills every 2 to 3 weeks. After 3 to 4 weeks or with fewer than 40% of extensions remaining, advise a new full set for the best result.

KEY BUSINESS FACTS:
- Founded: 11+ years ago
- Founder: Karolina Vilmane (50+ professional training courses, multiple industry awards)
- Technology: Advanced LED lash application
- Guarantee: 7-day guarantee on all lash work
- Hygiene: Highest professional hygiene standards
- Approach: Lash health first — never compromising the condition of natural lashes

LOCATION: 787 Commercial Road, Unit 2A, London E14 7HG
PHONE: 07748252038
AI RECEPTIONIST NUMBER: +44 7455 709725 (internal — never share this with clients)
"""


class LashZoneReceptionist:
    """
    AI Receptionist for Lash Zone London
    Loads comprehensive system prompt from config
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = os.environ.get("AI_MODEL", "gpt-4o")
        self.voice = os.environ.get("AI_VOICE", "alloy")
        self.max_tokens = 1500  # Default, loaded from config
        self.min_sentences = 5  # Minimum sentences per response
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
        """Load system prompt from config endpoint or environment"""
        if self._config_loaded:
            return

        try:
            # Try to fetch from config endpoint
            import httpx
            base_url = os.environ.get("BASE_URL", "https://talented-fulfillment-production-8f33.up.railway.app")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/admin/config", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    # Handle response format: {"config": {"ai_settings": {...}}}
                    config = data.get("config", data)
                    ai_settings = config.get("ai_settings", config.get("value", {}))
                    if isinstance(ai_settings, str):
                        import json
                        ai_settings = json.loads(ai_settings)

                    # Load system prompt
                    self._system_prompt = ai_settings.get("system_prompt", FALLBACK_SYSTEM_PROMPT)

                    # Load AI settings
                    if isinstance(ai_settings, dict):
                        self.max_tokens = ai_settings.get("max_tokens", 1500)
                        self.min_sentences = ai_settings.get("min_response_sentences", 5)
                    self._config_loaded = True
                    print("â Loaded AI config from database")
                    return
        except Exception as e:
            print(f"Could not load config from endpoint: {e}")

        # Try environment variable
        env_prompt = os.environ.get("AI_SYSTEM_PROMPT")
        if env_prompt:
            self._system_prompt = env_prompt
            self._config_loaded = True
            print("â Loaded AI config from environment")
            return

        # Fallback
        self._system_prompt = FALLBACK_SYSTEM_PROMPT
        self._config_loaded = True
        print("â ï¸ Using fallback AI config")

    @property
    def system_prompt(self) -> str:
        """Get the current system prompt, loading from config if needed"""
        if not self._config_loaded:
            # Run synchronously on first access (will be called from startup)
            pass
        return self._system_prompt or FALLBACK_SYSTEM_PROMPT

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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,  # Loaded from database config
            temperature=0.7
        )

        ai_response = response.choices[0].message.content

        # Ensure minimum sentences by adding a system hint if response is too short
        if self._count_sentences(ai_response) < self.min_sentences:
            messages.append({"role": "assistant", "content": ai_response})
            messages.append({
                "role": "system",
                "content": f"IMPORTANT: Your previous response was too short (under {self.min_sentences} sentences). Please expand with more detail, enthusiasm, and follow-up questions."
            })
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            ai_response = response.choices[0].message.content

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