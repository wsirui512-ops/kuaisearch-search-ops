<#
.SYNOPSIS
  Rebuild everything and run every verification in one command.

.DESCRIPTION
  - python run.py                        rebuild the DuckDB file and all aggregates
  - export_parquet / verify_engines      three-way reconciliation (DuckDB / Parquet / Python)
  - position_sensitivity                 length x position baseline check
  - build_review / make_spotcheck       100-row automatic pre-screen and blank 30-row spot-check
  - make_charts / build_dashboard_preview   README charts and static dashboard
  - build_dashboard_data / build_review_workbook   Excel exports (need openpyxl)

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
  powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -SkipBuild
#>
param([switch]$SkipBuild)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = if ($env:DSH_PYTHON) { $env:DSH_PYTHON } else { "python" }

function Invoke-Step([string]$label, [scriptblock]$action) {
    Write-Host ""
    Write-Host "==> $label" -ForegroundColor Cyan
    & $action
    if ($LASTEXITCODE -ne 0) { throw "$label failed with exit code $LASTEXITCODE" }
}

if (-not $SkipBuild) {
    Invoke-Step "rebuild database and aggregates" { & $python run.py }
}
Invoke-Step "export parquet" { & $python scripts/export_parquet.py }
Invoke-Step "three-way reconciliation" { & $python scripts/verify_engines.py }
Invoke-Step "position sensitivity" { & $python scripts/position_sensitivity.py }
Invoke-Step "review table" { & $python scripts/build_review.py }
Invoke-Step "README charts" { & $python scripts/make_charts.py }
Invoke-Step "dashboard deck" { & $python scripts/build_static_dashboard.py }
Invoke-Step "dashboard render" { & $python scripts/export_dashboard.py }
Invoke-Step "dashboard assets" { & $python scripts/check_dashboard_assets.py }
Invoke-Step "dashboard preview" { & $python scripts/build_dashboard_preview.py }
Invoke-Step "verify report figures" { & $python scripts/verify_docs.py }

& $python -c "import openpyxl" 2>$null
if ($LASTEXITCODE -eq 0) {
    Invoke-Step "dashboard workbook" { & $python scripts/build_dashboard_data.py }
    if (-not (Test-Path "outputs/spotcheck_30.xlsx")) {
        Invoke-Step "blank 30-row spot-check" { & $python scripts/make_spotcheck.py }
    } else {
        Write-Host "outputs/spotcheck_30.xlsx exists: keeping the filled spot-check" -ForegroundColor Yellow
    }
} else {
    Write-Host "openpyxl not found: skipping the two Excel exports" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "all checks passed" -ForegroundColor Green
