"""
Supabase Official Python SDK Client Integration
Provides cloud database operations and synchronization via supabase-py.
"""
from typing import Optional, List, Dict, Any
import os
from supabase import create_client, Client
from app.config import settings

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Returns singleton instance of the official Supabase Client."""
    global _supabase_client
    if _supabase_client is None:
        url = settings.SUPABASE_URL or os.getenv("SUPABASE_URL")
        key = settings.SUPABASE_KEY or os.getenv("SUPABASE_KEY")
        if url and key:
            try:
                _supabase_client = create_client(url, key)
            except Exception as e:
                print(f"[WARNING] Could not initialize Supabase SDK client: {e}")
                return None
    return _supabase_client


def is_supabase_enabled() -> bool:
    """Checks if Supabase credentials are configured."""
    return bool((settings.SUPABASE_URL or os.getenv("SUPABASE_URL")) and 
                (settings.SUPABASE_KEY or os.getenv("SUPABASE_KEY")))


def sync_patient_to_supabase(patient_dict: dict) -> bool:
    """
    Upserts a patient record to Supabase Cloud using the official Supabase SDK.
    Returns True if successfully synchronized.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        # Convert date and datetime objects to ISO strings if needed
        data = {}
        for k, v in patient_dict.items():
            if hasattr(v, "isoformat"):
                data[k] = v.isoformat()
            else:
                data[k] = v

        client.table("patients").upsert(data, on_conflict="patient_id").execute()
        return True
    except Exception as e:
        # If table doesn't exist yet in Supabase, log notice gracefully
        print(f"[SUPABASE SDK SYNC NOTICE] {e}")
        return False
