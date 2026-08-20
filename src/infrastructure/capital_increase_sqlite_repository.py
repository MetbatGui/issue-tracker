"""유상증자 SQLite 리포지토리 인프라스트럭처

유상증자 결정(Decision) 데이터를 SQLite에 SSOT로 저장/조회합니다.
"""
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from ..domain import CapitalIncreaseDecision
from ..domain.ports import ReportRepository
from ..domain.value_objects import StockInfo, FundingPurpose


__all__ = ["CapitalIncreaseSqliteRepository"]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS capital_increase_decisions (
    rcept_no TEXT PRIMARY KEY,
    source_filename TEXT NOT NULL,
    company_name TEXT NOT NULL,
    new_shares_common INTEGER NOT NULL DEFAULT 0,
    new_shares_preferred INTEGER NOT NULL DEFAULT 0,
    par_value INTEGER,
    total_shares_before INTEGER,
    issue_price INTEGER,
    method TEXT,
    assign_per_share REAL,
    board_resolution_date TEXT,
    disclosure_date TEXT,
    record_date TEXT,
    subscription_date TEXT,
    payment_date TEXT,
    report_name TEXT,
    is_correction INTEGER NOT NULL DEFAULT 0,
    parent_rcp_no TEXT,
    original_disclosure_date TEXT,
    final_issue_price TEXT,
    listing_date TEXT
);

CREATE TABLE IF NOT EXISTS funding_purposes (
    decision_rcept_no TEXT NOT NULL REFERENCES capital_increase_decisions(rcept_no),
    purpose_type TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (decision_rcept_no, purpose_type)
);
"""

# capital_increase_decisions에서 upsert 시 자동 파이프라인이 값을 채우거나 덮어쓰는 컬럼.
# final_issue_price/listing_date는 수동입력 전용 컬럼이라 의도적으로 제외한다.
_UPSERT_COLUMNS = [
    "rcept_no", "source_filename", "company_name",
    "new_shares_common", "new_shares_preferred",
    "par_value", "total_shares_before", "issue_price", "method", "assign_per_share",
    "board_resolution_date", "disclosure_date", "record_date", "subscription_date", "payment_date",
    "report_name", "is_correction", "parent_rcp_no", "original_disclosure_date",
]

_FUNDING_PURPOSE_TYPES = [
    "facility", "operating", "acquisition", "debt_repayment", "business_acquisition", "other",
]


def _date_to_iso(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _iso_to_date(s: Optional[str]) -> Optional[date]:
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


class CapitalIncreaseSqliteRepository(ReportRepository):
    """유상증자 결정 데이터를 SQLite에 저장/조회하는 리포지토리."""

    def __init__(self, db_path: str):
        """리포지토리를 초기화하고 스키마를 준비합니다.

        Args:
            db_path: SQLite 데이터베이스 파일 경로 (":memory:" 가능)
        """
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def upsert(self, decisions: List[CapitalIncreaseDecision]) -> int:
        """결정 목록을 rcept_no 기준으로 upsert합니다.

        final_issue_price/listing_date(수동입력 전용 컬럼)는 절대 덮어쓰지 않습니다.

        Args:
            decisions: 저장할 유상증자 결정 객체 리스트

        Returns:
            upsert된 건수
        """
        placeholders = ", ".join(f":{c}" for c in _UPSERT_COLUMNS)
        update_clause = ", ".join(f"{c} = excluded.{c}" for c in _UPSERT_COLUMNS if c != "rcept_no")
        sql = f"""
            INSERT INTO capital_increase_decisions ({", ".join(_UPSERT_COLUMNS)})
            VALUES ({placeholders})
            ON CONFLICT(rcept_no) DO UPDATE SET {update_clause}
        """

        for decision in decisions:
            self._conn.execute(sql, self._to_row_params(decision))
            self._upsert_funding_purposes(decision.rcept_no, decision.funding)

        self._conn.commit()
        return len(decisions)

    def get_all(self) -> List[CapitalIncreaseDecision]:
        """저장된 모든 유상증자 결정을 조회합니다."""
        rows = self._conn.execute(
            f"SELECT {', '.join(_UPSERT_COLUMNS)} FROM capital_increase_decisions"
        ).fetchall()

        return [self._row_to_decision(row) for row in rows]

    def _to_row_params(self, decision: CapitalIncreaseDecision) -> dict:
        return {
            "rcept_no": decision.rcept_no,
            "source_filename": decision.source_filename,
            "company_name": decision.company_name,
            "new_shares_common": decision.new_shares.common,
            "new_shares_preferred": decision.new_shares.preferred,
            "par_value": decision.par_value,
            "total_shares_before": decision.total_shares_before,
            "issue_price": decision.issue_price,
            "method": decision.method,
            "assign_per_share": decision.assign_per_share,
            "board_resolution_date": _date_to_iso(decision.board_resolution_date),
            "disclosure_date": _date_to_iso(decision.disclosure_date),
            "record_date": _date_to_iso(decision.record_date),
            "subscription_date": _date_to_iso(decision.subscription_date),
            "payment_date": _date_to_iso(decision.payment_date),
            "report_name": decision.report_name,
            "is_correction": int(decision.is_correction),
            "parent_rcp_no": decision.parent_rcp_no,
            "original_disclosure_date": _date_to_iso(decision.original_disclosure_date),
        }

    def _upsert_funding_purposes(self, rcept_no: str, funding: FundingPurpose) -> None:
        for purpose_type in _FUNDING_PURPOSE_TYPES:
            self._conn.execute(
                """
                INSERT INTO funding_purposes (decision_rcept_no, purpose_type, amount)
                VALUES (?, ?, ?)
                ON CONFLICT(decision_rcept_no, purpose_type) DO UPDATE SET amount = excluded.amount
                """,
                (rcept_no, purpose_type, getattr(funding, purpose_type)),
            )

    def _get_funding_purpose(self, rcept_no: str) -> FundingPurpose:
        rows = self._conn.execute(
            "SELECT purpose_type, amount FROM funding_purposes WHERE decision_rcept_no = ?",
            (rcept_no,),
        ).fetchall()
        amounts = {purpose_type: amount for purpose_type, amount in rows}
        return FundingPurpose(**{p: amounts.get(p, 0) for p in _FUNDING_PURPOSE_TYPES})

    def _row_to_decision(self, row: tuple) -> CapitalIncreaseDecision:
        values = dict(zip(_UPSERT_COLUMNS, row))
        return CapitalIncreaseDecision(
            source_filename=values["source_filename"],
            company_name=values["company_name"],
            new_shares=StockInfo(
                common=values["new_shares_common"],
                preferred=values["new_shares_preferred"],
            ),
            par_value=values["par_value"],
            total_shares_before=values["total_shares_before"],
            issue_price=values["issue_price"],
            funding=self._get_funding_purpose(values["rcept_no"]),
            method=values["method"],
            assign_per_share=values["assign_per_share"],
            board_resolution_date=_iso_to_date(values["board_resolution_date"]),
            disclosure_date=_iso_to_date(values["disclosure_date"]),
            record_date=_iso_to_date(values["record_date"]),
            subscription_date=_iso_to_date(values["subscription_date"]),
            payment_date=_iso_to_date(values["payment_date"]),
            report_name=values["report_name"],
            is_correction=bool(values["is_correction"]),
            rcept_no=values["rcept_no"],
            parent_rcp_no=values["parent_rcp_no"],
            original_disclosure_date=_iso_to_date(values["original_disclosure_date"]),
        )
