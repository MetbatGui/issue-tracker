"""CLI 인터페이스

유상증자 데이터 처리 프로그램의 명령줄 인터페이스입니다.
"""
import sys
import argparse
from datetime import datetime

from .application import CapitalIncreaseService, BonusSharesService


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description="유상증자 데이터 수집 및 처리 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s download                    # 데이터 다운로드 (2020-01-01 ~ 오늘)
  %(prog)s download --start 20250101   # 특정 날짜부터 다운로드
  %(prog)s convert                     # XML 파일들 UTF-8 변환
  %(prog)s export                      # XML 파싱 후 엑셀 저장
  %(prog)s daily                       # 일일 업데이트 (어제~오늘)
  %(prog)s daily --days 7              # 최근 7일 업데이트
  %(prog)s update --full               # 전체 프로세스 실행
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # download 명령
    download_parser = subparsers.add_parser("download", help="공시 데이터 다운로드")
    download_parser.add_argument(
        "--start",
        default="20200101",
        help="시작 날짜 (YYYYMMDD, 기본값: 20200101)"
    )
    download_parser.add_argument(
        "--end",
        default=None,
        help="종료 날짜 (YYYYMMDD, 기본값: 오늘)"
    )

    # convert 명령
    subparsers.add_parser("convert", help="XML 파일들 UTF-8 인코딩 변환")

    # export 명령
    subparsers.add_parser("export", help="XML 파싱 후 엑셀 저장")

    # daily 명령
    daily_parser = subparsers.add_parser("daily", help="일일 업데이트 (최근 데이터)")
    daily_parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="과거 며칠까지 가져올지 (기본값: 1 = 어제~오늘)"
    )

    # update 명령
    update_parser = subparsers.add_parser("update", help="데이터 업데이트")
    update_parser.add_argument(
        "--full",
        action="store_true",
        help="전체 업데이트 (다운로드 + 변환 + 엑셀 저장)"
    )
    update_parser.add_argument(
        "--start",
        default="20200101",
        help="시작 날짜 (YYYYMMDD, 기본값: 20200101)"
    )

    # bonus 명령 (무상증자)
    bonus_parser = subparsers.add_parser("bonus", help="무상증자 데이터 처리")
    bonus_subparsers = bonus_parser.add_subparsers(dest="bonus_command", help="무상증자 하위 명령")
    
    # bonus daily
    bonus_daily = bonus_subparsers.add_parser("daily", help="무상증자 일일 업데이트")
    bonus_daily.add_argument("--days", type=int, default=1, help="과거 며칠까지 (기본: 1)")
    
    # bonus full
    bonus_full = bonus_subparsers.add_parser("full", help="무상증자 전체 업데이트")
    bonus_full.add_argument("--start", default="20200101", help="시작 날짜 (기본: 20200101)")
    
    # bonus export
    bonus_subparsers.add_parser("export", help="무상증자 엑셀 생성")
    
    # bonus download
    bonus_download = bonus_subparsers.add_parser("download", help="무상증자 데이터 다운로드")
    bonus_download.add_argument("--start", default="20200101", help="시작 날짜")
    bonus_download.add_argument("--end", default=None, help="종료 날짜")

    args = parser.parse_args()

    # 명령 없이 실행 시 도움말 출력
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 명령 실행
    try:
        # 무상증자 명령어
        if args.command == "bonus":
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
                return
        
        # 유상증자 명령어 (기본)
        else:
            service = CapitalIncreaseService()
            
            if args.command == "download":
                service.download_reports(args.start, args.end)

            elif args.command == "convert":
                service.convert_xml_encoding()

            elif args.command == "export":
                service.parse_and_export_to_excel()

            elif args.command == "daily":
                service.daily_update(args.days)

            elif args.command == "update":
                if args.full:
                    service.full_update(args.start)
                else:
                    print("--full 옵션을 사용하세요.")
                    sys.exit(1)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
