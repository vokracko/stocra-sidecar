from typing import Dict

import sentry_sdk
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware import Middleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from genesis.blockchain.factory import NodeAdapterFactory, ParserFactory
from genesis.logging import logger
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from sidecar import routes_v1_0
from sidecar.auth import api_key_header_auth
from sidecar.config import CONFIG, REDIS
from sidecar.models import Limit

middleware = []

if CONFIG.sentry_dsn:
    sentry_sdk.init(  # pylint: disable=abstract-class-instantiated
        dsn=CONFIG.sentry_dsn,
        environment=CONFIG.environment,
        traces_sample_rate=0.0001,
    )
    middleware = [Middleware(SentryAsgiMiddleware)]

app = FastAPI(openapi_url=None, middleware=middleware)
app.include_router(routes_v1_0.router, prefix="/v1.0")


@app.on_event("startup")
async def startup() -> None:
    CONFIG.adapter = await NodeAdapterFactory.get_client(
        CONFIG.node_blockchain, url=CONFIG.node_url, token=CONFIG.node_token
    )
    CONFIG.parser = await ParserFactory.get_parser(CONFIG.node_blockchain, CONFIG.adapter)
    logger.info("Starting sidecar for %s connecting to %s", CONFIG.node_blockchain.blockchain_name, CONFIG.node_url)


@app.get("/")
async def index() -> Dict:
    return RedirectResponse("v1.0")


@app.post("/limit")
async def sync_limit(
    limit: Limit,
    api_key_header: HTTPAuthorizationCredentials = Depends(api_key_header_auth),
) -> None:
    if api_key_header is None or api_key_header.credentials != CONFIG.sidecar_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    new_value = await REDIS.incrby(limit.key, limit.value)
    local_ttl = await REDIS.ttl(limit.key)
    logger.debug(
        "sync limit: %s, new value: %d, local ttl: %d, remote ttl: %d",
        limit.key,
        new_value,
        local_ttl,
        limit.ttl,
    )
    if local_ttl < 0 or local_ttl > limit.ttl:
        await REDIS.expire(limit.key, limit.ttl)
