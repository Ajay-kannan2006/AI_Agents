import logging
import os
import sys
from config.settings import settings

def setup_logging():
    """Configures structured application logging to stdout and file."""
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    handlers = [console_handler]

    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("InterviewCoachAgent")
    logger.info(f"Logging initialized at level {settings.LOG_LEVEL}")
    return logger

logger = setup_logging()
