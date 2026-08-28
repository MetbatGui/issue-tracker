"""StoragePort 위에서 SQLite 작업 사본을 관리한다."""
import os
import tempfile
from pathlib import Path

from ..domain.ports import StoragePort


class SqliteStorageSession:
    """get_file → SQLite 작업 → put_file로 SSOT 파일을 갱신하는 세션."""

    _shared_sessions = {}

    def __init__(self, storage: StoragePort, storage_path: Path):
        self.storage = storage
        self.storage_path = storage_path
        self.working_path = self._prepare_working_path()

    @classmethod
    def get_shared(cls, storage: StoragePort, storage_path: Path) -> "SqliteStorageSession":
        """같은 원격 DB를 쓰는 서비스가 하나의 작업 사본을 공유하게 한다."""
        storage_identity = getattr(storage, "database_folder_id", None) or id(storage)
        key = (type(storage), storage_identity, str(storage_path))
        session = cls._shared_sessions.get(key)
        if session is None:
            session = cls(storage, storage_path)
            session._shared_key = key
            cls._shared_sessions[key] = session
        return session

    def _prepare_working_path(self) -> Path:
        downloaded_path = self.storage.get_file(self.storage_path)
        if downloaded_path is not None:
            return downloaded_path
        storage_error = getattr(self.storage, "last_error", None)
        if storage_error is not None:
            raise RuntimeError(f"원격 DB 작업 사본을 만들지 못했습니다: {storage_error}")
        if self.storage_path.exists():
            raise RuntimeError(f"SQLite 작업 사본을 만들지 못했습니다: {self.storage_path}")
        fd, temporary_name = tempfile.mkstemp(suffix=self.storage_path.suffix)
        os.close(fd)
        return Path(temporary_name)

    def persist(self) -> bool:
        return self.storage.put_file(self.working_path, self.storage_path)

    def close(self) -> None:
        """작업이 끝난 뒤 임시 SQLite 작업 사본을 제거한다."""
        self.working_path.unlink(missing_ok=True)
        shared_key = getattr(self, "_shared_key", None)
        if shared_key is not None:
            self._shared_sessions.pop(shared_key, None)
