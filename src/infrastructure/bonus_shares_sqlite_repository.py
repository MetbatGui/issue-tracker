"""무상증자 SQLite 리포지토리 인프라스트럭처

무상증자 결정(Decision) 데이터를 SQLite에 SSOT로 저장/조회합니다.
유상증자와 달리 자금조달목적(FundingPurpose)이 없고, listing_date는 manual-only 필드가 아니라
실제 파싱값이라 재upsert 시 정상적으로 갱신됩니다.
"""
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Set

from ..domain import BonusSharesDecision
from ..domain.ports import ReportRepository
from ..domain.value_objects import StockInfo


__all__ = ["BonusSharesSqliteRepository"]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS bonus_shares_decisions (
    rcept_no TEXT PRIMARY KEY,
    source_filename TEXT NOT NULL,
    company_name TEXT NOT NULL,
    new_shares_common INTEGER NOT NULL DEFAULT 0,
    new_shares_preferred INTEGER NOT NULL DEFAULT 0,
    par_value INTEGER,
    total_shares_before INTEGER,
    assign_per_share REAL,
    board_resolution_date TEXT,
    disclosure_date TEXT,
    record_date TEXT,
    listing_date TEXT,
    report_name TEXT,
    is_correction INTEGER NOT NULL DEFAULT 0,
    parent_rcp_no TEXT,
    original_disclosure_date TEXT
);
"""

_UPSERT_COLUMNS = [
    "rcept_no", "source_filename", "company_name",
    "new_shares_common", "new_shares_preferred",
    "par_value", "total_shares_before", "assign_per_share",
    "board_resolution_date", "disclosure_date", "record_date", "listing_date",
    "report_name", "is_correction", "parent_rcp_no", "original_disclosure_date",
]


def _date_to_iso(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _iso_to_date(s: Optional[str]) -> Optional[date]:
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


class BonusSharesSqliteRepository(ReportRepository):
    """무상증자 결정 데이터를 SQLite에 저장/조회하는 리포지토리."""

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

    def upsert(self, decisions: List[BonusSharesDecision]) -> int:
        """결정 목록을 rcept_no 기준으로 upsert합니다.

        Args:
            decisions: 저장할 무상증자 결정 객체 리스트

        Returns:
            upsert된 건수
        """
        placeholders = ", ".join(f":{c}" for c in _UPSERT_COLUMNS)
        update_clause = ", ".join(f"{c} = excluded.{c}" for c in _UPSERT_COLUMNS if c != "rcept_no")
        sql = f"""
            INSERT INTO bonus_shares_decisions ({", ".join(_UPSERT_COLUMNS)})
            VALUES ({placeholders})
            ON CONFLICT(rcept_no) DO UPDATE SET {update_clause}
        """

        try:
            for decision in decisions:
                self._conn.execute(sql, self._to_row_params(decision))
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return len(decisions)

    def get_all(self) -> List[BonusSharesDecision]:
        """저장된 모든 무상증자 결정을 조회합니다."""
        rows = self._conn.execute(
            f"SELECT {', '.join(_UPSERT_COLUMNS)} FROM bonus_shares_decisions"
        ).fetchall()

        return [self._row_to_decision(row) for row in rows]

    def existing_rcept_nos(self, rcept_nos: List[str]) -> Set[str]:
        if not rcept_nos:
            return set()
        placeholders = ", ".join("?" for _ in rcept_nos)
        rows = self._conn.execute(
            f"SELECT rcept_no FROM bonus_shares_decisions WHERE rcept_no IN ({placeholders})", rcept_nos
        ).fetchall()
        return {row[0] for row in rows}

    def _to_row_params(self, decision: BonusSharesDecision) -> dict:
        return {
            "rcept_no": decision.rcept_no,
            "source_filename": decision.source_filename,
            "company_name": decision.company_name,
            "new_shares_common": decision.new_shares.common,
            "new_shares_preferred": decision.new_shares.preferred,
            "par_value": decision.par_value,
            "total_shares_before": decision.total_shares_before,
            "assign_per_share": decision.assign_per_share,
            "board_resolution_date": _date_to_iso(decision.board_resolution_date),
            "disclosure_date": _date_to_iso(decision.disclosure_date),
            "record_date": _date_to_iso(decision.record_date),
            "listing_date": _date_to_iso(decision.listing_date),
            "report_name": decision.report_name,
            "is_correction": int(decision.is_correction),
            "parent_rcp_no": decision.parent_rcp_no,
            "original_disclosure_date": _date_to_iso(decision.original_disclosure_date),
        }

    def _row_to_decision(self, row: tuple) -> BonusSharesDecision:
        values = dict(zip(_UPSERT_COLUMNS, row))
        return BonusSharesDecision(
            source_filename=values["source_filename"],
            company_name=values["company_name"],
            new_shares=StockInfo(
                common=values["new_shares_common"],
                preferred=values["new_shares_preferred"],
            ),
            par_value=values["par_value"],
            total_shares_before=values["total_shares_before"],
            assign_per_share=values["assign_per_share"],
            board_resolution_date=_iso_to_date(values["board_resolution_date"]),
            disclosure_date=_iso_to_date(values["disclosure_date"]),
            record_date=_iso_to_date(values["record_date"]),
            listing_date=_iso_to_date(values["listing_date"]),
            report_name=values["report_name"],
            is_correction=bool(values["is_correction"]),
            rcept_no=values["rcept_no"],
            parent_rcp_no=values["parent_rcp_no"],
            original_disclosure_date=_iso_to_date(values["original_disclosure_date"]),
        )
