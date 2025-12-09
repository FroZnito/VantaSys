import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import Optional
import os

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)) -> Optional[str]:
    """
    Validates API Key from header if VANTASYS_TOKEN env var is set.
    """
    expected_key = os.getenv("VANTASYS_TOKEN")
    
    # If no token is configured, authentication is disabled (dev mode friendly)
    if not expected_key:
        return None

    if api_key_header == expected_key:
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )
