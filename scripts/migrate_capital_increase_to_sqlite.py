"""유상증자 Excel -> SQLite 1회성 마이그레이션 스크립트

기존 data/유상증자/유상증자.xlsx(연도별 시트)를 읽어 CapitalIncreaseSqliteRepository로 백필합니다.
"발행확정가액"/"신주상장일"처럼 도메인 모델에 없는 수동입력 전용 컬럼은 원본 Excel 값을 그대로
DB에 옮겨 보존합니다.

컷오버 전 필수 검증: 마이그레이션 후 Excel의 고유 접수번호 수와 DB row 수가 정확히 일치해야 함
(불일치 시 DB 기준 rebuild가 과거 데이터를 조용히 지울 위험 - db_drive_docker_migration_guide.md 1절 참고).
"""
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain import CapitalIncreaseDecision
from src.domain.value_objects import StockInfo, FundingPurpose
from src.infrastructure.capital_increase_sqlite_repository import CapitalIncreaseSqliteRepository


def _cell_to_str(value) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _cell_to_int(value) -> Optional[int]:
    if pd.isna(value) or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _cell_to_float(value) -> Optional[float]:
    if pd.isna(value) or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cell_to_date(value) -> Optional[date]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date() if isinstance(value, datetime) else value.to_pydatetime().date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _row_to_decision(row: pd.Series) -> Optional[CapitalIncreaseDecision]:
    rcept_no = _cell_to_str(row.get("접수번호"))
    if not rcept_no:
        return None

    company_name = _cell_to_str(row.get("종목명")) or ""

    return CapitalIncreaseDecision(
        # 원본 XML 파일명은 Excel에 없음 - rcept_no 기반 재구성 값(정보용, dedup 등 로직은 rcept_no 기준이라 무영향)
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        # Excel에는 신주발행주식수(보통주)만 있고 우선주 컬럼이 없어 과거 데이터는 복구 불가(0으로 마이그레이션)
        new_shares=StockInfo(common=_cell_to_int(row.get("신주발행주식수")) or 0, preferred=0),
        par_value=_cell_to_int(row.get("1주당 액면가")),
        total_shares_before=_cell_to_int(row.get("증자전 발행주식총수")),
        issue_price=_cell_to_int(row.get("신주의 발행가액")),
        # debt_repayment/business_acquisition은 유상증자 파서가 애초에 파싱하지 않아 Excel에도 없음
        funding=FundingPurpose(
            facility=_cell_to_int(row.get("시설자금")) or 0,
            operating=_cell_to_int(row.get("운영자금")) or 0,
            acquisition=_cell_to_int(row.get("타법인증권")) or 0,
            other=_cell_to_int(row.get("기타자금")) or 0,
        ),
        method=_cell_to_str(row.get("증자방식")) or "",
        assign_per_share=_cell_to_float(row.get("1주당 신주배정주식수")) or 0.0,
        board_resolution_date=_cell_to_date(row.get("이사회결의일")),
        disclosure_date=_cell_to_date(row.get("일자")),
        record_date=_cell_to_date(row.get("신주배정기준일")),
        subscription_date=_cell_to_date(row.get("청약예정일")),
        payment_date=_cell_to_date(row.get("납입일")),
        # 보고서명은 Excel에 저장된 적이 없어 과거 데이터는 복구 불가
        report_name=None,
        is_correction=_cell_to_str(row.get("기재정정여부")) == "[기재정정]",
        rcept_no=rcept_no,
        parent_rcp_no=_cell_to_str(row.get("상위접수번호")),
        original_disclosure_date=_cell_to_date(row.get("최초공시일")),
    ), _cell_to_str(row.get("발행확정가액")), _cell_to_str(row.get("신주상장일"))


def migrate(excel_path: str, db_path: str) -> dict:
    """Excel 데이터를 SQLite로 마이그레이션합니다.

    Returns:
        {"excel_rows": 고유 접수번호 수, "db_rows": 마이그레이션 후 DB row 수, "match": 일치 여부}
    """
    repo = CapitalIncreaseSqliteRepository(db_path)

    excel_file = pd.ExcelFile(excel_path)
    decisions = []
    manual_fields = {}  # rcept_no -> (final_issue_price, listing_date)

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=1)
        if "접수번호" not in df.columns:
            continue
        for _, row in df.iterrows():
            result = _row_to_decision(row)
            if result is None:
                continue
            decision, final_issue_price, listing_date = result
            decisions.append(decision)
            if final_issue_price or listing_date:
                manual_fields[decision.rcept_no] = (final_issue_price, listing_date)

    unique_rcept_nos = {d.rcept_no for d in decisions}
    repo.upsert(decisions)

    for rcept_no, (final_issue_price, listing_date) in manual_fields.items():
        repo._conn.execute(
            "UPDATE capital_increase_decisions SET final_issue_price = ?, listing_date = ? WHERE rcept_no = ?",
            (final_issue_price, listing_date, rcept_no),
        )
    repo._conn.commit()

    db_row_count = repo._conn.execute("SELECT COUNT(*) FROM capital_increase_decisions").fetchone()[0]

    return {
        "excel_rows": len(unique_rcept_nos),
        "db_rows": db_row_count,
        "match": len(unique_rcept_nos) == db_row_count,
    }


if __name__ == "__main__":
    result = migrate("data/유상증자/유상증자.xlsx", "data/유상증자/유상증자.db")
    print(f"Excel 고유 접수번호: {result['excel_rows']}건")
    print(f"DB row 수: {result['db_rows']}건")
    if result["match"]:
        print("✅ row count parity 일치 - 컷오버 가능")
    else:
        print("❌ row count parity 불일치 - 컷오버 중단, 원인 조사 필요")
        sys.exit(1)
