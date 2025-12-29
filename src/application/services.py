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
    DartXmlParser,
    ExcelWriter,
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
        self.parser = DartXmlParser()
        self.excel_writer = ExcelWriter(output_path=str(self.data_directory / "유상증자.xlsx"))
        self.file_converter = FileEncodingConverter()

    def download_reports(self, start_date: str, end_date: str = None) -> int:
        """공시 데이터를 다운로드합니다.
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD, 기본값: 오늘)
            
        Returns:
            다운로드된 공시 건수
        """
        print("=" * 50)
        print("📥 유상증자 공시 데이터 다운로드")
        print("=" * 50)
        
        reports = self.api_client.collect_reports(start_date, end_date)
        print(f"\n✅ 총 {len(reports)}건의 공시를 다운로드했습니다.")
        return len(reports)

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
        self.download_reports(start_date, end_date)

        # 2. 인코딩 변환
        self.convert_xml_encoding()

        # 3. 파싱 및 엑셀 저장
        self.parse_and_export_to_excel()

        print("\n" + "🎉" * 25)
        print(" " * 15 + "전체 업데이트 완료!")
        print("🎉" * 25 + "\n")
