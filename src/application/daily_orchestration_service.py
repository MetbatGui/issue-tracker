"""일일 수집 오케스트레이션 서비스

여러 보고서 유형(유상증자/무상증자/유무상증자/전환사채/신주인수권부사채) 서비스의
daily_update()를 순차 실행하되, 한 스텝의 실패가 나머지 스텝을 막지 않도록 격리합니다.
"""
from dataclasses import dataclass, field
from typing import Callable, List

from .base_report_service import BaseReportService
from ..logger import get_logger

logger = get_logger("DailyOrchestrationService")


__all__ = ["OrchestrationStep", "StepResult", "DailyOrchestrationResult", "DailyOrchestrationService"]


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


class DailyOrchestrationService:
    """등록된 스텝들을 순차 실행하고, 스텝별 성공/실패를 격리하여 기록합니다."""

    def __init__(self, steps: List[OrchestrationStep]):
        self.steps = steps

    def run(self, days: int) -> DailyOrchestrationResult:
        """모든 스텝의 daily_update(days)를 순차 실행합니다.

        스텝 하나가 예외를 던져도 나머지 스텝은 계속 실행됩니다.
        """
        results: List[StepResult] = []
        total = len(self.steps)

        for i, step in enumerate(self.steps, 1):
            logger.info(f">>> [{i}/{total}] {step.name} 업데이트 시작")
            try:
                service = step.factory()
                service.daily_update(days)
                results.append(StepResult(step.name, success=True))
            except Exception as e:
                logger.error(f"[{step.name}] 실패: {e}", exc_info=True)
                results.append(StepResult(step.name, success=False, error=str(e)))

        return DailyOrchestrationResult(results)


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
    print("OK: daily_orchestration_service self-check passed")


if __name__ == "__main__":
    _demo()
