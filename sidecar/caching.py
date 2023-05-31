import asyncio
from functools import wraps
from typing import Any, Callable
from uuid import uuid4

from fastapi.responses import Response
from genesis.encoders import fast_serializer_to_bytes
from genesis.logging import logger
from genesis.profiling import log_duration

from sidecar.async_utils import create_task_safely
from sidecar.config import CONFIG, REDIS


def get_method_signature(func: Callable, args: Any, kwargs: Any) -> str:
    separator = ", "
    function_name = func.__name__
    args_string = separator.join(map(str, args)) if args else ""
    kwargs_string = separator.join([f"{k}={str(v)}" for k, v in kwargs.items()]) if kwargs else ""
    return f"{function_name}({args_string}{separator if args and kwargs else ''}{kwargs_string})"


def get_cache_key(signature: str) -> str:
    return f"{CONFIG.node_blockchain.blockchain_name}/cache/{signature}"


async def store_response(key: str, seconds: int, serialized: bytes) -> None:
    await REDIS.setex(key, seconds, serialized)


async def extend_expiry(key: str, seconds: int) -> None:
    await REDIS.expire(key, seconds)


def cache_response(seconds: int, extend_life_on_hit: bool = True) -> Callable:
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        async def inner(*args: Any, **kwargs: Any) -> Any:
            signature = get_method_signature(func, args, kwargs)
            key = get_cache_key(signature)
            request_id = f"{signature}#{str(uuid4())}"
            with log_duration(f"profiling: {request_id}: whole"):
                logger.info("Active tasks count: %d", len([task for task in asyncio.all_tasks() if not task.done()]))

                with log_duration(f"profiling: {request_id}: inner: REDIS.get"):
                    response = await REDIS.get(key)

                if response:
                    if extend_life_on_hit:
                        with log_duration(f"profiling: {request_id}: inner: REDIS.expire"):
                            create_task_safely(extend_expiry(key, seconds))
                    logger.info("Cache hit: %s", key)
                    with log_duration(f"profiling: {request_id}: inner: returning cached response"):
                        return Response(content=response, media_type="application/json")

                logger.info("Cache miss: %s", key)
                with log_duration(f"profiling: {request_id}: inner: call real function"):
                    response = await func(*args, **kwargs)

                with log_duration(f"profiling: {request_id}: inner: fast serializer"):
                    serialized = fast_serializer_to_bytes(response.dict())

                with log_duration(f"profiling: {request_id}: inner: REDIS.setex"):
                    create_task_safely(store_response(key, seconds, serialized))
                return response

        return inner

    return wrapper
