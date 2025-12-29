# 유상증자 데이터 처리 - PowerShell 스크립트

# 전체 업데이트 (2020년부터)
function Full-Update {
    uv run python -m src.cli update --full
}

# 일일 업데이트 (어제~오늘)
function Daily-Update {
    uv run python -m src.cli daily
}

# 최근 N일 업데이트
function Daily-Update-N {
    param([int]$Days = 7)
    uv run python -m src.cli daily --days $Days
}

# 엑셀 파일 생성 (다운로드된 XML 파싱)
function Export-Excel {
    uv run python -m src.cli export
}

# XML 파일 UTF-8 변환
function Convert-XML {
    uv run python -m src.cli convert
}

# 특정 날짜부터 오늘까지 다운로드
function Download-From {
    param([string]$Start)
    uv run python -m src.cli download --start $Start
}

# 특정 기간 데이터 다운로드
function Download-Period {
    param(
        [string]$Start,
        [string]$End
    )
    uv run python -m src.cli download --start $Start --end $End
}

# 사용 가능한 함수 목록 표시
function Show-Help {
    Write-Host "유상증자 데이터 처리 - PowerShell 명령어" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "사용 가능한 함수:" -ForegroundColor Yellow
    Write-Host "  Full-Update              # 전체 업데이트 (2020년부터)"
    Write-Host "  Daily-Update             # 일일 업데이트 (어제~오늘)"
    Write-Host "  Daily-Update-N -Days 7   # 최근 7일 업데이트"
    Write-Host "  Export-Excel             # 엑셀 생성"
    Write-Host "  Convert-XML              # UTF-8 변환"
    Write-Host "  Download-From -Start 20250101"
    Write-Host "  Download-Period -Start 20250101 -End 20250131"
    Write-Host ""
    Write-Host "간단 명령어 (Alias):" -ForegroundColor Yellow
    Write-Host "  daily                    # Daily-Update"
    Write-Host "  full                     # Full-Update"
    Write-Host "  export                   # Export-Excel"
    Write-Host ""
}

# Alias 설정
Set-Alias -Name daily -Value Daily-Update
Set-Alias -Name full -Value Full-Update
Set-Alias -Name export -Value Export-Excel

# 스크립트 로드 시 도움말 표시
Show-Help
