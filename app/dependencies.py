from typing import Dict, Optional

from fastapi import Header, HTTPException

API_KEYS: Dict[str, str] = {
    "super-duper-secret-key": "user-default",
    "kislaya-key": "user-kislaya",
    "kislaya2-key": "user-kislaya2",
}


def verify_api_key(x_api_key: str = Header(...)) -> str:
    user_id = API_KEYS.get(x_api_key)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user_id


def resolve_user_id(api_key: str) -> Optional[str]:
    return API_KEYS.get(api_key)
