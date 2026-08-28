"""Docker cron 배포 구성의 안전한 실행 계약을 검증한다."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_docker_cron_configuration_uses_kst_root_scheduler_and_nonroot_payload():
    dockerfile = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    crontab = (ROOT / "docker" / "crontab").read_text(encoding="utf-8")
    runner = (ROOT / "docker" / "run-daily.sh").read_text(encoding="utf-8")

    assert "ln -snf /usr/share/zoneinfo/$TZ /etc/localtime" in dockerfile
    assert "user: root" in compose
    assert "name: issue-tracker" in compose
    assert ">> /proc/1/fd/1 2>&1" in crontab
    assert "su -s /bin/sh -c" in runner
    assert "src.cli all daily --days 30" in runner


def test_docker_artifacts_are_forced_to_lf_checkout():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "docker/*.sh text eol=lf" in attributes
    assert "docker/crontab text eol=lf" in attributes
    assert "docker/Dockerfile text eol=lf" in attributes


def test_cron_allows_google_oauth_token_refresh():
    compose = (ROOT / "docker" / "docker-compose.yml").read_text(encoding="utf-8")

    # OAuth refresh token은 실행 중 갱신되므로 credentials 디렉터리는 쓰기 가능해야 한다.
    assert "- ../secrets:/app/secrets\n" in compose
    assert "- ../secrets:/app/secrets:ro" not in compose


def test_bind_mounts_are_prepared_for_the_nonroot_payload_on_linux():
    compose = (ROOT / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    cron_entrypoint = (ROOT / "docker" / "cron-entrypoint.sh").read_text(encoding="utf-8")
    app_entrypoint = (ROOT / "docker" / "app-entrypoint.sh").read_text(encoding="utf-8")
    permissions = (ROOT / "docker" / "prepare-bind-mounts.sh").read_text(encoding="utf-8")

    assert 'entrypoint: ["/app/docker/app-entrypoint.sh"]' in compose
    assert "user: root" in compose
    assert "/app/docker/prepare-bind-mounts.sh" in cron_entrypoint
    assert "chown -R nonroot:nonroot" in permissions
    assert "exec runuser -u nonroot -- \"$@\"" in app_entrypoint
