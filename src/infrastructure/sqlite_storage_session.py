"""StoragePort 위에서 SQLite 작업 사본을 관리한다."""
import os
import tempfile
from pathlib import Path

from ..domain.ports import StoragePort


class SqliteStorageSession:
    """get_file → SQLite 작업 → put_file로 SSOT 파일을 갱신하는 세션."""

    def __init__(self, storage: StoragePort, storage_path: Path):
        self.storage = storage
        self.storage_path = storage_path
        self.working_path = self._prepare_working_path()

    def _prepare_working_path(self) -> Path:
        downloaded_path = self.storage.get_file(self.storage_path)
        if downloaded_path is not None:
            return downloaded_path
        fd, temporary_name = tempfile.mkstemp(suffix=self.storage_path.suffix)
        os.close(fd)
        return Path(temporary_name)

    def persist(self) -> bool:
        return self.storage.put_file(self.working_path, self.storage_path)
