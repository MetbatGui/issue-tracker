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

    @property
    def all_succeeded(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def failed_steps(self) -> List[StepResult]:
        return [s for s in self.steps if not s.success]

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

    def run(self, days: int) -> DailyOrchestrationResult:
        """모든 스텝의 daily_update(days)를 순차 실행합니다.

        스텝 하나가 예외를 던져도 나머지 스텝은 계속 실행됩니다.
        """
        return self._run_updates(lambda service: service.daily_update(days))

    def run_full(self, start_date: str) -> DailyOrchestrationResult:
        """모든 스텝의 full_update(start_date)를 순차 실행합니다."""
        return self._run_updates(lambda service: service.full_update(start_date))

    def _run_updates(self, update_service: Callable[[BaseReportService], LocalUpdateResult]) -> DailyOrchestrationResult:
        """수집·DB 반영 후 export와 원격 동기화까지 한 실행 흐름으로 처리한다."""
        results: List[StepResult] = []
        total = len(self.steps)

        for i, step in enumerate(self.steps, 1):
            logger.info(f">>> [{i}/{total}] {step.name} 업데이트 시작")
            try:
                service = step.factory()
                local_update = update_service(service)
                if local_update is None:
                    local_update = LocalUpdateResult.empty()
                results.append(StepResult(step.name, success=True, local_update=local_update))
            except Exception as e:
                logger.error(f"[{step.name}] 실패: {e}", exc_info=True)
                results.append(StepResult(step.name, success=False, error=str(e)))

        result = DailyOrchestrationResult(results)
        targets = result.sync_targets

        self.finalize_sync_targets(targets)

        return result

    @staticmethod
    def finalize_sync_targets(targets: List[SyncTarget]) -> None:
        """산출물을 생성한 뒤 Excel→DB 순서로 원격 동기화한다."""
        for target in targets:
            target.export_excel()
        for target in targets:
            target.upload_excel()
        for target in targets:
            target.upload_database()


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
