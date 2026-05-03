import logging
import sys
from config import settings


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("backend")
    if logger.handlers:
        return logger
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logger()
