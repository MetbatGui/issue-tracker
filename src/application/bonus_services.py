"""무상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.
"""
import sys
import glob
from pathlib import Path
from typing import List
from datetime import datetime, timedelta

from ..domain import BonusSharesDecision
from ..infrastructure import (
    DartApiClient,
    FileEncodingConverter
)
from ..infrastructure.bonus_xml_parser import BonusSharesXmlParser
from ..infrastructure.bonus_excel_writer import BonusSharesExcelWriter


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["BonusSharesService"]


class BonusSharesService:
    """무상증자 데이터 처리 서비스
    
    다운로드, 파싱, 엑셀 저장 등의 워크플로우를 조합합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/무상증자",
        api_key: str = None
    ):
        """서비스를 초기화합니다.
        
        Args:
            data_directory: 데이터 저장 디렉토리
            api_key: DART API 키 (None이면 .env에서 로드)
        """
        self.data_directory = Path(data_directory)
        self.xml_directory = self.data_directory / "xml"
        self.api_client = DartApiClient(api_key=api_key, save_directory=str(self.data_directory))
        self.parser = BonusSharesXmlParser()
        self.excel_writer = BonusSharesExcelWriter(output_path=str(self.data_directory / "무상증자.xlsx"))
        self.file_converter = FileEncodingConverter()

    def download_reports(self, start_date: str, end_date: str = None) -> int:
        """무상증자 공시 데이터를 다운로드합니다.
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD, 기본값: 오늘)
            
        Returns:
            다운로드된 공시 건수
        """
        print("=" * 50)
        print("📥 무상증자 공시 데이터 다운로드")
        print("=" * 50)
        
        # collect_reports 메서드를 직접 구현 (bonus용)
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        curr_start = datetime.strptime(start_date, "%Y%m%d")
        final_end = datetime.strptime(end_date, "%Y%m%d")
        all_filtered_reports = []

        print(f"🚀 수집 시작: {start_date} ~ {end_date}")
        print(f"📂 XML 저장 경로: {self.xml_directory}")

        while curr_start <= final_end:
            curr_end = curr_start + timedelta(days=90)
            if curr_end > final_end:
                curr_end = final_end

            bgn_de = curr_start.strftime("%Y%m%d")
            end_de = curr_end.strftime("%Y%m%d")

            print(f"\n📅 기간 검색: {bgn_de} ~ {end_de}")

            page = 1
            while True:
                result = self.api_client.fetch_disclosure_list(bgn_de, end_de, page_no=page)

                if not result:
                    break
                if result.get('status') != '000':
                    if result.get('status') != '013':
                        print(f"  ⚠️ API 메시지: {result.get('message')}")
                    break

                list_data = result.get('list', [])
                if not list_data:
                    break

                # 무상증자 필터링 및 XML 다운로드
                filtered = self.api_client.filter_bonus_shares_reports(list_data)
                for item in filtered:
                    xml_path = self.api_client.download_document_xml(
                        item['rcept_no'],
                        item['corp_name']
                    )
                    if xml_path:
                        item['xml_path'] = str(xml_path)

                all_filtered_reports.extend(filtered)

                print(f"  - p.{page} 완료: {len(filtered)}건 추가 (누적 {len(all_filtered_reports)}건)", end="\r")

                total_page = int(result.get('total_page', 1))
                if page >= total_page:
                    break
                page += 1

            curr_start = curr_end + timedelta(days=1)

        print("\n\n✅ 전체 수집 및 XML 다운로드 완료.")
        print(f"✅ 총 {len(all_filtered_reports)}건의 공시를 다운로드했습니다.")
        return len(all_filtered_reports)

    def convert_xml_encoding(self) -> dict:
        """XML 파일들을 UTF-8로 인코딩 변환합니다.
        
        Returns:
            변환 결과 통계 딕셔너리
        """
        print("\n" + "=" * 50)
        print("🔄 XML 파일 UTF-8 인코딩 변환")
        print("=" * 50)
        
        return self.file_converter.convert_directory(self.xml_directory)

    def parse_and_export_to_excel(self) -> int:
        """XML 파일들을 파싱하여 엑셀로 저장합니다.
        
        Returns:
            저장된 데이터 건수
        """
        print("\n" + "=" * 50)
        print("📊 XML 파싱 및 엑셀 생성")
        print("=" * 50)

        # XML 파일 목록 가져오기
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))

        if not xml_files:
            print("❌ 처리할 XML 파일이 없습니다.")
            return 0

        print(f"📂 {len(xml_files)}개의 XML 파일을 처리합니다...")

        # 파싱
        decisions: List[BonusSharesDecision] = []
        for xml_file in xml_files:
            decision = self.parser.parse(xml_file)
            if decision and not decision.is_limited_liability_company():
                decisions.append(decision)

        print(f"✅ {len(decisions)}건의 데이터를 파싱했습니다.")

        # 엑셀 저장
        if decisions:
            self.excel_writer.write(decisions)
            return len(decisions)
        else:
            print("⚠️ 저장할 데이터가 없습니다.")
            return 0

    def full_update(self, start_date: str = "20200101", end_date: str = None) -> None:
        """전체 업데이트 워크플로우를 실행합니다.
        
        Args:
            start_date: 시작일자 (YYYYMMDD, 기본값: 2020-01-01)
            end_date: 종료일자 (YYYYMMDD, 기본값: 오늘)
        """
        print("\n" + "🎁" * 25)
        print(" " * 10 + "무상증자 데이터 전체 업데이트")
        print("🎁" * 25 + "\n")

        # 1. 다운로드
        self.download_reports(start_date, end_date)

        # 2. 인코딩 변환
        self.convert_xml_encoding()

        # 3. 파싱 및 엑셀 저장
        self.parse_and_export_to_excel()

        print("\n" + "🎉" * 25)
        print(" " * 15 + "전체 업데이트 완료!")
        print("🎉" * 25 + "\n")

    def daily_update(self, days_back: int = 1) -> None:
        """일일 업데이트 워크플로우를 실행합니다.
        
        최근 N일간의 데이터를 다운로드하고 기존 엑셀에 병합합니다.
        
        Args:
            days_back: 과거 며칠까지 가져올지 (기본값: 1 = 어제~오늘)
        """
        import pandas as pd
        
        print("\n" + "📅" * 25)
        print(" " * 10 + f"무상증자 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        
        print(f"📆 수집 기간: {start_date} ~ {end_date}")

        # 1. 최근 데이터 다운로드
        count = self.download_reports(start_date, end_date)
        
        if count == 0:
            print("\n⚠️ 새로운 공시가 없습니다.")
            return

        # 2. 인코딩 변환
        self.convert_xml_encoding()

        # 3. 전체 XML 파일 재파싱
        print("\n" + "=" * 50)
        print("📊 전체 데이터 재구성")
        print("=" * 50)
        
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))
        all_decisions: List[BonusSharesDecision] = []
        
        for xml_file in xml_files:
            decision = self.parser.parse(xml_file)
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
        
        # 엑셀 저장
        self.excel_writer.write(unique_decisions)

        print("\n" + "🎉" * 25)
        print(" " * 15 + "Daily 업데이트 완료!")
        print("🎉" * 25 + "\n")
