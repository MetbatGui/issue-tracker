# 증자·사채 공시 추적기 - Just 명령어

# PowerShell 사용 설정
set shell := ["powershell.exe", "-Command"]

# 기본 헬프 메시지 표시
default:
    @just --list

# 전체(유상+무상+전환+신주+유무상) 일일 업데이트 - cron이 실행하는 것과 동일
daily:
    uv run python -m src.cli all daily

# 최근 N일 업데이트
daily-n days:
    uv run python -m src.cli all daily --days {{days}}

# 특정 날짜부터 오늘까지 전체(유상+무상+전환+신주) 백필
full start:
    uv run python -m src.cli all daily --start {{start}}

# 도커 이미지 빌드
build:
    docker compose -f docker/docker-compose.yml build

# 컨테이너 내장 cron 서비스를 백그라운드로 기동 (스케줄: docker/crontab)
cron-up:
    docker compose -f docker/docker-compose.yml up -d --build issue-tracker-cron

setup-release:
    git checkout master
    git remote add employers-issue-tracker https://github.com/guruta71/issue-tracker.git

# Release to employers-issue-tracker
# Usage: just release
release:
    git checkout -B release master
    git push -u employers-issue-tracker release:main
    git checkout master
