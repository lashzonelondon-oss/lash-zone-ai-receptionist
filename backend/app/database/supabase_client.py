"""
Database operations using Supabase
Handles all data storage for calls, appointments, clients, and configurations
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Supabase configuration
supabase_url = os.environ.get("SUPABASE_URL")
supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")

# Lazy Supabase client initialization - created on first use to avoid startup crashes
_supabase_client = None
_service_client = None

def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _supabase_client = create_client(url, key)
    return _supabase_client

def get_service_client() -> Client:
    global _service_client
    if _service_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _service_client = create_client(url, key)
    return _service_client

# Backward-compatible aliases (used throughout the class)
supabase = None  # Will be initialised lazily
service_client = None  # Will be initialised lazily


class DatabaseManager:
    """Manages all database operations"""

    # ==================== CALLS ====================

    async def create_call(self, call_data: Dict[str, Any]) -> Optional[Dict]:
        """Create a new call record"""
        try:
            data = {
                "caller_number": call_data.get("caller_number"),
                "duration_seconds": call_data.get("duration_seconds", 0),
                "outcome": call_data.get("outcome"),
                "transcript_json": json.dumps(call_data.get("transcript", [])),
                "recording_url": call_data.get("recording_url"),
                "created_at": datetime.now().isoformat()
            }

            result = get_service_client().table("calls").insert(data).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error creating call: {e}")
            return None

    async def update_call(self, call_id: str, update_data: Dict[str, Any]) -> bool:
        """Update call record"""
        try:
            update_data["updated_at"] = datetime.now().isoformat()

            result = get_service_client().table("calls").update(update_data).eq("id", call_id).execute()
            return len(result.data) > 0

        except Exception as e:
            print(f"Error updating call: {e}")
            return False

    async def get_call(self, call_id: str) -> Optional[Dict]:
        """Get call by ID"""
        try:
            result = get_supabase_client().table("calls").select("*").eq("id", call_id).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error getting call: {e}")
            return None

    async def get_calls(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get recent calls"""
        try:
            result = get_supabase_client().table("calls").select("*").order(
                "created_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            return result.data

        except Exception as e:
            print(f"Error getting calls: {e}")
            return []

    async def search_calls(self, query: str) -> List[Dict]:
        """Search calls by caller number or transcript"""
        try:
            result = get_supabase_client().table("calls").select("*").or_(
                f"caller_number.ilike.%{query}%",
                f"transcript_json.ilike.%{query}%"
            ).order("created_at", desc=True).execute()

            return result.data

        except Exception as e:
            print(f"Error searching calls: {e}")
            return []

    # ==================== APPOINTMENTS ====================

    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Optional[Dict]:
        """Create new appointment"""
        try:
            data = {
                "client_name": appointment_data.get("client_name"),
                "client_phone": appointment_data.get("client_phone"),
                "client_email": appointment_data.get("client_email"),
                "service": appointment_data.get("service"),
                "requested_date": appointment_data.get("requested_date"),
                "requested_time": appointment_data.get("requested_time"),
                "status": appointment_data.get("status", "pending"),
                "booked_via": appointment_data.get("booked_via", "ai_phone"),
                "call_id": appointment_data.get("call_id"),
                "notes": appointment_data.get("notes"),
                "created_at": datetime.now().isoformat()
            }

            result = get_service_client().table("appointments").insert(data).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error creating appointment: {e}")
            return None

    async def update_appointment(self, appointment_id: str, update_data: Dict[str, Any]) -> bool:
        """Update appointment"""
        try:
            update_data["updated_at"] = datetime.now().isoformat()

            result = get_service_client().table("appointments").update(update_data).eq("id", appointment_id).execute()
            return len(result.data) > 0

        except Exception as e:
            print(f"Error updating appointment: {e}")
            return False

    async def get_appointments(
        self,
        date: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get appointments with optional filters"""
        try:
            query = get_supabase_client().table("appointments").select("*")

            if date:
                query = query.eq("requested_date", date)

            if status:
                query = query.eq("status", status)

            result = query.order("requested_date").order("requested_time").limit(limit).execute()
            return result.data

        except Exception as e:
            print(f"Error getting appointments: {e}")
            return []

    async def check_availability(self, date: str, time: str, duration_minutes: int = 60) -> bool:
        """Check if time slot is available"""
        try:
            # Get all appointments for the date
            result = get_supabase_client().table("appointments").select("*").eq(
                "requested_date", date
            ).eq("status", "confirmed").execute()

            appointments = result.data

            # Simple overlap check
            requested_start = self._time_to_minutes(time)
            requested_end = requested_start + duration_minutes

            for apt in appointments:
                apt_start = self._time_to_minutes(apt.get("requested_time", "00:00"))
                apt_end = apt_start + duration_minutes

                # Check for overlap
                if not (requested_end <= apt_start or requested_start >= apt_end):
                    return False

            return True

        except Exception as e:
            print(f"Error checking availability: {e}")
            return True  # Default to available on error

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight"""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    # ==================== CLIENTS ====================

    async def create_or_update_client(self, client_data: Dict[str, Any]) -> Optional[Dict]:
        """Create or update client record"""
        try:
            phone = client_data.get("client_phone")

            # Check if client exists
            existing = get_supabase_client().table("clients").select("*").eq("phone", phone).execute()

            if existing.data:
                # Update existing
                client_id = existing.data[0]["id"]
                update_data = {k: v for k, v in client_data.items() if v}
                update_data["updated_at"] = datetime.now().isoformat()

                result = get_service_client().table("clients").update(update_data).eq("id", client_id).execute()
                return result.data[0] if result.data else None

            else:
                # Create new
                data = {
                    "name": client_data.get("client_name"),
                    "phone": phone,
                    "email": client_data.get("client_email"),
                    "preferred_service": client_data.get("preferred_service"),
                    "visit_count": 1,
                    "created_at": datetime.now().isoformat()
                }

                result = get_service_client().table("clients").insert(data).execute()
                return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error creating/updating client: {e}")
            return None

    async def get_client_by_phone(self, phone: str) -> Optional[Dict]:
        """Get client by phone number"""
        try:
            result = get_supabase_client().table("clients").select("*").eq("phone", phone).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error getting client: {e}")
            return None

    # ==================== ESCALATIONS ====================

    async def create_escalation(self, escalation_data: Dict[str, Any]) -> Optional[Dict]:
        """Create escalation request"""
        try:
            data = {
                "call_id": escalation_data.get("call_id"),
                "client_name": escalation_data.get("client_name"),
                "client_phone": escalation_data.get("client_phone"),
                "issue_summary": escalation_data.get("issue_summary"),
                "details_json": json.dumps(escalation_data.get("details", {})),
                "priority": escalation_data.get("priority", "normal"),
                "status": escalation_data.get("status", "pending"),
                "resolved_at": None,
                "notes": escalation_data.get("notes"),
                "created_at": datetime.now().isoformat()
            }

            result = get_service_client().table("escalations").insert(data).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error creating escalation: {e}")
            return None

    async def get_escalations(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get escalation requests"""
        try:
            query = get_supabase_client().table("escalations").select("*")

            if status:
                query = query.eq("status", status)

            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data

        except Exception as e:
            print(f"Error getting escalations: {e}")
            return []

    async def resolve_escalation(self, escalation_id: str, notes: str = "") -> bool:
        """Mark escalation as resolved"""
        try:
            result = get_service_client().table("escalations").update({
                "status": "resolved",
                "resolved_at": datetime.now().isoformat(),
                "notes": notes
            }).eq("id", escalation_id).execute()

            return len(result.data) > 0

        except Exception as e:
            print(f"Error resolving escalation: {e}")
            return False

    # ==================== CONFIGURATION ====================

    async def get_config(self, key: str) -> Optional[str]:
        """Get configuration value"""
        try:
            result = get_supabase_client().table("studio_config").select("config_value").eq(
                "config_key", key
            ).execute()

            return result.data[0]["config_value"] if result.data else None

        except Exception as e:
            print(f"Error getting config: {e}")
            return None

    async def set_config(self, key: str, value: str) -> bool:
        """Set configuration value"""
        try:
            # Upsert
            result = get_service_client().table("studio_config").upsert({
                "config_key": key,
                "config_value": value,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="config_key").execute()

            return len(result.data) > 0

        except Exception as e:
            print(f"Error setting config: {e}")
            return False

    async def get_all_config(self) -> Dict[str, str]:
        """Get all configuration"""
        try:
            result = get_supabase_client().table("studio_config").select("*").execute()

            return {row["config_key"]: row["config_value"] for row in result.data}

        except Exception as e:
            print(f"Error getting all config: {e}")
            return {}

    # ==================== FAQS ====================

    async def get_faqs(self, active_only: bool = True) -> List[Dict]:
        """Get FAQ knowledge base"""
        try:
            query = get_supabase_client().table("faq_knowledge").select("*")

            if active_only:
                query = query.eq("active", True)

            result = query.order("category").execute()
            return result.data

        except Exception as e:
            print(f"Error getting FAQs: {e}")
            return []

    async def create_faq(self, faq_data: Dict[str, Any]) -> Optional[Dict]:
        """Create new FAQ"""
        try:
            data = {
                "question_pattern": faq_data.get("question_pattern"),
                "answer": faq_data.get("answer"),
                "category": faq_data.get("category", "general"),
                "active": faq_data.get("active", True),
                "created_at": datetime.now().isoformat()
            }

            result = get_service_client().table("faq_knowledge").insert(data).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error creating FAQ: {e}")
            return None

    async def update_faq(self, faq_id: str, update_data: Dict[str, Any]) -> bool:
        """Update FAQ"""
        try:
            update_data["updated_at"] = datetime.now().isoformat()

            result = get_service_client().table("faq_knowledge").update(update_data).eq("id", faq_id).execute()
            return len(result.data) > 0

        except Exception as e:
            print(f"Error updating FAQ: {e}")
            return False

    async def delete_faq(self, faq_id: str) -> bool:
        """Delete FAQ"""
        try:
            result = get_service_client().table("faq_knowledge").delete().eq("id", faq_id).execute()
            return True

        except Exception as e:
            print(f"Error deleting FAQ: {e}")
            return False


# Singleton instance
db = DatabaseManager()
