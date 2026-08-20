"""신주인수권부사채 Excel -> SQLite 1회성 마이그레이션 스크립트

기존 data/신주인수권부사채/신주인수권부사채.xlsx(연도별 시트)를 읽어
BondWithWarrantSqliteRepository로 백필합니다.

컷오버 전 필수 검증: 마이그레이션 후 Excel의 고유 접수번호 수와 DB row 수가 정확히 일치해야 함
(불일치 시 DB 기준 rebuild가 과거 데이터를 조용히 지울 위험 - db_drive_docker_migration_guide.md 1절 참고).
"""
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.domain import BondWithWarrantDecision
from src.domain.value_objects import FundingPurpose
from src.infrastructure.bond_with_warrant_sqlite_repository import BondWithWarrantSqliteRepository


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


def _row_to_decision(row: pd.Series) -> Optional[BondWithWarrantDecision]:
    rcept_no = _cell_to_str(row.get("접수번호"))
    if not rcept_no:
        return None

    company_name = _cell_to_str(row.get("상호")) or ""

    return BondWithWarrantDecision(
        # 원본 XML 파일명은 Excel에 없음 - rcept_no 기반 재구성 값(dedup 등 로직은 rcept_no 기준이라 무영향)
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        sequence_number=_cell_to_str(row.get("회차")),
        bond_type=_cell_to_str(row.get("종류")),
        face_value_total=_cell_to_int(row.get("사채의 권면(전자등록)총액")),
        funding=FundingPurpose(
            facility=_cell_to_int(row.get("시설자금")) or 0,
            operating=_cell_to_int(row.get("운영자금")) or 0,
            acquisition=_cell_to_int(row.get("타법인증권")) or 0,
            debt_repayment=_cell_to_int(row.get("채무상환자금")) or 0,
            business_acquisition=_cell_to_int(row.get("영업양수자금")) or 0,
            other=_cell_to_int(row.get("기타자금")) or 0,
        ),
        # 이율은 XML 파서도 항상 추출하지 않아 Excel에도 없음
        interest_rate=None,
        maturity_date=_cell_to_date(row.get("사채의 만기일")),
        issue_method=_cell_to_str(row.get("사채발행방법")),
        exercise_ratio=_cell_to_float(row.get("신주인수권 비율")),
        exercise_price=_cell_to_int(row.get("행사가액")),
        exercise_shares=_cell_to_int(row.get("행사에 따라 발행할 주식수")),
        shares_ratio=_cell_to_float(row.get("주식총수 대비 비율")),
        exercise_start_date=_cell_to_date(row.get("권리행사기간 시작일")),
        exercise_end_date=_cell_to_date(row.get("권리행사기간 종료일")),
        subscription_date=_cell_to_date(row.get("청약일")),
        payment_date=_cell_to_date(row.get("납입일")),
        board_resolution_date=_cell_to_date(row.get("이사회결의일")),
        # 보고서명은 Excel에 저장된 적이 없어 과거 데이터는 복구 불가
        report_name=None,
        is_correction=_cell_to_str(row.get("기재정정여부")) == "[기재정정]",
        rcept_no=rcept_no,
        parent_rcp_no=_cell_to_str(row.get("상위접수번호")),
        disclosure_date=_cell_to_date(row.get("공시일")),
        original_disclosure_date=_cell_to_date(row.get("최초공시일")),
    )


def migrate(excel_path: str, db_path: str) -> dict:
    """Excel 데이터를 SQLite로 마이그레이션합니다.

    Returns:
        {"excel_rows": 고유 접수번호 수, "db_rows": 마이그레이션 후 DB row 수, "match": 일치 여부}
    """
    repo = BondWithWarrantSqliteRepository(db_path)

    excel_file = pd.ExcelFile(excel_path)
    decisions = []

    for sheet_name in excel_file.sheet_names:
        # CB와 마찬가지로 BW 엑셀도 BaseBondExcelWriter(startrow=0) 기준 - 헤더가 0번째 행
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
        if "접수번호" not in df.columns:
            continue
        for _, row in df.iterrows():
            decision = _row_to_decision(row)
            if decision is not None:
                decisions.append(decision)

    unique_rcept_nos = {d.rcept_no for d in decisions}
    repo.upsert(decisions)

    db_row_count = repo._conn.execute("SELECT COUNT(*) FROM bond_with_warrant_decisions").fetchone()[0]

    return {
        "excel_rows": len(unique_rcept_nos),
        "db_rows": db_row_count,
        "match": len(unique_rcept_nos) == db_row_count,
    }


if __name__ == "__main__":
    result = migrate("data/신주인수권부사채/신주인수권부사채.xlsx", "data/신주인수권부사채/신주인수권부사채.db")
    print(f"Excel 고유 접수번호: {result['excel_rows']}건")
    print(f"DB row 수: {result['db_rows']}건")
    if result["match"]:
        print("✅ row count parity 일치 - 컷오버 가능")
    else:
        print("❌ row count parity 불일치 - 컷오버 중단, 원인 조사 필요")
        sys.exit(1)
