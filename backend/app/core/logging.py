import sys
from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru to output structured logs to stdout."""

    logger.remove()
    logger.add(
        sys.stdout,
        level=level.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        backtrace=False,
        diagnose=False,
    )
