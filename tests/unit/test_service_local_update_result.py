"""서비스가 원격 동기화 없이 로컬 변경 결과만 반환하는지 검증한다."""
from src.application.capital_increase_services import CapitalIncreaseService
from src.application.daily_orchestration_service import LocalUpdateResult
from src.infrastructure.dart_api import DownloadedXml
import src.application.base_report_service as base_module


def test_daily_update_returns_local_sync_target_without_exporting_or_uploading(tmp_path, monkeypatch):
    service = CapitalIncreaseService(
        data_directory=str(tmp_path / "capital"),
        api_key="test-key",
        enable_google_drive=False,
    )
    document = DownloadedXml("20260101000001", "report_20260101000001.xml", b"<ROOT/>")
    monkeypatch.setattr(service, "download_reports_with_history", lambda *args, **kwargs: ([document], {}))

    parsed = []
    monkeypatch.setattr(
        service,
        "parse_and_export_to_excel",
        lambda documents, relation_map=None, export=True: parsed.append((documents, export)) or 1,
    )

    result = service.daily_update(days_back=1)

    assert isinstance(result, LocalUpdateResult)
    assert parsed == [([document], False)]
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


def test_service_initialization_does_not_create_an_xml_cache_directory(tmp_path):
    CapitalIncreaseService(
        data_directory=str(tmp_path / "capital"), api_key="test-key", enable_google_drive=False,
    )

    assert not (tmp_path / "capital" / "xml").exists()


def test_google_drive_enabled_service_uses_drive_as_its_database_storage(tmp_path, monkeypatch):
    created = []

    class FakeDriveStorage:
        def __init__(self, database_folder_id=None):
            created.append(database_folder_id)
            self.database_folder_id = database_folder_id

        def get_file(self, storage_path):
            return None

        def put_file(self, local_path, storage_path):
            return True

    monkeypatch.setenv("CAPITAL_INCREASE_GOOGLE_FOLDER_ID", "folder-id")
    monkeypatch.setattr(base_module, "GoogleDriveAdapter", FakeDriveStorage)

    service = CapitalIncreaseService(
        data_directory=str(tmp_path / "capital"), api_key="test-key", enable_google_drive=True,
    )

    assert created == ["folder-id"]
    assert service.source_storage is service.google_drive


def test_database_finalize_uses_storage_persist_once_without_a_second_drive_upload(tmp_path):
    service = object.__new__(CapitalIncreaseService)
    persisted = []

    class Session:
        def persist(self):
            persisted.append(True)
            return True

    service.database_session = Session()
    service._upload_file_to_google_drive = lambda _: (_ for _ in ()).throw(
        AssertionError("DB는 StoragePort.put_file로 한 번만 업로드해야 합니다")
    )

    service._persist_and_upload_database(tmp_path / "유상증자.db")

    assert persisted == [True]
