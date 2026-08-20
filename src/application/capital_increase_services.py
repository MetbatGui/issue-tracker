"""유상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.

DB(SQLite)가 SSOT입니다: XML 파싱 결과는 CapitalIncreaseSqliteRepository에 upsert되고,
Excel은 매 실행마다 DB 전체를 읽어 재구성되는 산출물입니다.
"""
import sys
import glob
from typing import List

from ..domain import CapitalIncreaseDecision
from ..infrastructure import (
    CapitalIncreaseXmlParser,
    CapitalIncreaseExcelWriter,
)
from ..infrastructure.capital_increase_sqlite_repository import CapitalIncreaseSqliteRepository
from .base_report_service import BaseReportService


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["CapitalIncreaseService"]


class CapitalIncreaseService(BaseReportService):
    """유상증자 데이터 처리 서비스

    다운로드, 파싱, DB 저장, 엑셀 재구성 워크플로우를 조합합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/유상증자",
        api_key: str = None,
        enable_google_drive: bool = True
    ):
        """서비스를 초기화합니다.

        Args:
            data_directory: 데이터 저장 디렉토리
            api_key: DART API 키 (None이면 .env에서 로드)
            enable_google_drive: 구글 드라이브 업로드 활성화 여부
        """
        super().__init__(
            data_directory=data_directory,
            api_key=api_key,
            enable_google_drive=enable_google_drive,
            google_folder_id_env_var="CAPITAL_INCREASE_GOOGLE_FOLDER_ID",
            excel_filename="유상증자.xlsx"
        )
        self.parser = CapitalIncreaseXmlParser()
        self.excel_writer = CapitalIncreaseExcelWriter(output_path=str(self.excel_path))
        self.repository = CapitalIncreaseSqliteRepository(str(self.data_directory / "유상증자.db"))

    def get_relation_map(self) -> dict:
        """DB에 저장된 parent_rcp_no 관계를 관계맵으로 반환합니다.

        DB가 SSOT이므로 relation_map.json/Excel 폴백(BaseReportService의 기본 구현)은 쓰지 않습니다.
        """
        return {
            d.rcept_no: d.parent_rcp_no
            for d in self.repository.get_all()
            if d.parent_rcp_no
        }

    def _parse_file_with_map(self, file_path: str, relation_map: dict) -> CapitalIncreaseDecision:
        """관계 맵을 사용하여 XML 파일을 파싱합니다."""

        # 접수번호 추출
        rcept_no = self._extract_rcept_no(file_path)

        parent_rcp = relation_map.get(rcept_no) if rcept_no else None

        return self.parser.parse(file_path, rcept_no=rcept_no, parent_rcp_no=parent_rcp)

    def parse_and_export_to_excel(self, relation_map: dict = None) -> int:
        """XML 파일들을 파싱해 DB에 반영한 뒤, DB 전체로 엑셀을 재구성합니다."""
        print("\n" + "=" * 50)
        print("📊 XML 파싱 및 DB 반영")
        print("=" * 50)

        # XML 파일 목록 가져오기
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))

        if not xml_files:
            print("❌ 처리할 XML 파일이 없습니다.")
            return 0

        print(f"📂 {len(xml_files)}개의 XML 파일을 처리합니다...")

        # 관계 맵 로드 (DB 기준)
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
        relation_map = base_map

        # 파싱
        decisions: List[CapitalIncreaseDecision] = []
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision and not decision.is_limited_liability_company():
                decisions.append(decision)

        print(f"✅ {len(decisions)}건의 데이터를 파싱했습니다.")

        if decisions:
            self.repository.upsert(decisions)
            print(f"💾 DB 반영 완료: {len(decisions)}건")

        return self.export_to_excel()

    def export_to_excel(self) -> int:
        """DB에 저장된 전체 데이터를 엑셀로 재구성합니다."""
        decisions = self.repository.get_all()

        if not decisions:
            print("⚠️ 저장할 데이터가 없습니다.")
            return 0

        # 최초공시일 계산 (parent_rcp_no 체인을 따라가는 파생값이라 DB에는 저장하지 않고 매번 계산)
        self._resolve_original_dates(decisions)

        self.excel_writer.write(decisions)
        return len(decisions)

    def full_update(self, start_date: str = "20200101", end_date: str = None) -> None:
        """전체 업데이트 워크플로우를 실행합니다."""
        print("\n" + "🚀" * 25)
        print(" " * 10 + "유상증자 데이터 전체 업데이트")
        print("🚀" * 25 + "\n")

        self.run_pipeline(
            self.api_client.collect_capital_increase_reports,
            start_date,
            end_date
        )

        print("\n" + "🎉" * 25)
        print(" " * 15 + "전체 업데이트 완료!")
        print("🎉" * 25 + "\n")

    def daily_update(self, days_back: int = 1) -> None:
        """일일 업데이트 워크플로우를 실행합니다.

        최근 N일간의 데이터를 다운로드하고 (이전 로직과 달리) 전체 데이터 재구성을 통해 엑셀을 갱신합니다.
        """
        from datetime import datetime, timedelta

        print("\n" + "📅" * 25)
        print(" " * 10 + f"유상증자 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")

        print(f"📆 수집 기간: {start_date} ~ Today")

        self.run_pipeline(
            self.api_client.collect_capital_increase_reports,
            start_date,
            skip_if_no_new_files=True
        )

        print("\n" + "🎉" * 25)
        print(" " * 15 + "Daily 업데이트 완료!")
        print("🎉" * 25 + "\n")
