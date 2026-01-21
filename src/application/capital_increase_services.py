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
        import re
        import os
        
        # 접수번호 추출
        rcept_no = None
        match_rcp = re.search(r'_(\d{14})\.xml$', os.path.basename(file_path))
        if match_rcp:
            rcept_no = match_rcp.group(1)
            
        parent_rcp = relation_map.get(rcept_no) if rcept_no else None
        
        return self.parser.parse(file_path, rcept_no=rcept_no, parent_rcp_no=parent_rcp)

    def parse_and_export_to_excel(self) -> int:
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
        relation_map = self._load_map_from_excel()

        # 파싱
        decisions: List[CapitalIncreaseDecision] = []
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision and not decision.is_limited_liability_company():
                decisions.append(decision)

        print(f"✅ {len(decisions)}건의 데이터를 파싱했습니다.")

        # 최초공시일 계산
        self._resolve_original_dates(decisions)

        # 엑셀 저장
        if decisions:
            self.excel_writer.write(decisions)
            return len(decisions)
        else:
            print("⚠️ 저장할 데이터가 없습니다.")
            return 0

    def _resolve_original_dates(self, decisions: List[CapitalIncreaseDecision]) -> None:
        """정정 공시의 최초 원본 공시일을 찾아 설정합니다."""
        # 1. 접수번호 맵핑 및 Dictionary 변환
        decision_map = {d.rcept_no: d for d in decisions if d.rcept_no}
        
        # 2. 각 결정에 대해 원본 찾기
        import dataclasses
        
        for i, decision in enumerate(decisions):
            # 이미 설정된 경우 패스 (만약 있다면)
            if decision.original_disclosure_date:
                continue
                
            current = decision
            visited = set()
            root_date = decision.disclosure_date
            
            # 상위로 탐색
            while current.parent_rcp_no and current.parent_rcp_no in decision_map:
                parent = decision_map[current.parent_rcp_no]
                
                # 순환 참조 방지
                if parent.rcept_no in visited:
                    break
                visited.add(parent.rcept_no)
                
                current = parent
                if current.disclosure_date:
                    root_date = current.disclosure_date
            
            # 찾은 root_date를 설정 (불변 객체이므로 교체)
            if root_date:
                decisions[i] = dataclasses.replace(decision, original_disclosure_date=root_date)

    def full_update(self, start_date: str = "20200101", end_date: str = None) -> None:
        """전체 업데이트 워크플로우를 실행합니다."""
        print("\n" + "🚀" * 25)
        print(" " * 10 + "유상증자 데이터 전체 업데이트")
        print("🚀" * 25 + "\n")

        # 1. 다운로드 (맵 업데이트 포함)
        # 중요: collect_capital_increase_reports 메서드를 전달
        downloaded_files, relation_map = self.download_reports_with_history(
            self.api_client.collect_capital_increase_reports,
            start_date,
            end_date
        )

        # 2. 다운로드한 파일만 인코딩 변환
        self._convert_downloaded_files(downloaded_files)

        # 3. 파싱 및 엑셀 저장
        self.parse_and_export_to_excel()
        
        # 4. 구글 드라이브 업로드
        self._upload_to_google_drive()

        print("\n" + "🎉" * 25)
        print(" " * 15 + "전체 업데이트 완료!")
        print("🎉" * 25 + "\n")

    def daily_update(self, days_back: int = 1) -> None:
        """일일 업데이트 워크플로우를 실행합니다.
        
        최근 N일간의 데이터를 다운로드하고 기존 엑셀에 병합합니다.
        """
        from datetime import datetime, timedelta
        
        print("\n" + "📅" * 25)
        print(" " * 10 + f"유상증자 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        
        print(f"📆 수집 기간: {start_date} ~ {end_date}")

        # 1. 최근 데이터 다운로드 (맵 업데이트 포함)
        downloaded_files, relation_map = self.download_reports_with_history(
            self.api_client.collect_capital_increase_reports,
            start_date,
            end_date
        )
        
        if not downloaded_files:
            print("\n⚠️ 새로운 공시가 없습니다.")
            return

        # 2. 다운로드한 파일만 인코딩 변환
        self._convert_downloaded_files(downloaded_files)

        # 3. 새 데이터 파싱
        print("\n" + "=" * 50)
        print("📊 신규 데이터 파싱")
        print("=" * 50)
        
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))
        new_decisions: List[CapitalIncreaseDecision] = []
        
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision and not decision.is_limited_liability_company():
                new_decisions.append(decision)

        print(f"✅ {len(new_decisions)}건의 신규 데이터를 파싱했습니다.")

        # 4. 기존 데이터와 병합
        if new_decisions:
            self._merge_and_save(new_decisions, relation_map)
        else:
            print("⚠️ 저장할 신규 데이터가 없습니다.")
        
        # 5. 구글 드라이브 업로드
        self._upload_to_google_drive()

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
            if decision and not decision.is_limited_liability_company():
                all_decisions.append(decision)
        
        # 중복 제거 (source_filename 기준)
        seen_filenames = set()
        unique_decisions = []
        for decision in all_decisions:
            if decision.source_filename not in seen_filenames:
                seen_filenames.add(decision.source_filename)
                unique_decisions.append(decision)
        
        print(f"✅ 총 {len(unique_decisions)}건의 고유 데이터 (중복 {len(all_decisions) - len(unique_decisions)}건 제거)")
        
        # 최초공시일 계산
        self._resolve_original_dates(unique_decisions)
        
        # 엑셀 저장
        self.excel_writer.write(unique_decisions)

