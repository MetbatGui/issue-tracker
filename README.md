# 유상증자 데이터 처리 프로젝트

## 설치 및 실행

### 1. 환경 설정

```powershell
# Python 3.14+ 설치 필요
# uv 설치 (없는 경우)
pip install uv
```

### 2. PowerShell에서 사용하기

**방법 1: PowerShell 함수 로드**

```powershell
# 스크립트 로드
. .\commands.ps1

# 명령어 실행
daily              # 일일 업데이트
full               # 전체 업데이트
Daily-Update-N -Days 7  # 최근 7일
```

**방법 2: just 사용** (just 설치 필요)

```powershell
just daily         # 일일 업데이트
just full          # 전체 업데이트
just daily-n 7     # 최근 7일
```

**방법 3: 직접 실행**

```powershell
uv run python -m src.cli daily
uv run python -m src.cli update --full
```

## 사용 가능한 명령어

### PowerShell 함수

| 함수 | 설명 |
|------|------|
| `Daily-Update` | 일일 업데이트 (어제~오늘) |
| `Daily-Update-N -Days 7` | 최근 N일 업데이트 |
| `Full-Update` | 전체 업데이트 (2020년부터) |
| `Export-Excel` | XML → 엑셀 변환 |
| `Convert-XML` | XML UTF-8 변환 |
| `Download-From -Start 20250101` | 특정 날짜부터 다운로드 |
| `Download-Period -Start 20250101 -End 20250131` | 특정 기간 다운로드 |

### Alias (단축 명령어)

- `daily` → `Daily-Update`
- `full` → `Full-Update`
- `export` → `Export-Excel`

## 프로젝트 구조

```
src/
├── domain/           # 도메인 계층
│   ├── models.py
│   └── value_objects.py
├── infrastructure/   # 인프라 계층
│   ├── dart_api.py
│   ├── xml_parser.py
│   ├── excel_writer.py
│   └── file_converter.py
├── application/      # 애플리케이션 계층
│   └── services.py
└── cli.py           # CLI 진입점
```

## 환경 변수 설정

`.env` 파일에 DART API 키 설정:

```
DART_API_KEY=your_api_key_here
```

## 예제

### 일일 업데이트 실행

```powershell
# PowerShell 스크립트 로드
. .\commands.ps1

# 일일 업데이트
daily
```

### 최근 7일 데이터 업데이트

```powershell
Daily-Update-N -Days 7
```

### 전체 업데이트 (처음 실행 시)

```powershell
full
```
