import logging
import sys

from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(settings.log_level)

    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    logHandler.setFormatter(formatter)

    # Remove default handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(logHandler)
    return logger


logger = setup_logging()
