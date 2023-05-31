from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyQuery, HTTPAuthorizationCredentials, HTTPBearer

from sidecar.config import CONFIG, REDIS

api_key_query_auth = APIKeyQuery(name="api_key", auto_error=False)
api_key_header_auth = HTTPBearer(auto_error=False)


async def get_api_key(
    api_key_header: HTTPAuthorizationCredentials = Depends(api_key_header_auth),
    api_key_query: str = Security(api_key_query_auth),
) -> Optional[str]:
    return api_key_query or (api_key_header.credentials if api_key_header else None)


async def get_api_key_and_limit(api_key: Optional[str] = Depends(get_api_key)) -> Tuple[Optional[str], Optional[float]]:
    if not api_key:
        return None, CONFIG.limit_default

    api_key_limit = await REDIS.hget(CONFIG.api_key_hash, api_key)
    if api_key and not api_key_limit:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    return api_key, float(api_key_limit)
