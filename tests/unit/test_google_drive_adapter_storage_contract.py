"""StoragePort 실패 계약을 Google Drive 어댑터에서 검증한다."""
import logging
from pathlib import Path

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
