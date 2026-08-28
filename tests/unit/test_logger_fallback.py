"""파일 로그 저장소를 쓸 수 없어도 수집 작업은 계속되어야 한다."""
import logging

from src import logger as logger_module


def test_setup_logger_keeps_console_logging_when_file_handler_fails(monkeypatch):
    logger_name = "test.file-log-fallback"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()

    def raise_permission_error(*args, **kwargs):
        raise PermissionError("read-only log directory")

    monkeypatch.setattr(logger_module, "TimedRotatingFileHandler", raise_permission_error)

    configured_logger = logger_module.setup_logger(logger_name)

    try:
        assert configured_logger is logger
        assert any(
            isinstance(handler, logging.StreamHandler) and handler.level == logging.INFO
            for handler in logger.handlers
        )
    finally:
        logger.handlers.clear()
