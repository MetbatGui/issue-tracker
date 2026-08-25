"""SQLite SSOT 작업 사본 세션을 검증한다."""
from pathlib import Path

from src.infrastructure import LocalFileStorageAdapter, SqliteStorageSession


def test_session_uses_working_copy_and_atomically_persists_it(tmp_path):
    storage_path = tmp_path / "ssot.db"
    storage_path.write_bytes(b"before")
    session = SqliteStorageSession(LocalFileStorageAdapter(), storage_path)

    assert session.working_path != storage_path
    assert session.working_path.read_bytes() == b"before"

    session.working_path.write_bytes(b"after")

    assert session.persist()
    assert storage_path.read_bytes() == b"after"
