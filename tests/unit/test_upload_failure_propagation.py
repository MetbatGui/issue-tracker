"""원격 동기화 실패가 실행 성공으로 숨겨지지 않는지 검증한다."""
import logging

import pytest

from src.application.base_report_service import BaseReportService


class _ServiceForUploadTest(BaseReportService):
    def parse_and_export_to_excel(self, relation_map=None) -> int:
        return 0


class _FailingDrive:
    def upload_file(self, *args, **kwargs):
        raise OSError("Drive unavailable")


def test_upload_failure_is_propagated_to_the_orchestrator(tmp_path):
    service = object.__new__(_ServiceForUploadTest)
    service.google_drive = _FailingDrive()
    service.google_drive_folder_id = "folder-id"
    service.excel_path = tmp_path / "report.xlsx"
    service.excel_path.write_bytes(b"test")
    service.logger = logging.getLogger("test-upload")

    with pytest.raises(OSError, match="Drive unavailable"):
        service._upload_to_google_drive()
