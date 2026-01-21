"""무상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.
"""
import sys
import glob
from typing import List

from ..domain import BonusSharesDecision
from ..infrastructure import (
    BonusSharesXmlParser,
    BonusSharesExcelWriter,
)
from .base_report_service import BaseReportService


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["BonusSharesService"]


class BonusSharesService(BaseReportService):
    """무상증자 데이터 처리 서비스
    
    다운로드, 파싱, 엑셀 저장 등의 워크플로우를 조합합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/무상증자",
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
            google_folder_id_env_var="BONUS_SHARES_GOOGLE_FOLDER_ID",
            excel_filename="무상증자.xlsx"
        )
        self.parser = BonusSharesXmlParser()
        self.excel_writer = BonusSharesExcelWriter(output_path=str(self.excel_path))

    def _parse_file_with_map(self, file_path: str, relation_map: dict) -> BonusSharesDecision:
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
        decisions: List[BonusSharesDecision] = []
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

    def _resolve_original_dates(self, decisions: List[BonusSharesDecision]) -> None:
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
        print("\n" + "🎁" * 25)
        print(" " * 10 + "무상증자 데이터 전체 업데이트")
        print("🎁" * 25 + "\n")

        # 1. 다운로드 (맵 업데이트 포함)
        downloaded_files, relation_map = self.download_reports_with_history(
            self.api_client.collect_bonus_shares_reports,
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
        print(" " * 10 + f"무상증자 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        
        print(f"📆 수집 기간: {start_date} ~ {end_date}")

        # 1. 최근 데이터 다운로드 (맵 업데이트 포함)
        downloaded_files, relation_map = self.download_reports_with_history(
            self.api_client.collect_bonus_shares_reports,
            start_date,
            end_date
        )
        
        if not downloaded_files:
            print("\n⚠️ 새로운 공시가 없습니다.")
            return

        # 2. 다운로드한 파일만 인코딩 변환
        self._convert_downloaded_files(downloaded_files)

        # 3. 전체 데이터 재구성 (CapitalIncrease와 동일한 로직 적용)
        print("\n" + "=" * 50)
        print("📊 전체 데이터 재구성")
        print("=" * 50)
        
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))
        all_decisions: List[BonusSharesDecision] = []
        
        # 관계 맵 병합
        excel_map = self._load_map_from_excel()
        if relation_map:
             excel_map.update(relation_map)
        relation_map = excel_map
        
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision and not decision.is_limited_liability_company():
                all_decisions.append(decision)

        # 중복 제거
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
        
        # 4. 구글 드라이브 업로드
        self._upload_to_google_drive()

        print("\n" + "🎉" * 25)
        print(" " * 15 + "Daily 업데이트 완료!")
        print("🎉" * 25 + "\n")
