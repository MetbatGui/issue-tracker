import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime

def setup_logger(name: str = None) -> logging.Logger:
    """로거 설정 및 반환
    
    Root Logger를 설정하여 프로젝트 전체에 적용합니다.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 이미 핸들러가 설정되어 있다면 중복 추가 방지
    if logger.handlers:
        return logger

    # 포맷 설정
    console_format = logging.Formatter('[%(levelname)s] %(message)s')
    file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    # 1. Console Handler (INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # 2. File Handler (DEBUG)
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        filename = f"issue_tracker_{datetime.now().strftime('%Y%m%d')}.log"
        file_path = log_dir / filename

        # 매일 자정에 로그 파일 회전, 최대 30일 보관
        file_handler = TimedRotatingFileHandler(
            file_path, when="midnight", interval=1, backupCount=30, encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except OSError as error:
        # Docker bind mount 등의 권한 문제에서도 콘솔 로그와 작업 실행은 유지한다.
        logger.warning("파일 로그를 초기화하지 못했습니다: %s", error)

    return logger

def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 가져오기 (루트 로거 설정을 상속받음)"""
    return logging.getLogger(name)
