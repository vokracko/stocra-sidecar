from unittest.mock import patch

import pytest
import pytest_asyncio
import sentry_sdk
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from genesis.blockchain.adapter import NodeAdapter
from genesis.blockchain.bitcoin.tests.fixtures.block import BLOCK_DECODED, BLOCK_JSON
from genesis.blockchain.bitcoin.tests.fixtures.pubkey_transaction import (
    TRANSACTION_DECODED,
    TRANSACTION_JSON,
)
from genesis.blockchain.parser import Parser
from genesis.blockchains import Blockchain

from sidecar.config import CONFIG
from sidecar.routes import app

BLOCK_DICT = BLOCK_JSON
BLOCK = BLOCK_DECODED
TRANSACTION_DICT = TRANSACTION_JSON
TRANSACTION = TRANSACTION_DECODED

CONFIG.node_blockchain = Blockchain.ETHEREUM


class NodeAdapterStub(NodeAdapter):
    ...


class ParserStub(Parser):
    ...


NODE_ADAPTER = NodeAdapterStub(url="", token="")
PARSER = ParserStub(NODE_ADAPTER)


@pytest.fixture(autouse=True, scope="session")
def disable_sentry() -> None:
    sentry_sdk.init(dsn="")


@pytest.fixture
def test_client() -> TestClient:
    with patch("sidecar.config.CONFIG.adapter", new=NODE_ADAPTER):
        with patch("sidecar.config.CONFIG.parser", new=PARSER):
            yield TestClient(app)


@pytest_asyncio.fixture(autouse=True, scope="function")
async def fake_redis() -> FakeRedis:
    instance = FakeRedis()
    with patch("sidecar.auth.REDIS", instance):
        with patch("sidecar.limits.REDIS", instance):
            with patch("sidecar.caching.REDIS", instance):
                with patch("sidecar.routes.REDIS", instance):
                    yield instance
