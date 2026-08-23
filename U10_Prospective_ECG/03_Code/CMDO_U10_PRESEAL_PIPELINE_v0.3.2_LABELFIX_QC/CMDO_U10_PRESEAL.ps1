param(
  [string]$Root = "$HOME\CMDO-U10-ECG",
  [int]$Workers = 16
)
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "CMDO_U10_PRESEAL_v032_LABELFIX_QC.py"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python not found on PATH." }

$mods = @("numpy","scipy","pandas","sklearn","joblib")
$missing = @()
foreach ($m in $mods) {
  & $python.Source -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$m') else 1)" *> $null
  if ($LASTEXITCODE -ne 0) { $missing += $m }
}
if ($missing.Count -gt 0) {
  Write-Host "[setup] Installing missing scientific packages..."
  & $python.Source -m pip install --user --upgrade numpy scipy pandas scikit-learn joblib
  if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}

Write-Host "============================================================"
Write-Host " CMDO U10 PRESEAL PIPELINE v0.3.2 LABELFIX+QC"
Write-Host " Root    : $Root"
Write-Host " Workers : $Workers"
Write-Host "============================================================"
& $python.Source $pyScript --root $Root --workers $Workers
if ($LASTEXITCODE -ne 0) { throw "PRESEAL pipeline failed with code $LASTEXITCODE" }
