from typing import Dict

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse
from genesis.logging import logger
from genesis.models import PlainBlock, PlainTransaction, TokenInfo

from sidecar.caching import cache_response
from sidecar.config import CONFIG
from sidecar.http_transformations import transform_to_http_exception
from sidecar.limits import rate_limiter
from sidecar.operations_v1_0 import (
    get_block_by_hash,
    get_block_by_height,
    get_block_latest,
    get_transaction_by_hash,
)

router = APIRouter()


@router.get("/", response_class=ORJSONResponse)
async def index() -> Dict:
    endpoints = []
    for route in router.routes:
        if route.name is not None:
            endpoints.append(f"/v1.0{route.path}")

    return {"endpoints": endpoints}


@router.get(
    "/blocks/latest",
    response_model=PlainBlock,
    response_class=ORJSONResponse,
    dependencies=[Depends(rate_limiter)],
)
async def route_get_latest_block() -> ORJSONResponse:
    logger.info("%s: get_latest_block()", CONFIG.node_blockchain.blockchain_name)

    with transform_to_http_exception():
        return await get_block_latest()


@router.get(
    "/blocks/{block_height:int}",
    response_model=PlainBlock,
    response_class=ORJSONResponse,
    dependencies=[Depends(rate_limiter)],
)
@cache_response(seconds=600, extend_life_on_hit=False)
async def route_get_block_by_height(block_height: int) -> PlainBlock:
    logger.info("%s: route_get_block_by_height(%s)", CONFIG.node_blockchain.blockchain_name, block_height)

    with transform_to_http_exception():
        return await get_block_by_height(block_height)


@router.get(
    "/blocks/{block_hash:str}",
    response_model=PlainBlock,
    response_class=ORJSONResponse,
    dependencies=[Depends(rate_limiter)],
)
@cache_response(seconds=600)
async def route_get_block_by_hash(block_hash: str) -> PlainBlock:
    logger.info("%s: route_get_block_by_hash(%s)", CONFIG.node_blockchain.blockchain_name, block_hash)

    with transform_to_http_exception():
        return await get_block_by_hash(block_hash)


@router.get(
    "/transactions/{transaction_hash:str}",
    response_model=PlainTransaction,
    response_class=ORJSONResponse,
    dependencies=[Depends(rate_limiter)],
)
@cache_response(seconds=600)
async def route_get_transaction_by_hash(transaction_hash: str) -> PlainTransaction:
    logger.info("%s: get_transaction_by_hash(%s)", CONFIG.node_blockchain.blockchain_name, transaction_hash)

    with transform_to_http_exception():
        return await get_transaction_by_hash(transaction_hash)


@router.get("/status", response_class=ORJSONResponse)
async def get_status() -> ORJSONResponse:
    response_ok = ORJSONResponse(content=dict(status="ok"), status_code=status.HTTP_200_OK)
    response_ko = ORJSONResponse(content=dict(status="ko"), status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        await route_get_latest_block()
    except Exception:  # pylint: disable=broad-except
        logger.exception("Status: get latest block")
        return response_ko

    return response_ok


@router.get("/tokens", response_class=ORJSONResponse)
async def get_tokens() -> Dict[str, TokenInfo]:
    return CONFIG.parser.TOKENS
