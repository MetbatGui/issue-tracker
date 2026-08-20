"""무상증자 Excel -> SQLite 1회성 마이그레이션 스크립트

기존 data/무상증자/무상증자.xlsx(연도별 시트)를 읽어 BonusSharesSqliteRepository로 백필합니다.

컷오버 전 필수 검증: 마이그레이션 후 Excel의 고유 접수번호 수와 DB row 수가 정확히 일치해야 함
(불일치 시 DB 기준 rebuild가 과거 데이터를 조용히 지울 위험 - db_drive_docker_migration_guide.md 1절 참고).
"""
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain import BonusSharesDecision
from src.domain.value_objects import StockInfo
from src.infrastructure.bonus_shares_sqlite_repository import BonusSharesSqliteRepository


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


def _cell_to_common_shares(value) -> int:
    """"신주의 종류와 수" 컬럼(예: "1,234" 또는 "0")을 보통주 수량으로 파싱합니다.

    Excel에는 보통주 수량만 문자열로 저장되어 있고 우선주는 애초에 컬럼이 없어
    과거 데이터의 우선주 수량은 복구 불가(0으로 마이그레이션).
    """
    text = _cell_to_str(value)
    if not text:
        return 0
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return 0


def _row_to_decision(row: pd.Series) -> Optional[BonusSharesDecision]:
    rcept_no = _cell_to_str(row.get("접수번호"))
    if not rcept_no:
        return None

    company_name = _cell_to_str(row.get("종목명")) or ""

    return BonusSharesDecision(
        # 원본 XML 파일명은 Excel에 없음 - rcept_no 기반 재구성 값(dedup 등 로직은 rcept_no 기준이라 무영향)
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=_cell_to_common_shares(row.get("신주의 종류와 수")), preferred=0),
        par_value=_cell_to_int(row.get("1주당 액면가액")),
        total_shares_before=_cell_to_int(row.get("증자전 발행주식총수")),
        assign_per_share=_cell_to_float(row.get("1주당 신주배정 주식수")) or 0.0,
        board_resolution_date=_cell_to_date(row.get("이사회결의일")),
        disclosure_date=_cell_to_date(row.get("일자")),
        record_date=_cell_to_date(row.get("신주배정기준일")),
        listing_date=_cell_to_date(row.get("신주의 상장 예정일")),
        # 보고서명은 Excel에 저장된 적이 없어 과거 데이터는 복구 불가
        report_name=None,
        is_correction=_cell_to_str(row.get("기재정정여부")) == "[기재정정]",
        rcept_no=rcept_no,
        parent_rcp_no=_cell_to_str(row.get("상위접수번호")),
        original_disclosure_date=_cell_to_date(row.get("최초공시일")),
    )


def migrate(excel_path: str, db_path: str) -> dict:
    """Excel 데이터를 SQLite로 마이그레이션합니다.

    Returns:
        {"excel_rows": 고유 접수번호 수, "db_rows": 마이그레이션 후 DB row 수, "match": 일치 여부}
    """
    repo = BonusSharesSqliteRepository(db_path)

    excel_file = pd.ExcelFile(excel_path)
    decisions = []

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=1)
        if "접수번호" not in df.columns:
            continue
        for _, row in df.iterrows():
            decision = _row_to_decision(row)
            if decision is not None:
                decisions.append(decision)

    unique_rcept_nos = {d.rcept_no for d in decisions}
    repo.upsert(decisions)

    db_row_count = repo._conn.execute("SELECT COUNT(*) FROM bonus_shares_decisions").fetchone()[0]

    return {
        "excel_rows": len(unique_rcept_nos),
        "db_rows": db_row_count,
        "match": len(unique_rcept_nos) == db_row_count,
    }


if __name__ == "__main__":
    result = migrate("data/무상증자/무상증자.xlsx", "data/무상증자/무상증자.db")
    print(f"Excel 고유 접수번호: {result['excel_rows']}건")
    print(f"DB row 수: {result['db_rows']}건")
    if result["match"]:
        print("✅ row count parity 일치 - 컷오버 가능")
    else:
        print("❌ row count parity 불일치 - 컷오버 중단, 원인 조사 필요")
        sys.exit(1)
