param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$pyScript = Join-Path $PSScriptRoot 'compute_figure5_theory_axes.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing Python audit script: $pyScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python not found on PATH.'
}

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 THEORY-AXIS AUDIT'
Write-Host ' R_id -> Lambda=B^2/V -> kappa=H/(A+C)'
Write-Host '============================================================'
Write-Host "Repository : $repo"

Write-Host "`n[1] Running frozen-data theory-axis audit"
& $python.Source $pyScript --repo $repo
if ($LASTEXITCODE -ne 0) {
    throw "Figure 5 theory-axis audit failed with code $LASTEXITCODE"
}

$outDir = Join-Path $repo 'source_data\figure5_final_system\theory_axis_audit'
$lambdaCsv = Join-Path $outDir 'CMDO_Figure5_Lambda_By_State_v0.1.csv'
$kappaCsv  = Join-Path $outDir 'CMDO_Figure5_Kappa_v0.1.csv'
$jsonPath  = Join-Path $outDir 'CMDO_Figure5_Theory_Axes_v0.1.json'

foreach ($p in @($lambdaCsv,$kappaCsv,$jsonPath)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Expected theory-axis audit output missing: $p"
    }
}

Write-Host "`n[2] Lambda = B^2/V by dataset and budget"
Import-Csv -LiteralPath $lambdaCsv |
    Select-Object dataset,budget,B,V_direct_mse,lambda_B2_over_V,oracle_quadratic_weight_wstar,observed_shared_constant_mean_weight,bias_variance_regime |
    Format-Table -AutoSize

Write-Host "`n[3] kappa = H/(A+C)"
Import-Csv -LiteralPath $kappaCsv |
    Select-Object scenario,H,A,C,A_plus_C,kappa_H_over_A_plus_C,threshold,status,evidence_role |
    Format-Table -AutoSize

$J = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json

Write-Host "`n[4] Compact result"
Write-Host ("  R_id lower-bound witness        : {0:F3}" -f [double]$J.R_id.value)
Write-Host ("  Lambda range                    : {0:F3} -> {1:F3}" -f [double]$J.Lambda.min,[double]$J.Lambda.max)
Write-Host ("  corr(w*, observed fixed weight) : {0:F3}" -f [double]$J.Lambda.corr_wstar_observed_fixed_weight)
Write-Host ("  kappa shared adaptive           : {0:F3}" -f [double]$J.kappa.shared_adaptive)
Write-Host ("  kappa permuted control          : {0:F3}" -f [double]$J.kappa.permuted_control)
Write-Host ("  kappa role-separated prediction : {0:F3}" -f [double]$J.kappa.role_separated_prediction)

Write-Host "`n============================================================"
Write-Host ' FIGURE 5 THEORY-AXIS AUDIT: PASS'
Write-Host '============================================================'
Write-Host 'Interpretation boundary:'
Write-Host '  - Lambda is a dimensionless bias-to-variance ratio, not a pass/fail certificate.'
Write-Host '  - w*=1/(1+Lambda) is the oracle quadratic reference under the stated risk model.'
Write-Host '  - kappa>1 is algebraically equivalent to H>A+C.'
Write-Host '  - Role-separated kappa is post-completion prediction/control only.'
Write-Host '  - U10 prospective verdict remains MECHANISM_NOT_CONFIRMED.'

Write-Host "`nGenerated local files:"
Write-Host "  $lambdaCsv"
Write-Host "  $kappaCsv"
Write-Host "  $jsonPath"

Write-Host "`nGit status:"
git status --short
