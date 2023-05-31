from genesis.blockchain.exceptions import DoesNotExist
from genesis.models import PlainBlock, PlainTransaction

from sidecar.config import CONFIG


async def get_block_latest() -> PlainBlock:
    block_number = await CONFIG.adapter.get_block_count()
    return await get_block_by_height(block_number)


async def get_block_by_height(height: int) -> PlainBlock:
    if int(height) < 1:
        raise DoesNotExist("Unable to get blocks with height < 1")

    raw_block = await CONFIG.adapter.get_block_by_height(height=int(height))
    return await CONFIG.parser.decode_block(raw_block)


async def get_block_by_hash(block_hash: str) -> PlainBlock:
    raw_block = await CONFIG.adapter.get_block_by_hash(block_hash=block_hash)
    return await CONFIG.parser.decode_block(raw_block)


async def get_transaction_by_hash(transaction_hash: str) -> PlainTransaction:
    raw_transaction = await CONFIG.adapter.get_transaction(transaction_hash)
    return await CONFIG.parser.decode_transaction(raw_transaction)
