from typing import Optional, Set

import aioredis
from genesis.blockchain.adapter import NodeAdapter
from genesis.blockchain.parser import Parser
from genesis.blockchains import Blockchain
from pydantic import AnyUrl, BaseSettings, validator


class Settings(BaseSettings):
    node_blockchain: Blockchain
    node_url: AnyUrl
    node_token: str
    redis_host: str
    limit_default: int = 10_000
    limit_interval: int = 60 * 60 * 24
    environment: str = "dev"
    adapter: Optional[NodeAdapter] = None
    parser: Optional[Parser] = None
    sidecar_token: Optional[str] = None
    sidecar_urls: Set[str] = set()
    sidecar_limit_sync_interval: int = 1_000
    sentry_dsn: Optional[str] = None

    class Config:
        env_file = ".env"

    @validator("node_blockchain", pre=True)
    @classmethod
    def convert_node_blockchain(cls, value: str) -> Blockchain:
        return Blockchain.from_name(value)

    @property
    def api_key_hash(self) -> str:
        return f"{self.node_blockchain.blockchain_name}/api_keys"


CONFIG = Settings()
REDIS = aioredis.from_url(f"redis://{CONFIG.redis_host}")
