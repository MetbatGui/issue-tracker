#!/bin/sh
set -e
cd /app

# cron은 root로 기동하지만 실제 수집과 원격 동기화는 최소 권한 사용자로 실행한다.
exec su -s /bin/sh -c '/app/.venv/bin/python -m src.cli all daily --days 30' nonroot
