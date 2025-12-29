"""CLI 인터페이스

유상증자 데이터 처리 프로그램의 명령줄 인터페이스입니다.
"""
import sys
import argparse
from datetime import datetime

from .application import CapitalIncreaseService


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

    args = parser.parse_args()

    # 명령 없이 실행 시 도움말 출력
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 서비스 초기화
    service = CapitalIncreaseService()

    # 명령 실행
    try:
        if args.command == "download":
            service.download_reports(args.start, args.end)

        elif args.command == "convert":
            service.convert_xml_encoding()

        elif args.command == "export":
            service.parse_and_export_to_excel()

        elif args.command == "update":
            if args.full:
                service.full_update(args.start)
            else:
                print("--full 옵션을 사용하세요.")
                update_parser.print_help()
                sys.exit(1)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
