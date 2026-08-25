"""로컬 파일을 StoragePort 계약으로 제공한다."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from ..domain.ports import StoragePort
from ..logger import get_logger


class LocalFileStorageAdapter(StoragePort):
    """SQLite SSOT의 작업 사본을 만들고 원자적으로 교체하는 로컬 저장소 어댑터."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def get_file(self, storage_path: Path) -> Optional[Path]:
        try:
            if not storage_path.exists():
                return None
            fd, temporary_name = tempfile.mkstemp(suffix=storage_path.suffix)
            os.close(fd)
            working_path = Path(temporary_name)
            shutil.copy2(storage_path, working_path)
            return working_path
        except OSError as error:
            self.logger.error("DB 작업 사본 생성 실패: %s", error)
            return None

    def put_file(self, local_path: Path, storage_path: Path) -> bool:
        try:
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(dir=storage_path.parent, suffix=".tmp")
            os.close(fd)
            temporary_path = Path(temporary_name)
            try:
                shutil.copy2(local_path, temporary_path)
                os.replace(temporary_path, storage_path)
            finally:
                temporary_path.unlink(missing_ok=True)
            return True
        except OSError as error:
            self.logger.error("DB 작업 사본 반영 실패: %s", error)
            return False

    def upload_file(self, file_path: Path, folder_id: str, file_name: Optional[str] = None) -> Optional[str]:
        return None

    def delete_file(self, file_id: str) -> bool:
        return False

    def list_files(self, folder_id: str):
        return []
