# 📑 Issue Tracker (증자·사채 공시 추적기)

DART(전자공시시스템)에서 **유상증자·무상증자·전환사채(CB)·신주인수권부사채(BW)** 공시를
자동으로 수집해 SQLite DB(SSOT)에 쌓고, 유형별 엑셀 리포트로 내보내는 배치 프로그램입니다.
유상증자와 무상증자가 동시에 발생한 "유무상증자" 케이스는 두 리포지토리를 재사용해 별도
수집 없이 파생 계산합니다.

이 문서는 다음 개발자 또는 시스템 관리자가 프로젝트를 빠르고 정확하게 파악하고 인수인계받을
수 있도록 작성되었습니다.

---

## ✨ 주요 기능

- **4개 도메인 독립 수집**: 유상증자(`capital-increase`), 무상증자(`bonus`), 전환사채(`cb`),
  신주인수권부사채(`bw`) 각각 DART 공시를 다운로드·XML 파싱·DB 저장합니다.
- **유무상증자 파생 계산**: `DualIncreaseService`가 유상증자·무상증자 리포지토리를 그대로
  재사용해, 같은 기업이 두 이벤트를 동시에 진행한 케이스를 별도 수집 없이 뽑아냅니다.
- **일일 자동 백필**: `all daily`가 4개 도메인을 한 번에 갱신하고 유무상증자까지 계산합니다.
  컨테이너 내장 cron이 평일 16:00 KST에 자동 실행하며, 최근 30일을 DB 완료 키 기준으로
  멱등 백필합니다(재수집 비용 없이 안전).
- **엑셀 리포트 생성** (`export`): 각 도메인 DB를 유형별 엑셀로 내보냅니다.
- **구글 드라이브 SSOT 동기화**: 도메인별로 별도 Drive 폴더에 DB/엑셀을 동기화합니다.

---

## 🏗 아키텍처

포트-어댑터(Hexagonal Architecture) 구조로, 비즈니스 로직이 외부 인프라(DART, SQLite,
구글 드라이브)에 직접 의존하지 않습니다.

```
issue-tracker/
├── docker/              # Docker 환경 구축 파일 (Dockerfile, docker-compose, cron 스크립트)
├── secrets/             # 인증 자격 증명 키 저장소 (Git 제외 대상)
├── data/                # SQLite SSOT DB 작업 사본 (Git 제외 대상)
├── logs/                # 로그 (Git 제외 대상)
├── src/
│   ├── application/       # CapitalIncreaseService, BonusSharesService, DualIncreaseService,
│   │                      # ConvertibleBondService, BondWithWarrantService,
│   │                      # DailyOrchestrationService(전체 흐름 소유)
│   ├── infrastructure/    # 도메인별 XML 파서/SQLite 리포지토리/엑셀 writer,
│   │                      # dart_api.py, google_drive_adapter.py, sqlite_storage_session.py
│   └── cli.py             # CLI 진입점 (capital-increase / bonus / cb / bw / all)
└── tests/                # unit + fixtures(실제 DART XML 샘플 다수)
```

- `DailyOrchestrationService`가 여러 `OrchestrationStep`(도메인별 서비스)을 조합해
  DB 다운로드 → 수집 → export → 업로드 전체 흐름을 소유합니다(`orchestration_guide.md` §1).
  CLI는 이 서비스를 호출만 합니다.
- 각 도메인은 자체 SQLite 리포지토리(`*_sqlite_repository.py`)를 SSOT로 쓰고,
  `sqlite_storage_session.py`가 GDrive 왕복(다운로드→작업→업로드)을 세션 단위로 감쌉니다
  (`db_ssot_guide.md` §6).
- 최근 30일을 매 실행마다 재조회해도, DB의 완료 키(접수번호 등) 기준으로 이미 처리된 건은
  걸러지므로 비용이 늘지 않습니다 — 사실상 자동 백필입니다(`orchestration_guide.md` §2.2).

---

## 🚀 환경 설정 및 설치

### 1. 사전 요구 사항
- Python 3.x + **`uv`** 패키지 관리자
- DART Open API 인증키
- **Docker 및 Docker Compose** (컨테이너 실행 시)

### 2. 패키지 설치
```bash
uv sync
```

### 3. 환경 변수 설정 (`.env`)
```env
DART_API_KEY=your_dart_open_api_key

CAPITAL_INCREASE_GOOGLE_FOLDER_ID=your_folder_id
BONUS_SHARES_GOOGLE_FOLDER_ID=your_folder_id
CONVERTIBLE_BOND_GOOGLE_FOLDER_ID=your_folder_id
BOND_WITH_WARRANT_GOOGLE_FOLDER_ID=your_folder_id
```

### 4. 시크릿 설정
`secrets/client_secret.json`(Google Cloud Console에서 발급받은 OAuth 2.0 Desktop app 클라이언트)을
넣어두면, 최초 실행 시 브라우저 인증을 거쳐 `secrets/token.json`이 자동 생성됩니다.

---

## 💻 사용법

```bash
# 전체(유상+무상+전환+신주+유무상) 일일 업데이트 - cron이 실행하는 것과 동일
just daily
uv run python -m src.cli all daily

# 최근 N일 업데이트
just daily-n 7

# 도메인별 개별 실행
uv run python -m src.cli capital-increase daily
uv run python -m src.cli bonus export
uv run python -m src.cli cb full
uv run python -m src.cli bw download --start 20250101

# 특정 날짜부터 오늘까지 전체(유상+무상+전환+신주) 백필
just full 20250101
```

`--help`로 각 하위 명령의 전체 옵션을 확인하세요.

---

## 🐳 Docker로 실행

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml run --rm issue-tracker python -m src.cli all daily
docker compose -f docker/docker-compose.yml up -d issue-tracker-cron
```

컨테이너 내장 cron이 스케줄에 따라 `all daily`(최근 30일 멱등 백필)를 자동 실행합니다.
스케줄은 `docker/crontab`을 참고하세요(기본: 평일 16:00 KST).

---

## 🧪 테스트

```bash
uv run pytest
```

`tests/fixtures/xml/`에 도메인별 실제 DART XML 샘플이 다수 포함돼 있어, 파서 테스트가
네트워크 없이 실제 공시 구조로 검증됩니다.

---

## 💡 인수인계 시 주의 사항 (개발 팁)

1. **DualIncreaseService는 자체 DB가 없음**: 유상증자·무상증자 리포지토리를 그대로 재사용해
   같은 기업의 동시 발생 케이스를 파생 계산합니다. CLI에도 별도 `dual` 하위 명령이 없고
   `all daily` 오케스트레이션 안에서만 호출됩니다.
2. **최근 30일 재조회는 의도된 설계**: DB 완료 키 기준으로 이미 처리된 접수번호는 걸러지므로
   비용 없이 안전합니다 — 창을 줄일 필요 없습니다(`orchestration_guide.md` §2.2).
3. **exit code로 실패를 숨기지 말 것**: 업로드/동기화 실패가 `_raise_if_failed`(cli.py)로
   전파되도록 설계돼 있습니다. 새 도메인을 추가할 때도 예외를 삼키고 조용히 성공 처리하지
   않도록 주의하세요(`docker_guide.md` §10).
4. **`tests/unit/test_no_print_calls_in_src.py`**: `src/`에 `print()`가 추가되면 이 테스트가
   실패합니다 — 새 어댑터/서비스도 반드시 `logger`를 쓸 것.
5. **의존성 패키지 관리 (`uv`)**: `pip install` 대신 `uv add <패키지명>`을 사용해
   `pyproject.toml`/`uv.lock`을 자동 최신화하세요.
