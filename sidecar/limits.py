import math
from typing import Optional, Tuple

import aiohttp
from fastapi import Depends, HTTPException, Request, status
from genesis.logging import logger

from sidecar.async_utils import create_task_safely
from sidecar.auth import get_api_key_and_limit
from sidecar.config import CONFIG, REDIS
from sidecar.models import Limit


async def rate_limiter(
    request: Request, api_key_info: Tuple[Optional[str], float] = Depends(get_api_key_and_limit)
) -> None:
    api_key, api_key_limit = api_key_info
    if api_key_limit == math.inf:
        logger.info("api_limits: %s: unlimited", api_key)
        return

    client_ip = request.headers.get("x-real-ip", request.client.host)
    key = get_limits_key(api_key, client_ip, CONFIG.node_blockchain.blockchain_name)
    await apply_limits(key, api_key_limit)


def get_limits_key(api_key: Optional[str], client_ip: str, blockchain_name: str) -> str:
    template = f"{blockchain_name}/limits/{{type}}/{{value}}"

    if api_key:
        return template.format(type="api_key", value=api_key)

    return template.format(type="ip", value=client_ip)


async def apply_limits(key: str, max_limit: float) -> None:
    current_usage = await REDIS.get(key)
    logger.info("api_limits: %s, %s/%s", key, int(current_usage) if current_usage else 0, max_limit)

    if current_usage is None:
        await REDIS.set(key, 1, ex=CONFIG.limit_interval)
        return

    current_usage = int(current_usage)

    if current_usage >= max_limit:
        retry_after = await REDIS.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
        )

    new_usage = await REDIS.incr(key)

    if new_usage % CONFIG.sidecar_limit_sync_interval == 0:
        create_task_safely(broadcast_limit_consumption(key))


async def broadcast_limit_consumption(redis_key: str) -> None:
    current_ttl = await REDIS.ttl(redis_key)

    for other_redis_url in CONFIG.sidecar_urls:
        try:
            async with aiohttp.ClientSession() as session:
                logger.warning(
                    "json %s",
                    Limit(
                        key=redis_key,
                        value=CONFIG.sidecar_limit_sync_interval,
                        ttl=current_ttl,
                    ).dict(),
                )
                response = await session.post(
                    url=f"{other_redis_url}/limit",
                    json=Limit(
                        key=redis_key,
                        value=CONFIG.sidecar_limit_sync_interval,
                        ttl=current_ttl,
                    ).dict(),
                    headers={"Authorization": f"Bearer {CONFIG.sidecar_token}"},
                    raise_for_status=True,
                    allow_redirects=False,
                )
                logger.warning("Response json %s:", await response.json())
        except Exception:  # pylint: disable=broad-except
            logger.exception("Syncing limit failed")
