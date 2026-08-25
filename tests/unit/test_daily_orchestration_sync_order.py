"""일일 오케스트레이션의 로컬 처리·내보내기·동기화 순서를 검증한다."""
from pathlib import Path
from datetime import datetime

from src.application.daily_orchestration_service import (
    DailyOrchestrationService,
    LocalUpdateResult,
    OrchestrationStep,
    SyncTarget,
)


class _FakeService:
    def __init__(self, name, events, changed=True):
        self.name = name
        self.events = events
        self.changed = changed

    def daily_update(self, days):
        self.events.append(f"collect:{self.name}")
        if not self.changed:
            return LocalUpdateResult.empty()

        return LocalUpdateResult(
            targets=[
                SyncTarget(
                    database_path=Path(f"{self.name}.db"),
                    excel_path=Path(f"{self.name}.xlsx"),
                    export_excel=lambda: self.events.append(f"export:{self.name}"),
                    upload_excel=lambda: self.events.append(f"upload-excel:{self.name}"),
                    upload_database=lambda: self.events.append(f"upload-db:{self.name}"),
                )
            ]
        )


def test_orchestrator_collects_before_exporting_and_uploads_excel_before_db():
    events = []
    orchestrator = DailyOrchestrationService([
        OrchestrationStep("A", lambda: _FakeService("A", events)),
        OrchestrationStep("B", lambda: _FakeService("B", events)),
    ])

    result = orchestrator.run(days=7)

    assert result.all_succeeded
    assert events == [
        "collect:A",
        "collect:B",
        "export:A",
        "export:B",
        "upload-excel:A",
        "upload-excel:B",
        "upload-db:A",
        "upload-db:B",
    ]


def test_orchestrator_ignores_unchanged_services_for_export_and_upload():
    events = []
    orchestrator = DailyOrchestrationService([
        OrchestrationStep("changed", lambda: _FakeService("changed", events)),
        OrchestrationStep("unchanged", lambda: _FakeService("unchanged", events, changed=False)),
    ])

    orchestrator.run(days=7)

    assert events == [
        "collect:changed",
        "collect:unchanged",
        "export:changed",
        "upload-excel:changed",
        "upload-db:changed",
    ]


def test_orchestrator_runs_full_update_before_exporting_and_uploading():
    events = []

    class _FullService(_FakeService):
        def full_update(self, start_date):
            self.events.append(f"full:{self.name}:{start_date}")
            return LocalUpdateResult(
                targets=[
                    SyncTarget(
                        database_path=Path(f"{self.name}.db"),
                        excel_path=Path(f"{self.name}.xlsx"),
                        export_excel=lambda: self.events.append(f"export:{self.name}"),
                        upload_excel=lambda: self.events.append(f"upload-excel:{self.name}"),
                        upload_database=lambda: self.events.append(f"upload-db:{self.name}"),
                    )
                ]
            )

    orchestrator = DailyOrchestrationService([
        OrchestrationStep("A", lambda: _FullService("A", events)),
    ])

    result = orchestrator.run_full("20200101")

    assert result.all_succeeded
    assert events == [
        "full:A:20200101",
        "export:A",
        "upload-excel:A",
        "upload-db:A",
    ]


def test_orchestrator_runs_db_based_export_through_sync_flow():
    events = []

    class _ExportService:
        def export_update(self):
            events.append("select-db")
            return LocalUpdateResult([
                SyncTarget(
                    database_path=Path("A.db"),
                    excel_path=Path("A.xlsx"),
                    export_excel=lambda: events.append("export:A"),
                    upload_excel=lambda: events.append("upload-excel:A"),
                    upload_database=lambda: events.append("upload-db:A"),
                )
            ])

    result = DailyOrchestrationService([
        OrchestrationStep("A", _ExportService),
    ]).run_export()

    assert result.all_succeeded
    assert events == ["select-db", "export:A", "upload-excel:A", "upload-db:A"]


def test_orchestrator_passes_injected_clock_to_daily_service():
    received = []

    class _ClockAwareService:
        def daily_update(self, days, today=None):
            received.append((days, today))
            return LocalUpdateResult.empty()

    today = datetime(2025, 1, 1, 9, 0, 0)
    DailyOrchestrationService([
        OrchestrationStep("A", _ClockAwareService),
    ]).run(days=3, today=today)

    assert received == [(3, today)]


def test_orchestrator_returns_upload_failure_in_result_without_skipping_db_upload():
    events = []

    def fail_excel_upload():
        events.append("upload-excel:A")
        raise OSError("Drive unavailable")

    target = SyncTarget(
        database_path=Path("A.db"),
        excel_path=Path("A.xlsx"),
        export_excel=lambda: events.append("export:A"),
        upload_excel=fail_excel_upload,
        upload_database=lambda: events.append("upload-db:A"),
    )

    class _Service:
        def daily_update(self, days):
            return LocalUpdateResult([target])

    result = DailyOrchestrationService([
        OrchestrationStep("A", _Service),
    ]).run(days=1)

    assert not result.all_succeeded
    assert len(result.failed_sync_results) == 1
    assert result.failed_sync_results[0].excel_upload_error == "Drive unavailable"
    assert events == ["export:A", "upload-excel:A", "upload-db:A"]
