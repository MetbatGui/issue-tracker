"""유상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.
"""
import sys
import glob
from typing import List

from ..domain import CapitalIncreaseDecision
from ..infrastructure import (
    CapitalIncreaseXmlParser,
    CapitalIncreaseExcelWriter,
)
from .base_report_service import BaseReportService


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["CapitalIncreaseService"]


class CapitalIncreaseService(BaseReportService):
    """유상증자 데이터 처리 서비스
    
    다운로드, 파싱, 엑셀 저장 등의 워크플로우를 조합합니다.
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

    def _parse_file_with_map(self, file_path: str, relation_map: dict) -> CapitalIncreaseDecision:
        """관계 맵을 사용하여 XML 파일을 파싱합니다."""
        
        # 접수번호 추출
        rcept_no = self._extract_rcept_no(file_path)
            
        parent_rcp = relation_map.get(rcept_no) if rcept_no else None
        
        return self.parser.parse(file_path, rcept_no=rcept_no, parent_rcp_no=parent_rcp)

    def parse_and_export_to_excel(self, relation_map: dict = None) -> int:
        """XML 파일들을 파싱하여 엑셀로 저장합니다."""
        print("\n" + "=" * 50)
        print("📊 XML 파싱 및 엑셀 생성")
        print("=" * 50)

        # XML 파일 목록 가져오기
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))

        if not xml_files:
            print("❌ 처리할 XML 파일이 없습니다.")
            return 0

        print(f"📂 {len(xml_files)}개의 XML 파일을 처리합니다...")
        
        # 관계 맵 로드
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
        relation_map = base_map

        # 파싱
        decisions: List[CapitalIncreaseDecision] = []
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision:
                decisions.append(decision)

        print(f"✅ {len(decisions)}건의 데이터를 파싱했습니다.")

        # 최초공시일 계산
        self._resolve_original_dates(decisions)

        # 엑셀 저장
        if decisions:
            # 중복 제거 (rcept_no 기준)
            seen_rcp = set()
            unique_decisions = []
            for d in decisions:
                if d.rcept_no not in seen_rcp:
                    seen_rcp.add(d.rcept_no)
                    unique_decisions.append(d)
            
            print(f"✅ 중복 제거 완료: {len(decisions)} -> {len(unique_decisions)}건")
            self.excel_writer.write(unique_decisions)
            return len(unique_decisions)
        else:
            print("⚠️ 저장할 데이터가 없습니다.")
            return 0

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
            start_date
        )

        print("\n" + "🎉" * 25)
        print(" " * 15 + "Daily 업데이트 완료!")
        print("🎉" * 25 + "\n")

    def _merge_and_save(self, new_decisions: List[CapitalIncreaseDecision], relation_map: dict = None) -> None:
        """기존 엑셀 데이터와 신규 데이터를 병합하여 저장합니다."""
        import pandas as pd
        
        # 기존 데이터 로드
        if self.excel_path.exists():
            print("\n📖 기존 엑셀 데이터 로드 중...")
            try:
                existing_data = pd.read_excel(self.excel_path, sheet_name=None)
                for sheet_name, df in existing_data.items():
                    if not df.empty and '종목명' in df.columns:
                        print(f"  - {sheet_name}년: {len(df)}건")
                print(f"✅ 기존 데이터 로드 완료")
            except Exception as e:
                print(f"⚠️ 기존 데이터 로드 실패: {e}")
        
        # 전체 XML 파일 재파싱 (신규 + 기존)
        print("\n🔄 전체 데이터 재구성 중...")
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))
        all_decisions: List[CapitalIncreaseDecision] = []
        
        # 관계 맵 병합 (전달받은 최신 맵 + 엑셀 로드 맵)
        if relation_map is None:
             relation_map = self._load_map_from_excel()
        else:
             excel_map = self._load_map_from_excel()
             relation_map.update(excel_map)
             excel_map.update(relation_map)
             relation_map = excel_map
        
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision:
                all_decisions.append(decision)
        
        # 중복 제거 (rcept_no 기준)
        seen_rcp = set()
        unique_decisions = []
        for decision in all_decisions:
            if decision.rcept_no not in seen_rcp:
                seen_rcp.add(decision.rcept_no)
                unique_decisions.append(decision)
        
        print(f"✅ 총 {len(unique_decisions)}건의 고유 데이터 (중복 {len(all_decisions) - len(unique_decisions)}건 제거)")
        
        # 최초공시일 계산
        self._resolve_original_dates(unique_decisions)
        
        # 엑셀 저장
        self.excel_writer.write(unique_decisions)

