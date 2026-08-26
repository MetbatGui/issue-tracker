"""StoragePort 실패 계약을 Google Drive 어댑터에서 검증한다."""
import logging
from pathlib import Path

import src.infrastructure.google_drive_adapter as drive_module
from src.infrastructure.google_drive_adapter import GoogleDriveAdapter


class _UnavailableFiles:
    def list(self, **kwargs):
        raise OSError("Drive unavailable")


class _UnavailableService:
    def files(self):
        return _UnavailableFiles()


def test_upload_file_returns_none_when_local_source_is_missing(tmp_path):
    adapter = object.__new__(GoogleDriveAdapter)
    adapter.logger = logging.getLogger("test-google-drive")

    result = adapter.upload_file(tmp_path / "missing.xlsx", "folder-id")

    assert result is None


def test_upload_file_returns_none_when_drive_call_fails(tmp_path):
    adapter = object.__new__(GoogleDriveAdapter)
    adapter.logger = logging.getLogger("test-google-drive")
    adapter.service = _UnavailableService()
    file_path = tmp_path / "report.xlsx"
    file_path.write_bytes(b"test")

    result = adapter.upload_file(file_path, "folder-id")

    assert result is None


def test_get_file_downloads_the_remote_db_to_an_isolated_working_copy(tmp_path, monkeypatch):
    adapter = object.__new__(GoogleDriveAdapter)
    adapter.logger = logging.getLogger("test-google-drive")
    adapter.database_folder_id = "folder-id"
    adapter.service = _DownloadService()
    monkeypatch.setattr(adapter, "_find_file_by_name", lambda folder_id, file_name: "remote-db-id")
    monkeypatch.setattr(drive_module, "MediaIoBaseDownload", _FakeDownloader)

    working_path = adapter.get_file(Path("data/유상증자/유상증자.db"))

    assert working_path is not None
    assert working_path.read_bytes() == b"remote-db"
    assert working_path.name != "유상증자.db"


def test_put_file_updates_the_configured_drive_db_folder(tmp_path, monkeypatch):
    adapter = object.__new__(GoogleDriveAdapter)
    adapter.logger = logging.getLogger("test-google-drive")
    adapter.database_folder_id = "folder-id"
    local_db = tmp_path / "working.db"
    local_db.write_bytes(b"changed")
    uploaded = []
    monkeypatch.setattr(
        adapter,
        "upload_file",
        lambda file_path, folder_id, file_name=None: uploaded.append((file_path, folder_id, file_name)) or "remote-id",
    )

    assert adapter.put_file(local_db, Path("data/유상증자/유상증자.db"))
    assert uploaded == [(local_db, "folder-id", "유상증자.db")]


class _DownloadFiles:
    def get_media(self, fileId):
        assert fileId == "remote-db-id"
        return object()


class _DownloadService:
    def files(self):
        return _DownloadFiles()


class _FakeDownloader:
    def __init__(self, output, request):
        self.output = output

    def next_chunk(self):
        self.output.write(b"remote-db")
        return None, True
