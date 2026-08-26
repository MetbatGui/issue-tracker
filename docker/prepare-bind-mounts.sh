#!/bin/sh
set -e

# Linux bind mount는 호스트의 UID/GID를 그대로 사용한다. cron은 root로 기동하므로
# 수집 payload(nonroot)가 DB·로그·OAuth 토큰을 쓸 수 있게 마운트 디렉터리를 준비한다.
for mount_path in /app/data /app/logs /app/secrets; do
    mkdir -p "$mount_path"
    chown -R nonroot:nonroot "$mount_path"
done
