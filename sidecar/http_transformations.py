from contextlib import contextmanager

from fastapi import HTTPException, status
from genesis.blockchain.exceptions import DoesNotExist, SkippedBlock, Unavailable
from genesis.logging import logger


@contextmanager
def transform_to_http_exception() -> None:
    try:
        yield
    except DoesNotExist as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except Unavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from exc
    except SkippedBlock as exc:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT) from exc
    except Exception as exc:
        logger.exception("%s", str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
