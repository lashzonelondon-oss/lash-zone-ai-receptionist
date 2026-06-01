"""
AI Receptionist Backend Package
"""

from .api.routes import app
from .ai.receptionist import receptionist
from .voice_handler import voice_handler
from .database.supabase_client import db