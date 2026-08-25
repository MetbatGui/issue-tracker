"""전환사채 SQLite 리포지토리 인프라스트럭처

전환사채 결정(Decision) 데이터를 SQLite에 SSOT로 저장/조회합니다.
"""
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Set

from ..domain import ConvertibleBondDecision
from ..domain.ports import ReportRepository
from ..domain.value_objects import FundingPurpose


__all__ = ["ConvertibleBondSqliteRepository"]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS convertible_bond_decisions (
    rcept_no TEXT PRIMARY KEY,
    source_filename TEXT NOT NULL,
    company_name TEXT NOT NULL,
    sequence_number TEXT,
    bond_type TEXT,
    face_value_total INTEGER,
    interest_rate REAL,
    maturity_date TEXT,
    issue_method TEXT,
    conversion_ratio REAL,
    conversion_price INTEGER,
    conversion_shares INTEGER,
    shares_ratio REAL,
    conversion_start_date TEXT,
    conversion_end_date TEXT,
    subscription_date TEXT,
    payment_date TEXT,
    board_resolution_date TEXT,
    report_name TEXT,
    is_correction INTEGER NOT NULL DEFAULT 0,
    parent_rcp_no TEXT,
    disclosure_date TEXT,
    original_disclosure_date TEXT
);

CREATE TABLE IF NOT EXISTS funding_purposes (
    decision_rcept_no TEXT NOT NULL REFERENCES convertible_bond_decisions(rcept_no),
    purpose_type TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (decision_rcept_no, purpose_type)
);
"""

_UPSERT_COLUMNS = [
    "rcept_no", "source_filename", "company_name", "sequence_number", "bond_type",
    "face_value_total", "interest_rate", "maturity_date", "issue_method",
    "conversion_ratio", "conversion_price", "conversion_shares", "shares_ratio",
    "conversion_start_date", "conversion_end_date", "subscription_date", "payment_date",
    "board_resolution_date", "report_name", "is_correction", "parent_rcp_no",
    "disclosure_date", "original_disclosure_date",
]

_FUNDING_PURPOSE_TYPES = [
    "facility", "operating", "acquisition", "debt_repayment", "business_acquisition", "other",
]


def _date_to_iso(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _iso_to_date(s: Optional[str]) -> Optional[date]:
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


class ConvertibleBondSqliteRepository(ReportRepository):
    """전환사채 결정 데이터를 SQLite에 저장/조회하는 리포지토리."""

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

    def upsert(self, decisions: List[ConvertibleBondDecision]) -> int:
        """결정 목록을 rcept_no 기준으로 upsert합니다.

        Args:
            decisions: 저장할 전환사채 결정 객체 리스트

        Returns:
            upsert된 건수
        """
        placeholders = ", ".join(f":{c}" for c in _UPSERT_COLUMNS)
        update_clause = ", ".join(f"{c} = excluded.{c}" for c in _UPSERT_COLUMNS if c != "rcept_no")
        sql = f"""
            INSERT INTO convertible_bond_decisions ({", ".join(_UPSERT_COLUMNS)})
            VALUES ({placeholders})
            ON CONFLICT(rcept_no) DO UPDATE SET {update_clause}
        """

        try:
            for decision in decisions:
                self._conn.execute(sql, self._to_row_params(decision))
                self._upsert_funding_purposes(decision.rcept_no, decision.funding)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return len(decisions)

    def get_all(self) -> List[ConvertibleBondDecision]:
        """저장된 모든 전환사채 결정을 조회합니다."""
        rows = self._conn.execute(
            f"SELECT {', '.join(_UPSERT_COLUMNS)} FROM convertible_bond_decisions"
        ).fetchall()

        return [self._row_to_decision(row) for row in rows]

    def existing_rcept_nos(self, rcept_nos: List[str]) -> Set[str]:
        if not rcept_nos:
            return set()
        placeholders = ", ".join("?" for _ in rcept_nos)
        rows = self._conn.execute(
            f"SELECT rcept_no FROM convertible_bond_decisions WHERE rcept_no IN ({placeholders})", rcept_nos
        ).fetchall()
        return {row[0] for row in rows}

    def close(self) -> None:
        self._conn.close()

    def _to_row_params(self, decision: ConvertibleBondDecision) -> dict:
        return {
            "rcept_no": decision.rcept_no,
            "source_filename": decision.source_filename,
            "company_name": decision.company_name,
            "sequence_number": decision.sequence_number,
            "bond_type": decision.bond_type,
            "face_value_total": decision.face_value_total,
            "interest_rate": decision.interest_rate,
            "maturity_date": _date_to_iso(decision.maturity_date),
            "issue_method": decision.issue_method,
            "conversion_ratio": decision.conversion_ratio,
            "conversion_price": decision.conversion_price,
            "conversion_shares": decision.conversion_shares,
            "shares_ratio": decision.shares_ratio,
            "conversion_start_date": _date_to_iso(decision.conversion_start_date),
            "conversion_end_date": _date_to_iso(decision.conversion_end_date),
            "subscription_date": _date_to_iso(decision.subscription_date),
            "payment_date": _date_to_iso(decision.payment_date),
            "board_resolution_date": _date_to_iso(decision.board_resolution_date),
            "report_name": decision.report_name,
            "is_correction": int(decision.is_correction),
            "parent_rcp_no": decision.parent_rcp_no,
            "disclosure_date": _date_to_iso(decision.disclosure_date),
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

    def _row_to_decision(self, row: tuple) -> ConvertibleBondDecision:
        values = dict(zip(_UPSERT_COLUMNS, row))
        return ConvertibleBondDecision(
            source_filename=values["source_filename"],
            company_name=values["company_name"],
            sequence_number=values["sequence_number"],
            bond_type=values["bond_type"],
            face_value_total=values["face_value_total"],
            funding=self._get_funding_purpose(values["rcept_no"]),
            interest_rate=values["interest_rate"],
            maturity_date=_iso_to_date(values["maturity_date"]),
            issue_method=values["issue_method"],
            conversion_ratio=values["conversion_ratio"],
            conversion_price=values["conversion_price"],
            conversion_shares=values["conversion_shares"],
            shares_ratio=values["shares_ratio"],
            conversion_start_date=_iso_to_date(values["conversion_start_date"]),
            conversion_end_date=_iso_to_date(values["conversion_end_date"]),
            subscription_date=_iso_to_date(values["subscription_date"]),
            payment_date=_iso_to_date(values["payment_date"]),
            board_resolution_date=_iso_to_date(values["board_resolution_date"]),
            report_name=values["report_name"],
            is_correction=bool(values["is_correction"]),
            rcept_no=values["rcept_no"],
            parent_rcp_no=values["parent_rcp_no"],
            disclosure_date=_iso_to_date(values["disclosure_date"]),
            original_disclosure_date=_iso_to_date(values["original_disclosure_date"]),
        )
