"""CLI 인터페이스

유상증자 및 무상증자 데이터 처리 프로그램의 명령줄 인터페이스입니다.
"""
import sys
import argparse
from datetime import datetime

from .application import (
    CapitalIncreaseService,
    BonusSharesService,
    DualIncreaseService,
    ConvertibleBondService,
    BondWithWarrantService,
    OrchestrationStep,
    DailyOrchestrationService,
)
from .logger import setup_logger, get_logger


def _run_single_daily(name, service, days: int):
    return DailyOrchestrationService([
        OrchestrationStep(name, lambda: service),
    ]).run(days)


def _run_single_full(name, service, start_date: str):
    return DailyOrchestrationService([
        OrchestrationStep(name, lambda: service),
    ]).run_full(start_date)


def _raise_if_failed(result) -> None:
    if not result.all_succeeded:
        failed_names = ", ".join(step.name for step in result.failed_steps)
        failed_syncs = ", ".join(str(sync.target.database_path) for sync in result.failed_sync_results)
        failed_names = ", ".join(name for name in (failed_names, failed_syncs) if name)
        raise RuntimeError(f"업데이트 실패: {failed_names}")


def main():
    """CLI 메인 함수"""
    # 로거 초기화 (Root Logger 설정)
    setup_logger()
    logger = get_logger("CLI")

    parser = argparse.ArgumentParser(
        description="유상증자/무상증자 데이터 수집 및 처리 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 유상증자 (Capital Increase)
  %(prog)s capital-increase download --start 20250101
  %(prog)s capital-increase daily
  %(prog)s capital-increase export

  # 무상증자 (Bonus Shares)
  %(prog)s bonus daily
  %(prog)s bonus export

  # 전체 (Both)
  %(prog)s all daily             # 어제 데이터 업데이트
  %(prog)s all daily --days 7    # 최근 7일 데이터 업데이트
  %(prog)s all daily --start 20251230  # 2025년 12월 30일부터 오늘까지 업데이트
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # ==========================================
    # 1. capital-increase 명령 (유상증자)
    # ==========================================
    ci_parser = subparsers.add_parser("capital-increase", help="유상증자 데이터 처리")
    ci_subparsers = ci_parser.add_subparsers(dest="ci_command", help="유상증자 하위 명령")

    # daily
    ci_daily = ci_subparsers.add_parser("daily", help="유상증자 일일 업데이트")
    ci_daily.add_argument("--days", type=int, default=7, help="과거 며칠까지 (기본: 7)")

    # full
    ci_full = ci_subparsers.add_parser("full", help="유상증자 전체 업데이트")
    ci_full.add_argument("--start", default="20200101", help="시작 날짜")

    # export
    ci_subparsers.add_parser("export", help="유상증자 엑셀 생성")

    # download
    ci_download = ci_subparsers.add_parser("download", help="유상증자 데이터 다운로드")
    ci_download.add_argument("--start", default="20200101", help="시작 날짜")
    ci_download.add_argument("--end", default=None, help="종료 날짜")

    # convert
    ci_subparsers.add_parser("convert", help="XML 파일들 UTF-8 인코딩 변환")


    # ==========================================
    # 2. bonus 명령 (무상증자)
    # ==========================================
    bonus_parser = subparsers.add_parser("bonus", help="무상증자 데이터 처리")
    bonus_subparsers = bonus_parser.add_subparsers(dest="bonus_command", help="무상증자 하위 명령")
    
    # daily
    bonus_daily = bonus_subparsers.add_parser("daily", help="무상증자 일일 업데이트")
    bonus_daily.add_argument("--days", type=int, default=7, help="과거 며칠까지 (기본: 7)")
    
    # full
    bonus_full = bonus_subparsers.add_parser("full", help="무상증자 전체 업데이트")
    bonus_full.add_argument("--start", default="20200101", help="시작 날짜")
    
    # export
    bonus_subparsers.add_parser("export", help="무상증자 엑셀 생성")
    
    # download
    bonus_download = bonus_subparsers.add_parser("download", help="무상증자 데이터 다운로드")
    bonus_download.add_argument("--start", default="20200101", help="시작 날짜")
    bonus_download.add_argument("--end", default=None, help="종료 날짜")



    # ==========================================
    # 3. cb 명령 (전환사채)
    # ==========================================
    cb_parser = subparsers.add_parser("cb", help="전환사채 데이터 처리")
    cb_subparsers = cb_parser.add_subparsers(dest="cb_command", help="전환사채 하위 명령")

    # daily
    cb_daily = cb_subparsers.add_parser("daily", help="전환사채 일일 업데이트")
    cb_daily.add_argument("--days", type=int, default=7, help="과거 며칠까지 (기본: 7)")

    # full
    cb_full = cb_subparsers.add_parser("full", help="전환사채 전체 업데이트")
    cb_full.add_argument("--start", default="20200101", help="시작 날짜")

    # export
    cb_subparsers.add_parser("export", help="전환사채 엑셀 생성")


    # ==========================================
    # 5. bw 명령 (신주인수권부사채)
    # ==========================================
    bw_parser = subparsers.add_parser("bw", help="신주인수권부사채 데이터 처리")
    bw_subparsers = bw_parser.add_subparsers(dest="bw_command", help="신주인수권부사채 하위 명령")

    # daily
    bw_daily = bw_subparsers.add_parser("daily", help="신주인수권부사채 일일 업데이트")
    bw_daily.add_argument("--days", type=int, default=7, help="과거 며칠까지 (기본: 7)")

    # full
    bw_full = bw_subparsers.add_parser("full", help="신주인수권부사채 전체 업데이트")
    bw_full.add_argument("--start", default="20200101", help="시작 날짜")

    # export
    bw_subparsers.add_parser("export", help="신주인수권부사채 엑셀 생성")


    # ==========================================
    # 6. all 명령 (전체)
    # ==========================================
    all_parser = subparsers.add_parser("all", help="전체(유상+무상+전환+신주) 데이터 처리")
    all_subparsers = all_parser.add_subparsers(dest="all_command", help="전체 하위 명령")

    # daily
    all_daily = all_subparsers.add_parser("daily", help="전체 일일 업데이트 일괄 실행")
    all_daily.add_argument("--days", type=int, default=7, help="과거 며칠까지 (기본: 7)")
    all_daily.add_argument("--start", default=None, help="시작 날짜 (YYYYMMDD 형식, 오늘까지 자동 계산)")


    args = parser.parse_args()

    # 명령 없이 실행 시 도움말 출력
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 명령 실행
    try:
        # ----------------------------------
        # Capital Increase
        # ----------------------------------
        if args.command == "capital-increase":
            service = CapitalIncreaseService()
            
            if args.ci_command == "daily":
                _raise_if_failed(_run_single_daily("유상증자", service, getattr(args, 'days', 1)))
            elif args.ci_command == "full":
                _raise_if_failed(_run_single_full("유상증자", service, getattr(args, 'start', '20200101')))
            elif args.ci_command == "export":
                service.parse_and_export_to_excel()
            elif args.ci_command == "download":
                service.download_reports(args.start, getattr(args, 'end', None))
            elif args.ci_command == "convert":
                service.convert_xml_encoding()
            else:
                logger.warning("capital-increase 하위 명령어를 지정하세요.")

        # ----------------------------------
        # Bonus Shares
        # ----------------------------------
        elif args.command == "bonus":
            bonus_service = BonusSharesService()
            
            if args.bonus_command == "daily":
                _raise_if_failed(_run_single_daily("무상증자", bonus_service, getattr(args, 'days', 1)))
            elif args.bonus_command == "full":
                _raise_if_failed(_run_single_full("무상증자", bonus_service, getattr(args, 'start', '20200101')))
            elif args.bonus_command == "export":
                bonus_service.parse_and_export_to_excel()
            elif args.bonus_command == "download":
                bonus_service.download_reports(args.start, getattr(args, 'end', None))
            else:
                logger.warning("bonus 하위 명령어를 지정하세요.")

        # ----------------------------------
        # Convertible Bond
        # ----------------------------------
        elif args.command == "cb":
            service = ConvertibleBondService()
            
            if args.cb_command == "daily":
                _raise_if_failed(_run_single_daily("전환사채", service, getattr(args, 'days', 1)))
            elif args.cb_command == "full":
                _raise_if_failed(_run_single_full("전환사채", service, getattr(args, 'start', '20200101')))
            elif args.cb_command == "export":
                service.parse_and_export_to_excel()
            else:
                logger.warning("cb 하위 명령어를 지정하세요.")

        # ----------------------------------
        # Bond with Warrant (BW)
        # ----------------------------------
        elif args.command == "bw":
            service = BondWithWarrantService(dart_api_key=None)  # API 키는 .env에서 로드
            
            if args.bw_command == "daily":
                _raise_if_failed(_run_single_daily("신주인수권부사채", service, getattr(args, 'days', 1)))
            elif args.bw_command == "full":
                _raise_if_failed(_run_single_full("신주인수권부사채", service, getattr(args, 'start', '20200101')))
            elif args.bw_command == "export":
                service.parse_and_export_to_excel()
            else:
                logger.warning("bw 하위 명령어를 지정하세요.")

        # ----------------------------------
        # All (Combined)
        # ----------------------------------
        elif args.command == "all":
            if args.all_command == "daily":
                # --start와 --days 옵션 처리
                if args.start:
                    # --start가 주어진 경우: 시작 날짜부터 오늘까지 일수 계산
                    try:
                        start_date = datetime.strptime(args.start, "%Y%m%d")
                        today = datetime.now()
                        days = (today - start_date).days + 1  # 시작일 포함
                        logger.info(f"{args.start}부터 오늘까지: {days}일")
                    except ValueError:
                        logger.error(f"잘못된 날짜 형식: {args.start} (YYYYMMDD 형식으로 입력하세요)")
                        sys.exit(1)
                else:
                    # --days가 주어진 경우 또는 기본값 사용
                    days = args.days if args.days is not None else 7
                
                logger.info("="*60)
                logger.info(f"🚀 [ALL] 유상/무상/전환사채/신주인수권부사채 일일 업데이트 시작 (최근 {days}일)")
                logger.info("="*60)

                orchestrator = DailyOrchestrationService([
                    OrchestrationStep("유상증자", lambda: CapitalIncreaseService()),
                    OrchestrationStep("무상증자", lambda: BonusSharesService()),
                    OrchestrationStep("유무상증자", lambda: DualIncreaseService()),
                    OrchestrationStep("전환사채", lambda: ConvertibleBondService()),
                    OrchestrationStep("신주인수권부사채", lambda: BondWithWarrantService(dart_api_key=None)),
                ])
                result = orchestrator.run(days)

                logger.info("="*60)
                if result.all_succeeded:
                    logger.info("✅ [ALL] 모든 업데이트가 완료되었습니다.")
                else:
                    failed_names = ", ".join(s.name for s in result.failed_steps)
                    failed_syncs = ", ".join(str(sync.target.database_path) for sync in result.failed_sync_results)
                    failed_names = ", ".join(name for name in (failed_names, failed_syncs) if name)
                    logger.error(f"⚠️ [ALL] 일부 업데이트 실패: {failed_names}")
                logger.info("="*60)

                if not result.all_succeeded:
                    sys.exit(1)
            else:
                logger.warning("all 하위 명령어를 지정하세요.")

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
