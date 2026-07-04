"""
LangSmith tracing — wraps the pipeline with observability.
Free tier: 5k traces/month.
"""
import os
import functools
import logging
from typing import Callable
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _setup_langsmith():
    """Configure LangSmith environment variables."""
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info(f"LangSmith tracing enabled for project: {settings.langsmith_project}")
    else:
        logger.info("LangSmith API key not set — tracing disabled")


_setup_langsmith()


def trace_pipeline(func: Callable) -> Callable:
    """
    Decorator to trace pipeline execution in LangSmith.
    Falls back gracefully if LangSmith is unavailable.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not settings.langsmith_api_key:
            return await func(*args, **kwargs)

        try:
            from langsmith import traceable
            traced_func = traceable(
                name="taxai_pipeline",
                run_type="chain",
                tags=["taxai", "direct-tax", "ita-2025"],
            )(func)
            return await traced_func(*args, **kwargs)
        except ImportError:
            logger.warning("langsmith not installed — running without tracing")
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"LangSmith trace failed ({e}) — running without tracing")
            return await func(*args, **kwargs)

    return wrapper
