"""DB에 이미 반영된 공시를 백필 수집에서 제외하는지 검증한다."""
import io
import zipfile

from src.infrastructure.dart_api import DartApiClient, DownloadedXml


def test_document_download_returns_xml_bytes_without_creating_a_file(tmp_path, monkeypatch):
    xml = b"<?xml version='1.0' encoding='utf-8'?><ROOT/>"
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("document.xml", xml)

    class Response:
        content = zipped.getvalue()
        headers = {}

        def raise_for_status(self):
            pass

    client = DartApiClient(api_key="test-key", save_directory=str(tmp_path))
    monkeypatch.setattr("src.infrastructure.dart_api.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("src.infrastructure.dart_api.time.sleep", lambda _: None)

    document = client.download_document_xml("20260101000001", "테스트/회사")

    assert document == DownloadedXml("20260101000001", "테스트회사_20260101000001.xml", xml)
    assert list(tmp_path.rglob("*.xml")) == []


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
        return DownloadedXml(rcept_no, f"{rcept_no}.xml", b"<ROOT/>")

    monkeypatch.setattr(client, "download_document_xml", download)

    result = client.collect_capital_increase_reports(
        "20260101", "20260101", existing_rcept_nos=lambda rcept_nos: {"20260101000001"}
    )

    assert [report["rcept_no"] for report in result] == ["20260101000002"]
    assert downloaded == ["20260101000002"]
