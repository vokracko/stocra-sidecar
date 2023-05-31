from typing import Optional

from fastapi import Response
from flexmock import flexmock
from genesis.blockchain.tests.utils import AwaitableValue
from starlette import status
from starlette.testclient import TestClient

from sidecar.tests.conftest import BLOCK, BLOCK_DICT, NODE_ADAPTER, PARSER


def make_request_for_block_by_hash(
    test_client: TestClient,
    api_key_query: Optional[str] = None,
    api_key_header: Optional[str] = None,
    expected_status_code: int = status.HTTP_200_OK,
) -> Response:
    flexmock(NODE_ADAPTER).should_receive("get_block_by_hash").with_args("hash").and_return(AwaitableValue(BLOCK_DICT))
    flexmock(PARSER).should_receive("decode_block").with_args(BLOCK_DICT).and_return(AwaitableValue(BLOCK))

    params = None
    headers = None

    if api_key_query:
        params = dict(api_key=api_key_query)

    if api_key_header:
        headers = dict(Authorization=f"Bearer {api_key_header}")

    response = test_client.get(f"/v1.0/blocks/hash", params=params, headers=headers)
    assert response.status_code == expected_status_code
    return response


def make_request_for_block_by_height(
    test_client: TestClient,
    api_key_query: Optional[str] = None,
    api_key_header: Optional[str] = None,
    expected_status_code: int = status.HTTP_200_OK,
) -> Response:
    flexmock(NODE_ADAPTER).should_receive("get_block_by_height").with_args(10).and_return(AwaitableValue(BLOCK_DICT))
    flexmock(PARSER).should_receive("decode_block").with_args(BLOCK_DICT).and_return(AwaitableValue(BLOCK))

    params = None
    headers = None

    if api_key_query:
        params = dict(api_key=api_key_query)

    if api_key_header:
        headers = dict(Authorization=f"Bearer {api_key_header}")

    response = test_client.get(f"/v1.0/blocks/10", params=params, headers=headers)
    assert response.status_code == expected_status_code
    return response
