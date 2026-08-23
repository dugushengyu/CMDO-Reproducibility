param(
  [string]$Root = "$HOME\CMDO-U10-ECG"
)
$ErrorActionPreference="Stop"
$scriptDir=Split-Path -Parent $MyInvocation.MyCommand.Path
$py=Join-Path $scriptDir "CMDO_U10_DEPENDENCE_DECOMPOSITION_v01.py"
$python=Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python not found." }

Write-Host "============================================================"
Write-Host " CMDO U10 POST-HOC DEPENDENCE DECOMPOSITION v0.1"
Write-Host " Prospective verdict remains immutable."
Write-Host "============================================================"
& $python.Source $py --root $Root
if ($LASTEXITCODE -ne 0) { throw "Dependence decomposition failed with code $LASTEXITCODE" }
