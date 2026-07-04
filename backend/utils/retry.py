"""
Resilience utilities — exponential backoff retry wrapper for
LLM calls, embedding API, Pinecone, and Elasticsearch.
"""
import asyncio
import logging
import functools
import time
from typing import Callable, TypeVar, Any, Optional

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default retry config
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 0.5   # seconds
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_MAX_DELAY = 8.0


def retry_sync(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: tuple = (Exception,),
):
    """
    Synchronous retry decorator with exponential backoff.
    Usage:
        @retry_sync(max_retries=3)
        def fetch_pdf(url): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        break
                    logger.warning(
                        f"[retry] {func.__name__} attempt {attempt+1}/{max_retries} "
                        f"failed: {e}. Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            raise last_exc
        return wrapper
    return decorator


def retry_async(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: tuple = (Exception,),
):
    """
    Async retry decorator with exponential backoff.
    Usage:
        @retry_async(max_retries=3)
        async def embed_query(text): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        break
                    logger.warning(
                        f"[retry] {func.__name__} attempt {attempt+1}/{max_retries} "
                        f"failed: {e}. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            raise last_exc
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Simple circuit breaker — trips after `failure_threshold` consecutive
    failures, then stays OPEN for `reset_timeout` seconds before allowing
    one trial request.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        name: str = "circuit",
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.name = name
        self._state = self.CLOSED
        self._failures = 0
        self._opened_at: Optional[float] = None

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                self._state = self.HALF_OPEN
        return self._state

    def record_success(self):
        self._failures = 0
        self._state = self.CLOSED

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold:
            if self._state != self.OPEN:
                logger.error(f"[CircuitBreaker:{self.name}] TRIPPED after {self._failures} failures")
            self._state = self.OPEN
            self._opened_at = time.monotonic()

    def is_allowed(self) -> bool:
        s = self.state
        if s == self.CLOSED:
            return True
        if s == self.HALF_OPEN:
            return True   # Allow one trial
        logger.warning(f"[CircuitBreaker:{self.name}] OPEN — request blocked")
        return False


# Pre-built circuit breakers for main external services
groq_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=30, name="groq")
pinecone_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=20, name="pinecone")
elasticsearch_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=20, name="elasticsearch")
