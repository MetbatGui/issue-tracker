"""파일 인코딩 변환 유틸리티

파일 인코딩을 감지하고 UTF-8로 변환합니다.
"""
from pathlib import Path
from typing import Optional, Tuple, List

from ..logger import get_logger


__all__ = ["FileEncodingConverter"]

logger = get_logger("FileEncodingConverter")


class FileEncodingConverter:
    """파일 인코딩 변환기
    
    여러 인코딩을 시도하여 파일을 읽고 UTF-8로 변환합니다.
    """

    ENCODINGS = ['utf-8', 'cp949', 'euc-kr', 'latin-1']

    @classmethod
    def detect_and_read(cls, file_path: Path) -> Optional[Tuple[str, str]]:
        """파일의 인코딩을 감지하고 내용을 읽습니다.
        
        Args:
            file_path: 읽을 파일 경로
            
        Returns:
            (인코딩, 파일내용) 튜플. 실패 시 None
        """
        for encoding in cls.ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    return encoding, content
            except (UnicodeDecodeError, LookupError):
                continue
        return None

    @classmethod
    def convert_to_utf8(cls, file_path: Path) -> bool:
        """파일을 UTF-8 인코딩으로 변환합니다.
        
        Args:
            file_path: 변환할 파일 경로
            
        Returns:
            변환 성공 여부
        """
        result = cls.detect_and_read(file_path)

        if result is None:
            logger.error(f"{file_path.name}: 인코딩을 감지할 수 없습니다")
            return False

        current_encoding, content = result

        if current_encoding.lower() == 'utf-8':
            logger.info(f"{file_path.name}: 이미 UTF-8")
            return True

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"{file_path.name}: {current_encoding} -> UTF-8 변환 완료")
            return True
        except Exception as e:
            logger.error(f"{file_path.name}: {e}")
            return False

    @classmethod
    def convert_directory(cls, directory: Path, pattern: str = "*.xml") -> dict:
        """디렉토리 내 파일들을 일괄 변환합니다.
        
        Args:
            directory: 대상 디렉토리
            pattern: 파일 패턴 (기본값: *.xml)
            
        Returns:
            변환 결과 통계 딕셔너리
        """
        if not directory.exists():
            logger.error(f"디렉토리를 찾을 수 없습니다: {directory}")
            return {"converted": 0, "already_utf8": 0, "errors": 0}

        files = list(directory.glob(pattern))
        logger.info(f"총 {len(files)}개의 파일을 처리합니다.")

        converted = 0
        already_utf8 = 0
        errors = 0

        for file_path in files:
            result = cls.detect_and_read(file_path)
            if result and result[0].lower() != 'utf-8':
                if cls.convert_to_utf8(file_path):
                    converted += 1
                else:
                    errors += 1
            elif result and result[0].lower() == 'utf-8':
                logger.info(f"{file_path.name}: 이미 UTF-8")
                already_utf8 += 1
            else:
                errors += 1

        logger.info(f"변환 완료: 변환됨 {converted}개, 이미 UTF-8 {already_utf8}개, 오류 {errors}개")

        return {"converted": converted, "already_utf8": already_utf8, "errors": errors}
