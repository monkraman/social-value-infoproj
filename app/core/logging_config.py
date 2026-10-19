import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar
from typing import Optional

# Request ID context for tracking logs across asynchronous tasks
current_request_id: ContextVar[str] = ContextVar("current_request_id", default="system")


class RequestIdFilter(logging.Filter):
    """Injects current_request_id into log records."""
    def filter(self, record):
        record.request_id = current_request_id.get("system")
        return True


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """
    Initializes Enterprise Logging with:
    - Console output with Request-ID and module tags.
    - Rotating file sink: logs/app.log (10 MB per file, max 10 backups).
    - Dedicated error sink: logs/errors.log (only WARNING, ERROR, CRITICAL).
    """
    os.makedirs(log_dir, exist_ok=True)

    app_logger = logging.getLogger("social_value")
    app_logger.setLevel(log_level)

    # Avoid duplicate handlers on reload
    if app_logger.handlers:
        return app_logger

    log_format = (
        "[%(asctime)s] [%(levelname)s] [ReqID:%(request_id)s] "
        "[%(name)s:%(funcName)s:%(lineno)d]: %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    req_filter = RequestIdFilter()

    # 1. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(req_filter)
    app_logger.addHandler(console_handler)

    # 2. General Application Log File (Rotating: 10MB x 10 files)
    app_log_path = os.path.join(log_dir, "app.log")
    file_handler = RotatingFileHandler(
        app_log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(req_filter)
    app_logger.addHandler(file_handler)

    # 3. Dedicated Error Log File (WARNING, ERROR, CRITICAL only)
    error_log_path = os.path.join(log_dir, "errors.log")
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(req_filter)
    app_logger.addHandler(error_handler)

    return app_logger


# Singleton logger instance
logger = setup_logging()
