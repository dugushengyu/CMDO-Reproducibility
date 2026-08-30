param(
    [string]$CanonicalDir = ""
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$pyScript = Join-Path $PSScriptRoot 'compute_figure5_system_objectives.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing Python audit script: $pyScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python not found on PATH.'
}

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 SYSTEM-OBJECTIVE AUDIT'
Write-Host ' certified utility -> breadth -> composition cost -> HAC'
Write-Host '============================================================'
Write-Host "Repository : $repo"
if ($CanonicalDir) {
    Write-Host "Canonical  : $CanonicalDir"
} else {
    Write-Host 'Canonical  : auto-resolve from CMDO config/environment'
}

$argsList = @(
    $pyScript,
    '--repo', $repo
)
if ($CanonicalDir) {
    $argsList += @('--canonical-dir', $CanonicalDir)
}

Write-Host "`n[1] Running frozen-data system-objective audit"
& $python.Source @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Figure 5 system-objective audit failed with code $LASTEXITCODE"
}

$outDir = Join-Path $repo 'source_data\figure5_final_system\objective_audit'
$candidateCsv = Join-Path $outDir 'CMDO_Figure5_Certified_Utility_Candidates_v0.1.csv'
$objectiveCsv = Join-Path $outDir 'CMDO_Figure5_System_Objectives_v0.1.csv'
$jsonPath = Join-Path $outDir 'CMDO_Figure5_System_Objectives_v0.1.json'

foreach ($p in @($candidateCsv,$objectiveCsv,$jsonPath)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Expected audit output missing: $p"
    }
}

Write-Host "`n[2] Certified utility candidates"
Import-Csv -LiteralPath $candidateCsv |
    Select-Object method,raw_pooled_gain_pct,eligible,certified_utility_pct,positive_targets,target_count,inadmissibility_reason |
    Format-Table -AutoSize

Write-Host "`n[3] Final Figure 5 system objectives"
Import-Csv -LiteralPath $objectiveCsv |
    Select-Object panel,metric,scenario,value,direction,status,note |
    Format-Table -AutoSize

$J = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json

Write-Host "`n[4] Compact result"
Write-Host ("  Certified-utility winner : {0}" -f [string]$J.certified_utility.winner)
Write-Host ("  CMDO certified utility   : {0:+0.000;-0.000;0.000}%" -f [double]$J.certified_utility.cmdo_certified_utility_pct)
Write-Host ("  Development breadth      : {0}/{1} ({2:F1}%)" -f [int]$J.breadth.development.improved,[int]$J.breadth.development.total,[double]$J.breadth.development.breadth_pct)
Write-Host ("  Cross-domain U6 breadth  : {0}/{1} ({2:F1}%)" -f [int]$J.breadth.cross_domain_U6.improved,[int]$J.breadth.cross_domain_U6.total,[double]$J.breadth.cross_domain_U6.breadth_pct)
Write-Host ("  Clinical U7 AUC breadth  : {0}/{1} ({2:F1}%)" -f [int]$J.breadth.clinical_U7_AUC.improved,[int]$J.breadth.clinical_U7_AUC.total,[double]$J.breadth.clinical_U7_AUC.breadth_pct)
Write-Host ("  C shared / perm / role   : {0:F6} / {1:F6} / {2:F6}" -f [double]$J.hac.C_shared,[double]$J.hac.C_permuted,[double]$J.hac.C_role_separated_prediction)
Write-Host ("  HAC margin shared        : {0:+0.000000;-0.000000;0.000000}" -f [double]$J.hac.margin_shared)
Write-Host ("  HAC margin permuted      : {0:+0.000000;-0.000000;0.000000}" -f [double]$J.hac.margin_permuted)
Write-Host ("  HAC margin role-sep      : {0:+0.000000;-0.000000;0.000000}" -f [double]$J.hac.margin_role_separated_prediction)
Write-Host ("  Prospective verdict      : {0}" -f [string]$J.prospective_verdict)

Write-Host "`n============================================================"
Write-Host ' FIGURE 5 SYSTEM-OBJECTIVE AUDIT: PASS'
Write-Host '============================================================'
Write-Host 'Interpretation boundary:'
Write-Host '  - Certified utility uses the frozen U5F eligibility rule, not unrestricted MAE.'
Write-Host '  - Breadth uses all frozen U5F/U6/U7 target rows.'
Write-Host '  - HAC quantities are post-completion mechanistic evidence.'
Write-Host '  - Role-separated PASS is a prediction/control, not prospective confirmation.'
Write-Host '  - U10 prospective verdict remains MECHANISM_NOT_CONFIRMED.'

Write-Host "`nGenerated local files:"
Write-Host "  $candidateCsv"
Write-Host "  $objectiveCsv"
Write-Host "  $jsonPath"

Write-Host "`nGit status:"
git status --short
