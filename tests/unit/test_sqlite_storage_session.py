"""SQLite SSOT 작업 사본 세션을 검증한다."""
from pathlib import Path

import pytest

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


def test_session_does_not_replace_existing_ssot_when_working_copy_cannot_be_created(tmp_path, monkeypatch):
    storage_path = tmp_path / "ssot.db"
    storage_path.write_bytes(b"original")
    storage = LocalFileStorageAdapter()
    monkeypatch.setattr(storage, "get_file", lambda _: None)

    with pytest.raises(RuntimeError, match="작업 사본"):
        SqliteStorageSession(storage, storage_path)

    assert storage_path.read_bytes() == b"original"


def test_session_close_removes_temporary_working_copy(tmp_path):
    storage_path = tmp_path / "ssot.db"
    storage_path.write_bytes(b"before")
    session = SqliteStorageSession(LocalFileStorageAdapter(), storage_path)

    session.close()

    assert not session.working_path.exists()
