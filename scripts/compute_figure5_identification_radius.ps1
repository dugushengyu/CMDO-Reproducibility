$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$pyScript = Join-Path $PSScriptRoot 'compute_figure5_identification_radius.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing Python audit script: $pyScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python not found on PATH.'
}

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 IDENTIFICATION-RADIUS AUDIT'
Write-Host ' outcome-free lower bound -> current-outcome contraction'
Write-Host '============================================================'
Write-Host "Repository : $repo"

Write-Host "`n[1] Running frozen-data identification audit"
& $python.Source $pyScript --repo $repo
if ($LASTEXITCODE -ne 0) {
    throw "Figure 5 identification-radius audit failed with code $LASTEXITCODE"
}

$outDir = Join-Path $repo 'source_data\figure5_final_system\identification_audit'
$witnessCsv = Join-Path $outDir 'CMDO_Figure5_Identification_Witness_v0.1.csv'
$contractionCsv = Join-Path $outDir 'CMDO_Figure5_Outcome_Audit_Contraction_v0.1.csv'
$jsonPath = Join-Path $outDir 'CMDO_Figure5_Identification_Radius_v0.1.json'

foreach ($p in @($witnessCsv,$contractionCsv,$jsonPath)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Expected audit output missing: $p"
    }
}

Write-Host "`n[2] Information-closure witness"
Import-Csv -LiteralPath $witnessCsv |
    Select-Object cohort,n,telemetry_identical,auc_world_plus,auc_world_minus,auc_identified_diameter_witness,minimax_abs_auc_error_lower_bound,status |
    Format-Table -AutoSize

Write-Host "`n[3] Current-outcome direct-audit contraction"
Import-Csv -LiteralPath $contractionCsv |
    Select-Object audit_budget_m,n_temporal_cycles,mean_direct_mae,mae_relative_to_m128,mae_times_sqrt_m,global_loglog_slope |
    Format-Table -AutoSize

$J = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json

Write-Host "`n[4] Compact result"
Write-Host ("  Outcome-free minimax |AUC error| lower bound : >= {0:F3}" -f [double]$J.u11.common_minimax_abs_auc_error_lower_bound)
Write-Host ("  U8 direct-audit log-log slope               : {0:+0.000000;-0.000000;0.000000}" -f [double]$J.u8_current_outcome_audit.loglog_slope)
Write-Host ("  U8 frozen slope                             : {0:+0.000000;-0.000000;0.000000}" -f [double]$J.u8_current_outcome_audit.frozen_loglog_slope)
Write-Host ("  CV[MAE*sqrt(m)]                             : {0:F2}%" -f [double]$J.u8_current_outcome_audit.mae_times_sqrt_m_cv_pct)

$mae = @($J.u8_current_outcome_audit.mean_direct_mae)
$budgets = @($J.u8_current_outcome_audit.budgets)
Write-Host ("  U8 mean direct MAE                          : m={0} {1:F6} -> m={2} {3:F6}" -f [int]$budgets[0],[double]$mae[0],[int]$budgets[-1],[double]$mae[-1])

Write-Host "`n============================================================"
Write-Host ' FIGURE 5 IDENTIFICATION-RADIUS AUDIT: PASS'
Write-Host '============================================================'
Write-Host 'Interpretation boundary:'
Write-Host '  - R_id = 0.5 is an algorithm-independent minimax lower bound only for estimators restricted to the same outcome-independent telemetry.'
Write-Host '  - U11 is a constructive information-closure witness, not a claim about real clinical outcomes.'
Write-Host '  - U8 direct-audit contraction is empirical current-outcome sampling evidence.'
Write-Host '  - The U8 slope is descriptive root-budget scaling evidence, not a new asymptotic theorem.'
Write-Host '  - Do not present the U11 lower bound and U8 MAE as a same-cohort estimator benchmark.'

Write-Host "`nGenerated local files:"
Write-Host "  $witnessCsv"
Write-Host "  $contractionCsv"
Write-Host "  $jsonPath"

Write-Host "`nGit status:"
git status --short
