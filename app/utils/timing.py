import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


@contextmanager
def timed(operation: str) -> Iterator[None]:
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        logger.info("%s completed in %.2f ms", operation, duration_ms)