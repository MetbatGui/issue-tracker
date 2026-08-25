"""서비스가 원격 동기화 없이 로컬 변경 결과만 반환하는지 검증한다."""
from pathlib import Path

from src.application.capital_increase_services import CapitalIncreaseService
from src.application.base_report_service import BaseReportService
from src.application.daily_orchestration_service import LocalUpdateResult


class _PendingFileService(BaseReportService):
    def parse_and_export_to_excel(self, relation_map=None) -> int:
        return 0


def test_daily_update_returns_local_sync_target_without_exporting_or_uploading(tmp_path, monkeypatch):
    service = CapitalIncreaseService(
        data_directory=str(tmp_path / "capital"),
        api_key="test-key",
        enable_google_drive=False,
    )
    monkeypatch.setattr(service, "download_reports_with_history", lambda *args, **kwargs: (["report.xml"], {}))
    monkeypatch.setattr(service, "_convert_downloaded_files", lambda *args, **kwargs: None)

    parsed = []
    monkeypatch.setattr(
        service,
        "parse_and_export_to_excel",
        lambda relation_map=None, export=True: parsed.append(export) or 1,
    )

    result = service.daily_update(days_back=1)

    assert isinstance(result, LocalUpdateResult)
    assert parsed == [False]
    assert len(result.targets) == 1
    assert result.targets[0].excel_path == service.excel_path
    assert result.targets[0].database_path == service.database_session.storage_path


def test_daily_update_requests_excel_rebuild_when_db_has_data_but_output_is_missing(tmp_path, monkeypatch):
    service = CapitalIncreaseService(
        data_directory=str(tmp_path / "capital"),
        api_key="test-key",
        enable_google_drive=False,
    )
    monkeypatch.setattr(service, "download_reports_with_history", lambda *args, **kwargs: ([], {}))
    monkeypatch.setattr(service.repository, "get_all", lambda: [object()])
    monkeypatch.setattr(
        service,
        "parse_and_export_to_excel",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("재파싱하면 안 됩니다")),
    )

    result = service.daily_update(days_back=1)

    assert len(result.targets) == 1
    assert not service.excel_path.exists()


def test_pending_xml_files_excludes_receipt_numbers_already_in_db(tmp_path):
    service = object.__new__(_PendingFileService)
    service.xml_directory = tmp_path
    (tmp_path / "existing_20260101000001.xml").write_text("x", encoding="utf-8")
    (tmp_path / "pending_20260101000002.xml").write_text("x", encoding="utf-8")

    files = service._pending_xml_files(lambda rcept_nos: {"20260101000001"})

    assert files == [str(tmp_path / "pending_20260101000002.xml")]
