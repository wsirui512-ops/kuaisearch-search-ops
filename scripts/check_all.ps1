<#
.SYNOPSIS
  Rebuild everything and run every verification in one command.

.DESCRIPTION
  - python run.py                        rebuild the DuckDB file and all aggregates
  - export_parquet / verify_engines      three-way reconciliation (DuckDB / Parquet / Python)
  - position_sensitivity                 length x position baseline check
  - build_review                        100-row query x product review table
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
Invoke-Step "dashboard preview" { & $python scripts/build_dashboard_preview.py }

& $python -c "import openpyxl" 2>$null
if ($LASTEXITCODE -eq 0) {
    Invoke-Step "dashboard workbook" { & $python scripts/build_dashboard_data.py }
    Invoke-Step "review workbook" { & $python scripts/build_review_workbook.py }
} else {
    Write-Host "openpyxl not found: skipping the two Excel exports" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "all checks passed" -ForegroundColor Green
