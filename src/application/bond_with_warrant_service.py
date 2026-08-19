"""신주인수권부사채 분석 서비스

신주인수권부사채 공시 데이터를 수집, 파싱하고 엑셀로 저장하는 서비스입니다.
"""
from typing import List, Optional
from datetime import datetime, timedelta

from .base_report_service import BaseReportService
from ..domain import BondWithWarrantDecision
from ..infrastructure.bond_with_warrant_xml_parser import BondWithWarrantXmlParser
from ..infrastructure.bond_with_warrant_excel_writer import BondWithWarrantExcelWriter
from ..infrastructure.dart_api import DartApiClient


__all__ = ["BondWithWarrantService"]


class BondWithWarrantService(BaseReportService):
    """신주인수권부사채 분석 서비스"""

    def __init__(
        self,
        dart_api_key: str,
        output_path: str = "data/신주인수권부사채/신주인수권부사채.xlsx",
        enable_google_drive: bool = True
    ):
        """서비스 초기화
        
        Args:
            dart_api_key: DART API 키
            output_path: 결과 엑셀 파일 경로
            enable_google_drive: 구글 드라이브 업로드 활성화 여부
        """
        super().__init__(
            data_directory="data/신주인수권부사채",
            api_key=dart_api_key,
            enable_google_drive=enable_google_drive,
            google_folder_id_env_var="BOND_WITH_WARRANT_GOOGLE_FOLDER_ID",  # 필요시 환경변수 추가
            excel_filename="신주인수권부사채.xlsx"  # output_path 인자는 초기화시 무시되고 BaseReportService 규칙 따름 (data_directory + filename)
        )
        self.output_path = output_path  # 하지만 하위호환을 위해 유지하거나, super().excel_path를 사용하도록 변경 필요
        # BaseReportService가 excel_path를 설정하므로 그것을 사용
        
        self.xml_parser = BondWithWarrantXmlParser()
        self.excel_writer = BondWithWarrantExcelWriter(str(self.excel_path))

    def _parse_file_with_map(self, file_path: str, relation_map: dict) -> Optional[BondWithWarrantDecision]:
        """관계 맵을 사용하여 XML 파일을 파싱합니다."""
        rcept_no = self._extract_rcept_no(file_path)
        parent_rcp = relation_map.get(rcept_no) if rcept_no else None
        
        return self.xml_parser.parse(file_path, rcept_no=rcept_no, parent_rcp_no=parent_rcp)

    def parse_and_export_to_excel(
        self,
        relation_map: dict = None,
        start_date: str = "20200101", # 하위호환성을 위해 남겨둠, 실제로는 run_pipeline에서 호출시 relation_map만 전달됨
        end_date: Optional[str] = None
    ) -> List[BondWithWarrantDecision]:
        """기간 내 보고서를 수집하여 엑셀로 저장합니다."""
        
        # run_pipeline에서 호출될 때는 relation_map만 전달됨. 
        # 따라서 start_date 등이 기본값으로 사용될 수 있음.
        # 하지만 여기 로직은 "이미 다운로드된 XML"을 파싱하는 것이 목적이므로 날짜는 로깅용일 뿐임.
        
        print(f"[*] 신주인수권부사채 파싱 및 엑셀 저장 시작")

        print("\n" + "=" * 50)
        print("📊 XML 파싱 및 엑셀 생성")
        print("=" * 50)

        # 3.1. 모든 XML 파일 대상 (기존에 다운로드된 것도 포함)
        import glob
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))
        
        if not xml_files:
             print("❌ 처리할 XML 파일이 없습니다.")
             return []

        # 3.2. 맵 병합 (기존 맵 + 이번 수집 맵)
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
        final_map = base_map

        decisions = []
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, final_map)
            if decision:
                decisions.append(decision)

        print(f"✅ {len(decisions)}건의 데이터를 파싱했습니다.")

        # 4. 최초공시일 계산
        self._resolve_original_dates(decisions)

        # 5. 엑셀 저장
        if decisions:
            # 중복 제거 (rcept_no 기준)
            seen_rcp = set()
            unique_decisions = []
            for d in decisions:
                key = d.rcept_no or d.source_filename
                if key not in seen_rcp:
                    seen_rcp.add(key)
                    unique_decisions.append(d)
            
            print(f"✅ 중복 제거 완료: {len(decisions)} -> {len(unique_decisions)}건")
            self.excel_writer.write(unique_decisions)
        else:
            print("[*] 저장할 데이터가 없습니다.")

        return decisions

    def daily_update(self, days: int = 30) -> None:
        """일일 업데이트 (최근 N일)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y%m%d")
        
        print(f"[*] Daily 업데이트 시작: {start_str} ~")
        
        self.run_pipeline(
            self.api_client.collect_bond_with_warrant_reports,
            start_str,
            skip_if_no_new_files=True
        )

    def full_update(self, start_date: str = "20200101") -> None:
        """전체 업데이트"""
        print(f"[*] 전체 업데이트 시작: {start_date} ~")
        
        self.run_pipeline(
            self.api_client.collect_bond_with_warrant_reports,
            start_date
        )
