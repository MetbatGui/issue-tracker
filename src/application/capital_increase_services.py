"""유상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.
"""
import sys
import glob
from pathlib import Path
from typing import List

from ..domain import CapitalIncreaseDecision
from ..infrastructure import (
    DartApiClient,
    CapitalIncreaseXmlParser,
    CapitalIncreaseExcelWriter,
    FileEncodingConverter
)


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["CapitalIncreaseService"]


class CapitalIncreaseService:
    """유상증자 데이터 처리 서비스
    
    다운로드, 파싱, 엑셀 저장 등의 워크플로우를 조합합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/유상증자",
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
        self.parser = CapitalIncreaseXmlParser()
        self.excel_writer = CapitalIncreaseExcelWriter(output_path=str(self.data_directory / "유상증자.xlsx"))
        self.file_converter = FileEncodingConverter()

    def download_reports(self, start_date: str, end_date: str = None) -> List[str]:
        """공시 데이터를 다운로드합니다.
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD, 기본값: 오늘)
            
        Returns:
            다운로드된 XML 파일 경로 리스트
        """
        print("=" * 50)
        print("📥 유상증자 공시 데이터 다운로드")
        print("=" * 50)
        
        reports = self.api_client.collect_reports(start_date, end_date)
        
        # 다운로드된 파일 경로 추출
        downloaded_files = [report['xml_path'] for report in reports if 'xml_path' in report]
        
        print(f"\n✅ 총 {len(reports)}건의 공시를 다운로드했습니다.")
        return downloaded_files

    def convert_xml_encoding(self) -> dict:
        """XML 파일들을 UTF-8로 인코딩 변환합니다.
        
        Returns:
            변환 결과 통계 딕셔너리
        """
        print("\n" + "=" * 50)
        print("🔄 XML 파일 UTF-8 인코딩 변환")
        print("=" * 50)
        
        return self.file_converter.convert_directory(self.xml_directory)
    
    def _convert_downloaded_files(self, file_paths: List[str]) -> dict:
        """다운로드한 파일들만 UTF-8로 인코딩 변환합니다.
        
        Args:
            file_paths: 변환할 파일 경로 리스트
            
        Returns:
            변환 결과 통계 딕셔너리
        """
        if not file_paths:
            return {"converted": 0, "already_utf8": 0, "errors": 0}
        
        print("\n" + "=" * 50)
        print(f"🔄 다운로드한 {len(file_paths)}개 파일 UTF-8 변환")
        print("=" * 50)
        
        converted = 0
        already_utf8 = 0
        errors = 0
        
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            result = self.file_converter.detect_and_read(file_path)
            
            if result and result[0].lower() != 'utf-8':
                if self.file_converter.convert_to_utf8(file_path):
                    converted += 1
                else:
                    errors += 1
            elif result and result[0].lower() == 'utf-8':
                already_utf8 += 1
            else:
                errors += 1
        
        print(f"\n✅ 변환 완료: {converted}개 | 이미 UTF-8: {already_utf8}개 | 오류: {errors}개")
        return {"converted": converted, "already_utf8": already_utf8, "errors": errors}

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
        decisions: List[CapitalIncreaseDecision] = []
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
        print("\n" + "🚀" * 25)
        print(" " * 10 + "유상증자 데이터 전체 업데이트")
        print("🚀" * 25 + "\n")

        # 1. 다운로드
        downloaded_files = self.download_reports(start_date, end_date)

        # 2. 다운로드한 파일만 인코딩 변환
        self._convert_downloaded_files(downloaded_files)

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
        from datetime import datetime, timedelta
        import os
        
        print("\n" + "📅" * 25)
        print(" " * 10 + f"유상증자 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        
        print(f"📆 수집 기간: {start_date} ~ {end_date}")

        # 1. 최근 데이터 다운로드
        downloaded_files = self.download_reports(start_date, end_date)
        
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
            decision = self.parser.parse(xml_file)
            if decision and not decision.is_limited_liability_company():
                new_decisions.append(decision)

        print(f"✅ {len(new_decisions)}건의 신규 데이터를 파싱했습니다.")

        # 4. 기존 데이터와 병합
        if new_decisions:
            self._merge_and_save(new_decisions)
        else:
            print("⚠️ 저장할 신규 데이터가 없습니다.")

        print("\n" + "🎉" * 25)
        print(" " * 15 + "Daily 업데이트 완료!")
        print("🎉" * 25 + "\n")

    def _merge_and_save(self, new_decisions: List[CapitalIncreaseDecision]) -> None:
        """기존 엑셀 데이터와 신규 데이터를 병합하여 저장합니다.
        
        Args:
            new_decisions: 신규 유상증자 결정 목록
        """
        import pandas as pd
        
        excel_path = self.data_directory / "유상증자.xlsx"
        
        # 기존 데이터 로드
        existing_decisions: List[CapitalIncreaseDecision] = []
        
        if excel_path.exists():
            print("\n📖 기존 엑셀 데이터 로드 중...")
            try:
                # 모든 시트의 데이터를 읽어서 중복 확인용으로 사용
                existing_data = pd.read_excel(excel_path, sheet_name=None)
                existing_filenames = set()
                
                for sheet_name, df in existing_data.items():
                    if not df.empty and '종목명' in df.columns:
                        # 각 시트의 데이터 개수 출력
                        print(f"  - {sheet_name}년: {len(df)}건")
                
                print(f"✅ 기존 데이터 로드 완료")
            except Exception as e:
                print(f"⚠️ 기존 데이터 로드 실패: {e}")
        
        # 전체 XML 파일 재파싱 (신규 + 기존)
        print("\n🔄 전체 데이터 재구성 중...")
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))
        all_decisions: List[CapitalIncreaseDecision] = []
        
        for xml_file in xml_files:
            decision = self.parser.parse(xml_file)
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
        
        # 엑셀 저장
        self.excel_writer.write(unique_decisions)

