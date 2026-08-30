param(
    [string]$Root = "$HOME\CMDO-U10-ECG",
    [int]$Bootstraps = 10000
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 STRATEGY INTERVAL AUDIT'
Write-Host ' 200 frozen audit replicates -> deterministic 95% intervals'
Write-Host '============================================================'
Write-Host "Repository : $repo"
Write-Host "U10 root   : $Root"
Write-Host "Bootstraps : $Bootstraps"

if (-not (Test-Path -LiteralPath $Root)) {
    throw "U10 root not found: $Root"
}

$pyScript = Join-Path $repo 'scripts\compute_figure5_strategy_intervals.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing Python audit script: $pyScript"
}

# Prefer the repository virtual environment used by the reproducibility workflow.
$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw 'Python not found and repository .venv is unavailable.'
    }
    $pythonExe = $pythonCmd.Source
}

$outDir = Join-Path $repo 'source_data\figure5_final_system\interval_audit'
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

$outCsv = Join-Path $outDir 'CMDO_Figure5_U10_Strategy_Intervals_v0.1.csv'
$outJson = [System.IO.Path]::ChangeExtension($outCsv, '.json')

Write-Host "`n[1] Running deterministic interval computation"
& $pythonExe $pyScript `
    --root $Root `
    --repo $repo `
    --out $outCsv `
    --bootstraps $Bootstraps

if ($LASTEXITCODE -ne 0) {
    throw "Figure 5 strategy interval computation failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path -LiteralPath $outCsv)) {
    throw "Expected CSV was not created: $outCsv"
}
if (-not (Test-Path -LiteralPath $outJson)) {
    throw "Expected JSON was not created: $outJson"
}

Write-Host "`n[2] Output integrity"
$csvHash = (Get-FileHash -LiteralPath $outCsv -Algorithm SHA256).Hash.ToLowerInvariant()
$jsonHash = (Get-FileHash -LiteralPath $outJson -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "  CSV SHA256  = $csvHash"
Write-Host "  JSON SHA256 = $jsonHash"

$rows = @(Import-Csv -LiteralPath $outCsv)
if ($rows.Count -ne 32) {
    throw "Expected 32 rows (2 datasets x 4 budgets x 4 strategies); got $($rows.Count)."
}

$datasets = @($rows | Select-Object -ExpandProperty dataset -Unique)
$strategies = @($rows | Select-Object -ExpandProperty strategy -Unique)
$budgets = @($rows | Select-Object -ExpandProperty budget -Unique)

if ($datasets.Count -ne 2) { throw "Expected 2 datasets; got $($datasets.Count)." }
if ($strategies.Count -ne 4) { throw "Expected 4 strategies; got $($strategies.Count)." }
if ($budgets.Count -ne 4) { throw "Expected 4 budgets; got $($budgets.Count)." }

Write-Host "`n[3] Compact interval table"
$rows | Select-Object dataset,budget,strategy,@{N='gain';E={('{0:+0.00;-0.00;0.00}' -f [double]$_.point_gain_pct)}},@{N='CI95';E={('[{0:+0.00;-0.00;0.00}, {1:+0.00;-0.00;0.00}]' -f [double]$_.ci95_low_pct,[double]$_.ci95_high_pct)}},ci_excludes_zero | Format-Table -AutoSize

Write-Host "`n============================================================"
Write-Host ' FIGURE 5 STRATEGY INTERVAL AUDIT: PASS'
Write-Host '============================================================'
Write-Host 'Interpretation boundary:'
Write-Host '  - These are post-hoc descriptive uncertainty intervals over the 200 frozen audit replicates.'
Write-Host '  - They are NOT population-level clinical confidence intervals.'
Write-Host '  - They do NOT replace the locked U10 verdict MECHANISM_NOT_CONFIRMED.'
Write-Host '  - Shared/fixed/cross-fit use paired bootstrap intervals.'
Write-Host '  - Permuted control uses an independent-marginal bootstrap matching the control definition.'
Write-Host "`nGenerated local files:"
Write-Host "  $outCsv"
Write-Host "  $outJson"
Write-Host "`nGit status:"
git status --short
