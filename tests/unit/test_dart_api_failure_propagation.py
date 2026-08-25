"""DART 수집 실패가 정상적인 빈 결과로 숨겨지지 않는지 검증한다."""
import pytest

from src.infrastructure.dart_api import DartApiClient


def test_collection_raises_when_disclosure_list_request_fails(tmp_path, monkeypatch):
    client = DartApiClient(api_key="test-key", save_directory=str(tmp_path))
    monkeypatch.setattr(client, "fetch_disclosure_list", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="DART 목록 조회 실패"):
        client.collect_capital_increase_reports("20260101", "20260101")
