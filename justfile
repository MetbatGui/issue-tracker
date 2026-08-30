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

# 도커 이미지 빌드 (CI가 build -> deploy -> release를 독립 호출할 수 있도록 이름을
# 표준화함 - handoff_guide.md §2.1 참고)
docker-build:
    docker compose -f docker/docker-compose.yml build

# 컨테이너 내장 cron 서비스를 백그라운드로 기동 (스케줄: docker/crontab).
# 재빌드는 하지 않음 - docker-build를 먼저 실행할 것.
docker-deploy:
    docker compose -f docker/docker-compose.yml up -d issue-tracker-cron

# 현재 브랜치가 main/master일 때만 origin push - ship은 "안정화된 main 배포"가 목적이라
# feature 브랜치에서 실수로 배포/릴리즈되는 걸 막는다.
push-main:
    $branch = git rev-parse --abbrev-ref HEAD; if ($branch -ne 'main' -and $branch -ne 'master') { Write-Error "Refusing to push: current branch is '$branch', not main/master"; exit 1 }; git push origin $branch

# push-main -> docker-build -> docker-deploy -> release를 순서대로 한 번에 실행
ship: push-main docker-build docker-deploy release

setup-release:
    git checkout master
    git remote add employers-issue-tracker https://github.com/guruta71/issue-tracker.git

# Release to employers-issue-tracker
# Usage: just release
release:
    git checkout -B release master
    git push -u employers-issue-tracker release:main
    git checkout master
