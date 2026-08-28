"""일일 수집 오케스트레이션 서비스

여러 보고서 유형(유상증자/무상증자/유무상증자/전환사채/신주인수권부사채) 서비스의
daily_update()를 순차 실행하되, 한 스텝의 실패가 나머지 스텝을 막지 않도록 격리합니다.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List

from .base_report_service import BaseReportService
from ..logger import get_logger

logger = get_logger("DailyOrchestrationService")


__all__ = [
    "SyncTarget",
    "LocalUpdateResult",
    "SyncResult",
    "OrchestrationStep",
    "StepResult",
    "DailyOrchestrationResult",
    "DailyOrchestrationService",
]


@dataclass(frozen=True)
class SyncTarget:
    """한 DB SSOT와 여기서 생성되는 Excel 산출물의 동기화 단위."""

    database_path: Path
    excel_path: Path
    export_excel: Callable[[], int | None]
    upload_excel: Callable[[], None]
    upload_database: Callable[[], None]


@dataclass
class LocalUpdateResult:
    """서비스의 로컬 수집·DB 반영 결과.

    외부 업로드는 수행하지 않고, 오케스트레이터가 사용할 동기화 대상만 반환한다.
    """

    targets: List[SyncTarget] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "LocalUpdateResult":
        return cls()


@dataclass
class SyncResult:
    """동기화 대상 하나의 export·원격 업로드 실행 결과."""

    target: SyncTarget
    export_error: str = ""
    excel_upload_error: str = ""
    database_upload_error: str = ""

    @property
    def success(self) -> bool:
        return not (self.export_error or self.excel_upload_error or self.database_upload_error)


@dataclass
class OrchestrationStep:
    """오케스트레이션 대상 스텝 하나.

    factory는 run() 시점에만 호출됩니다 — 구글 드라이브 인증 등 비용이 드는
    초기화를 실제로 그 스텝을 실행할 때까지 미루기 위함입니다.
    """
    name: str
    factory: Callable[[], BaseReportService]


@dataclass
class StepResult:
    """스텝 하나의 실행 결과."""
    name: str
    success: bool
    error: str = ""
    local_update: LocalUpdateResult = field(default_factory=LocalUpdateResult.empty)


@dataclass
class DailyOrchestrationResult:
    """DailyOrchestrationService.run()의 전체 실행 결과."""
    steps: List[StepResult] = field(default_factory=list)
    sync_results: List[SyncResult] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return all(s.success for s in self.steps) and all(sync.success for sync in self.sync_results)

    @property
    def failed_steps(self) -> List[StepResult]:
        return [s for s in self.steps if not s.success]

    @property
    def failed_sync_results(self) -> List[SyncResult]:
        return [sync for sync in self.sync_results if not sync.success]

    @property
    def sync_targets(self) -> List[SyncTarget]:
        """성공한 스텝의 동기화 대상을 DB 경로 기준으로 중복 제거해 반환한다."""
        targets_by_database = {}
        for step in self.steps:
            if step.success:
                for target in step.local_update.targets:
                    targets_by_database[target.database_path] = target
        return list(targets_by_database.values())


class DailyOrchestrationService:
    """등록된 스텝들을 순차 실행하고, 스텝별 성공/실패를 격리하여 기록합니다."""

    def __init__(self, steps: List[OrchestrationStep]):
        self.steps = steps

    def run(self, days: int, today=None) -> DailyOrchestrationResult:
        """모든 스텝의 daily_update(days)를 순차 실행합니다.

        스텝 하나가 예외를 던져도 나머지 스텝은 계속 실행됩니다.
        """
        if today is None:
            return self._run_updates(lambda service: service.daily_update(days))
        return self._run_updates(lambda service: service.daily_update(days, today=today))

    def run_full(self, start_date: str) -> DailyOrchestrationResult:
        """모든 스텝의 full_update(start_date)를 순차 실행합니다."""
        return self._run_updates(lambda service: service.full_update(start_date))

    def run_export(self) -> DailyOrchestrationResult:
        """모든 스텝의 DB 기반 산출물 재생성·동기화를 실행합니다."""
        return self._run_updates(lambda service: service.export_update())

    def _run_updates(self, update_service: Callable[[BaseReportService], LocalUpdateResult]) -> DailyOrchestrationResult:
        """수집·DB 반영 후 export와 원격 동기화까지 한 실행 흐름으로 처리한다."""
        results: List[StepResult] = []
        services_to_close = []
        total = len(self.steps)

        for i, step in enumerate(self.steps, 1):
            logger.info(f">>> [{i}/{total}] {step.name} 업데이트 시작")
            try:
                service = step.factory()
                services_to_close.append(service)
                local_update = update_service(service)
                if local_update is None:
                    local_update = LocalUpdateResult.empty()
                results.append(StepResult(step.name, success=True, local_update=local_update))
            except Exception as e:
                logger.error(f"[{step.name}] 실패: {e}", exc_info=True)
                results.append(StepResult(step.name, success=False, error=str(e)))

        result = DailyOrchestrationResult(results)
        targets = result.sync_targets

        try:
            result.sync_results = self.finalize_sync_targets(targets)
        finally:
            for service in reversed(services_to_close):
                close = getattr(service, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception as error:
                        logger.error("서비스 리소스 정리 실패: %s", error, exc_info=True)

        return result

    @staticmethod
    def finalize_sync_targets(targets: List[SyncTarget]) -> List[SyncResult]:
        """산출물 생성 후 Excel→DB 동기화를 수행하고 각 결과를 반환한다."""
        results = [SyncResult(target) for target in targets]

        for result in results:
            try:
                result.target.export_excel()
            except Exception as error:
                result.export_error = str(error)
                logger.error("Excel export failed for %s: %s", result.target.excel_path, error)
        for result in results:
            if result.export_error:
                continue
            try:
                result.target.upload_excel()
            except Exception as error:
                result.excel_upload_error = str(error)
                logger.error("Excel upload failed for %s: %s", result.target.excel_path, error)
        for result in results:
            try:
                result.target.upload_database()
            except Exception as error:
                result.database_upload_error = str(error)
                logger.error("Database upload failed for %s: %s", result.target.database_path, error)

        return results


def _demo() -> None:
    """스텝 격리 동작 자가 점검: 중간 스텝이 예외를 던져도 나머지 스텝은 실행되어야 함."""
    calls = []

    class _FakeService:
        def __init__(self, tag):
            self.tag = tag

        def daily_update(self, days):
            calls.append(self.tag)
            if self.tag == "b":
                raise RuntimeError("boom")

    steps = [
        OrchestrationStep("A", lambda: _FakeService("a")),
        OrchestrationStep("B", lambda: _FakeService("b")),
        OrchestrationStep("C", lambda: _FakeService("c")),
    ]

    result = DailyOrchestrationService(steps).run(days=1)

    assert calls == ["a", "b", "c"], f"모든 스텝이 실행되어야 함: {calls}"
    assert [s.success for s in result.steps] == [True, False, True]
    assert result.all_succeeded is False
    assert [s.name for s in result.failed_steps] == ["B"]
    logger.info("daily_orchestration_service self-check passed")


if __name__ == "__main__":
    _demo()
