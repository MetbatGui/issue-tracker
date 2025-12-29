# 유상증자 데이터 처리 프로젝트 - Just 명령어

# 기본 헬프 메시지 표시
default:
    @just --list

# 전체 업데이트 (2020년부터)
full:
    uv run python -m src.cli update --full

# 일일 업데이트 (어제~오늘)
daily:
    uv run python -m src.cli daily

# 최근 N일 업데이트
daily-n days:
    uv run python -m src.cli daily --days {{days}}

# 엑셀 파일 생성 (다운로드된 XML 파싱)
export:
    uv run python -m src.cli export

# XML 파일 UTF-8 변환
convert:
    uv run python -m src.cli convert

# 특정 날짜부터 오늘까지 다운로드
download start:
    uv run python -m src.cli download --start {{start}}

# 특정 기간 데이터 다운로드
download-period start end:
    uv run python -m src.cli download --start {{start}} --end {{end}}
