"""DB에 이미 반영된 공시를 백필 수집에서 제외하는지 검증한다."""
from pathlib import Path

from src.infrastructure.dart_api import DartApiClient


def test_collection_skips_database_existing_rcept_nos_before_xml_download(tmp_path, monkeypatch):
    client = DartApiClient(api_key="test-key", save_directory=str(tmp_path))
    reports = [
        {"rcept_no": "20260101000001", "corp_name": "기존", "corp_cls": "Y", "report_nm": "유상증자결정"},
        {"rcept_no": "20260101000002", "corp_name": "신규", "corp_cls": "Y", "report_nm": "유상증자결정"},
    ]
    monkeypatch.setattr(client, "fetch_disclosure_list", lambda *args, **kwargs: {
        "status": "000", "list": reports, "total_page": 1,
    })
    downloaded = []

    def download(rcept_no, corp_name):
        downloaded.append(rcept_no)
        return Path(tmp_path / f"{rcept_no}.xml")

    monkeypatch.setattr(client, "download_document_xml", download)

    result = client.collect_capital_increase_reports(
        "20260101", "20260101", existing_rcept_nos=lambda rcept_nos: {"20260101000001"}
    )

    assert [report["rcept_no"] for report in result] == ["20260101000002"]
    assert downloaded == ["20260101000002"]
