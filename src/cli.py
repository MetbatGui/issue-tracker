"""CLI 인터페이스

유상증자 및 무상증자 데이터 처리 프로그램의 명령줄 인터페이스입니다.
"""
import sys
import argparse
from datetime import datetime

from .application import CapitalIncreaseService, BonusSharesService


def main():
    """CLI 메인 함수"""
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
    ci_daily.add_argument("--days", type=int, default=1, help="과거 며칠까지 (기본: 1)")

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
    bonus_daily.add_argument("--days", type=int, default=1, help="과거 며칠까지 (기본: 1)")
    
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
    # 3. all 명령 (전체)
    # ==========================================
    all_parser = subparsers.add_parser("all", help="전체(유상+무상) 데이터 처리")
    all_subparsers = all_parser.add_subparsers(dest="all_command", help="전체 하위 명령")

    # daily
    all_daily = all_subparsers.add_parser("daily", help="유상/무상 일일 업데이트 일괄 실행")
    all_daily.add_argument("--days", type=int, default=None, help="과거 며칠까지 (기본: 1)")
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
                service.daily_update(getattr(args, 'days', 1))
            elif args.ci_command == "full":
                service.full_update(getattr(args, 'start', '20200101'))
            elif args.ci_command == "export":
                service.parse_and_export_to_excel()
            elif args.ci_command == "download":
                service.download_reports(args.start, getattr(args, 'end', None))
            elif args.ci_command == "convert":
                service.convert_xml_encoding()
            else:
                print("capital-increase 하위 명령어를 지정하세요.")

        # ----------------------------------
        # Bonus Shares
        # ----------------------------------
        elif args.command == "bonus":
            bonus_service = BonusSharesService()
            
            if args.bonus_command == "daily":
                bonus_service.daily_update(getattr(args, 'days', 1))
            elif args.bonus_command == "full":
                bonus_service.full_update(getattr(args, 'start', '20200101'))
            elif args.bonus_command == "export":
                bonus_service.parse_and_export_to_excel()
            elif args.bonus_command == "download":
                bonus_service.download_reports(args.start, getattr(args, 'end', None))
            else:
                print("bonus 하위 명령어를 지정하세요.")

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
                        print(f"📅 {args.start}부터 오늘까지: {days}일")
                    except ValueError:
                        print(f"❌ 잘못된 날짜 형식: {args.start} (YYYYMMDD 형식으로 입력하세요)")
                        sys.exit(1)
                else:
                    # --days가 주어진 경우 또는 기본값 사용
                    days = args.days if args.days else 1
                
                print("\n" + "="*60)
                print(f"🚀 [ALL] 유상증자 & 무상증자 일일 업데이트 시작 (최근 {days}일)")
                print("="*60)

                # 1. 유상증자
                print("\n>>> [1/2] 유상증자 업데이트 시작")
                ci_service = CapitalIncreaseService()
                ci_service.daily_update(days)

                # 2. 무상증자
                print("\n\n>>> [2/2] 무상증자 업데이트 시작")
                bonus_service = BonusSharesService()
                bonus_service.daily_update(days)

                print("\n" + "="*60)
                print("✅ [ALL] 모든 업데이트가 완료되었습니다.")
                print("="*60)
            else:
                print("all 하위 명령어를 지정하세요.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
