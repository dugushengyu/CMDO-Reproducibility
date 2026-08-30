# CMDO Figure 5 final-system verifier
# PowerShell 5.1 compatible.
#
# Scientific source of truth: GitHub repository.
# Local MATLAB is rendering only.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw "ASSERTION FAILED: $Message"
    }
}

function Assert-Close {
    param(
        [double]$Actual,
        [double]$Expected,
        [double]$Tol,
        [string]$Message
    )
    if ([Math]::Abs($Actual - $Expected) -gt $Tol) {
        throw ("ASSERTION FAILED: {0}`n  actual   = {1:R}`n  expected = {2:R}`n  tol      = {3:R}" -f $Message,$Actual,$Expected,$Tol)
    }
}

function Mean-Double {
    param([double[]]$Values)
    Assert-True ($Values.Count -gt 0) 'Mean requested on empty vector.'
    $sum = 0.0
    foreach ($v in $Values) { $sum += $v }
    return $sum / [double]$Values.Count
}

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$summaryPath = Join-Path $repo 'source_data\figure5_final_system\CMDO_Figure5_Final_System_v1.0.json'
Assert-True (Test-Path -LiteralPath $summaryPath) "Missing integration summary: $summaryPath"

$S = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 FINAL-SYSTEM VERIFY'
Write-Host ' REUSE -> PRESERVE -> IDENTIFY CLOSURE'
Write-Host '============================================================'
Write-Host "Repository : $repo"
Write-Host "Summary    : $summaryPath"

# -------------------------------------------------------------------------
# 1. Required upstream files
# -------------------------------------------------------------------------
$sourceFields = @(
    'u8_temporal_source',
    'u9b_summary',
    'u9b_composability',
    'u10_primary',
    'u10_dependence_csv',
    'u10_dependence_json',
    'u11_result',
    'u11_sha256_manifest'
)

Write-Host "`n[1] Required upstream files"
foreach ($field in $sourceFields) {
    $rel = [string]$S.sources.$field
    $p = Join-Path $repo $rel
    Assert-True (Test-Path -LiteralPath $p) "Missing upstream source: $rel"
    Write-Host "  [OK] $rel"
}

# -------------------------------------------------------------------------
# 2. Pinned content hashes
# -------------------------------------------------------------------------
Write-Host "`n[2] Pinned content hashes"

$u10CsvPath = Join-Path $repo ([string]$S.sources.u10_dependence_csv)
$u10Hash = (Get-FileHash -LiteralPath $u10CsvPath -Algorithm SHA256).Hash.ToLowerInvariant()
Assert-True ($u10Hash -eq ([string]$S.source_integrity.u10_dependence_csv_sha256).ToLowerInvariant()) 'U10 dependence CSV SHA256 mismatch.'
Write-Host "  [OK] U10 dependence CSV SHA256 = $u10Hash"

$u11ResultPath = Join-Path $repo ([string]$S.sources.u11_result)
$u11Hash = (Get-FileHash -LiteralPath $u11ResultPath -Algorithm SHA256).Hash.ToLowerInvariant()
Assert-True ($u11Hash -eq ([string]$S.source_integrity.u11_result_sha256).ToLowerInvariant()) 'U11 result SHA256 mismatch.'
Write-Host "  [OK] U11 result SHA256         = $u11Hash"

# -------------------------------------------------------------------------
# 3. U9B external composability stress test
# -------------------------------------------------------------------------
Write-Host "`n[3] U9B external composability"

$u9SummaryPath = Join-Path $repo ([string]$S.sources.u9b_summary)
$U9 = Get-Content -LiteralPath $u9SummaryPath -Raw | ConvertFrom-Json

Assert-Close ([double](100.0 * [double]$U9.relative_gain)) ([double]$S.preserve_u9b.pooled_observer_gain_pct) 1e-10 'U9B pooled gain mismatch.'
Assert-Close ([double]$U9.worst_state_regret) ([double]$S.preserve_u9b.worst_state_regret) 1e-12 'U9B worst regret mismatch.'
Assert-True ([string]$U9.decision -eq [string]$S.preserve_u9b.decision) 'U9B decision mismatch.'

$u9CompPath = Join-Path $repo ([string]$S.sources.u9b_composability)
$U9C = @(Import-Csv -LiteralPath $u9CompPath)
Assert-True ($U9C.Count -eq 4) 'U9B composability table must contain four budgets.'

for ($i=0; $i -lt 4; $i++) {
    $ref = $S.preserve_u9b.budget_rows[$i]
    Assert-Close ([double]$U9C[$i].budget) ([double]$ref.budget) 0.0 "U9B budget mismatch at row $i."
    Assert-Close ([double]$U9C[$i].scalar_gain_pct) ([double]$ref.fixed_scalar_gain_pct) 1e-12 "U9B scalar gain mismatch at row $i."
    Assert-Close ([double]$U9C[$i].observed_gain_pct) ([double]$ref.observed_adaptive_gain_pct) 1e-12 "U9B observed gain mismatch at row $i."
    Assert-Close ([double]$U9C[$i].xi_downward_pp) ([double]$ref.xi_downward_pp) 1e-12 "U9B Xi mismatch at row $i."
}

Write-Host ("  pooled observer gain = {0:+0.000;-0.000;0.000}%" -f [double]$S.preserve_u9b.pooled_observer_gain_pct)
Write-Host ("  decision             = {0}" -f [string]$S.preserve_u9b.decision)
Write-Host '  [OK] 4/4 budget-level composability rows match'

# -------------------------------------------------------------------------
# 4. U10 locked prospective verdict
# -------------------------------------------------------------------------
Write-Host "`n[4] U10 locked prospective result"

$u10PrimaryPath = Join-Path $repo ([string]$S.sources.u10_primary)
$U10P = Get-Content -LiteralPath $u10PrimaryPath -Raw | ConvertFrom-Json

Assert-True ([string]$U10P.primary_verdict -eq 'MECHANISM_NOT_CONFIRMED') 'U10 prospective verdict changed.'
Assert-True ([bool]$U10P.per_target_gate.georgia.per_target_gate_pass) 'Georgia U10 gate expected PASS.'
Assert-True (-not [bool]$U10P.per_target_gate.cpsc_2018.per_target_gate_pass) 'CPSC U10 gate expected FAIL.'
Assert-Close ([double]$U10P.pooled_strict_median_abs_coupling_reduction_pct) ([double]$S.preserve_u10_prospective.pooled_strict_median_abs_coupling_reduction_pct) 1e-10 'U10 strict pooled reduction mismatch.'
Assert-Close ([double]$U10P.pooled_crossfit_median_abs_coupling_reduction_pct) ([double]$S.preserve_u10_prospective.pooled_crossfit_median_abs_coupling_reduction_pct) 1e-10 'U10 crossfit pooled reduction mismatch.'

Write-Host '  primary verdict = MECHANISM_NOT_CONFIRMED'
Write-Host '  Georgia gate    = PASS'
Write-Host '  CPSC gate       = FAIL'

# -------------------------------------------------------------------------
# 5. Recompute the U10 HAC post-completion frontier from frozen CSV
# -------------------------------------------------------------------------
Write-Host "`n[5] U10 HAC post-completion recomputation"

$rows = @(Import-Csv -LiteralPath $u10CsvPath)
Assert-True ($rows.Count -eq 8) 'U10 dependence decomposition must contain 8 dataset-budget rows.'

$lambda = New-Object 'System.Collections.Generic.List[double]'
$wstar  = New-Object 'System.Collections.Generic.List[double]'
$meanW  = New-Object 'System.Collections.Generic.List[double]'
$xiExact = New-Object 'System.Collections.Generic.List[double]'
$xiPerm  = New-Object 'System.Collections.Generic.List[double]'
$xiHet   = New-Object 'System.Collections.Generic.List[double]'

foreach ($r in $rows) {
    $B = [double]$r.B
    $V = [double]$r.direct_mse
    Assert-True ($V -gt 0) 'U10 direct_mse must be positive.'

    $lam = ($B*$B)/$V
    $ws = 1.0/(1.0+$lam)

    $lambda.Add($lam)
    $wstar.Add($ws)
    $meanW.Add([double]$r.shared_constant_mean_weight)

    $xiExact.Add( ( [double]$r.shared_adaptive_mse - [double]$r.shared_constant_mean_mse ) / $V )
    $xiPerm.Add(  ( [double]$r.shared_permuted_weight_mse - [double]$r.shared_constant_mean_mse ) / $V )
    $xiHet.Add(   ( [double]$r.shared_tax_weight_heterogeneity ) / $V )
}

$lambdaArray = [double[]]$lambda.ToArray()
$wstarArray  = [double[]]$wstar.ToArray()
$meanWArray  = [double[]]$meanW.ToArray()
$wGlobal = 1.0 / (1.0 + (Mean-Double $lambdaArray))

$Hrows = New-Object 'System.Collections.Generic.List[double]'
$Arows = New-Object 'System.Collections.Generic.List[double]'

for ($i=0; $i -lt $rows.Count; $i++) {
    $onePlus = 1.0 + $lambdaArray[$i]
    $Hrows.Add($onePlus * [Math]::Pow($wstarArray[$i] - $wGlobal, 2.0))
    $Arows.Add($onePlus * [Math]::Pow($meanWArray[$i] - $wstarArray[$i], 2.0))
}

$H = Mean-Double ([double[]]$Hrows.ToArray())
$A = Mean-Double ([double[]]$Arows.ToArray())
$Cshared = Mean-Double ([double[]]$xiExact.ToArray())
$Cperm   = Mean-Double ([double[]]$xiPerm.ToArray())
$Crole   = Mean-Double ([double[]]$xiHet.ToArray())

$marginShared = $H - ($A + $Cshared)
$marginPerm   = $H - ($A + $Cperm)
$marginRole   = $H - ($A + $Crole)

Assert-Close $H ([double]$S.preserve_u10_hac_postcompletion.H) 5e-7 'U10 HAC H fingerprint mismatch.'
Assert-Close $A ([double]$S.preserve_u10_hac_postcompletion.A) 5e-7 'U10 HAC A fingerprint mismatch.'
Assert-Close $Cshared ([double]$S.preserve_u10_hac_postcompletion.C_shared) 5e-7 'U10 HAC C_shared fingerprint mismatch.'
Assert-Close $Cperm ([double]$S.preserve_u10_hac_postcompletion.C_permuted) 5e-7 'U10 HAC C_permuted fingerprint mismatch.'
Assert-Close $Crole ([double]$S.preserve_u10_hac_postcompletion.C_role_separated_prediction) 5e-7 'U10 HAC C_role fingerprint mismatch.'

Assert-True ($marginShared -lt 0.0) 'Shared adaptive HAC margin must be negative.'
Assert-True ($marginPerm -gt 0.0) 'Permuted HAC control margin must be positive.'
Assert-True ($marginRole -gt 0.0) 'Role-separated prediction HAC margin must be positive.'

Write-Host ("  H              = {0:F8}" -f $H)
Write-Host ("  A              = {0:F8}" -f $A)
Write-Host ("  C shared       = {0:F8}" -f $Cshared)
Write-Host ("  C permuted     = {0:F8}" -f $Cperm)
Write-Host ("  C role-sep     = {0:F8}" -f $Crole)
Write-Host ("  shared margin  = {0:+0.00000000;-0.00000000;0.00000000}" -f $marginShared)
Write-Host ("  perm margin    = {0:+0.00000000;-0.00000000;0.00000000}" -f $marginPerm)
Write-Host ("  role margin    = {0:+0.00000000;-0.00000000;0.00000000}" -f $marginRole)

# -------------------------------------------------------------------------
# 6. U11 information closure
# -------------------------------------------------------------------------
Write-Host "`n[6] U11 information closure"

$U11 = Get-Content -LiteralPath $u11ResultPath -Raw | ConvertFrom-Json
Assert-True ([string]$U11.primary_verdict -eq 'INFORMATION_CLOSURE_WITNESS_CONFIRMED') 'U11 verdict mismatch.'
Assert-True (-not [bool]$U11.source_outcomes_read) 'U11 source_outcomes_read must be false.'
Assert-True (-not [bool]$U11.true_u10_labels_used) 'U11 true_u10_labels_used must be false.'
Assert-True (-not [bool]$U11.retraining_performed) 'U11 retraining_performed must be false.'
Assert-True (-not [bool]$U11.reinference_performed) 'U11 reinference_performed must be false.'

foreach ($cohort in @('georgia','cpsc_2018')) {
    $c = $U11.cohorts.$cohort
    Assert-True ([bool]$c.construction.telemetry_byte_identity_claim) "$cohort telemetry identity failed."
    Assert-True ([bool]$c.construction.matched_prevalence) "$cohort prevalence matching failed."
    Assert-Close ([double]$c.world_plus.auc) 1.0 0.0 "$cohort WORLD+ AUC mismatch."
    Assert-Close ([double]$c.world_minus.auc) 0.0 0.0 "$cohort WORLD- AUC mismatch."
    Assert-Close ([double]$c.primary_auc_gap) 1.0 0.0 "$cohort AUC gap mismatch."
    Assert-True ([bool]$c.primary_success) "$cohort primary witness failed."
}

Write-Host '  primary verdict = INFORMATION_CLOSURE_WITNESS_CONFIRMED'
Write-Host '  Georgia         = same telemetry, AUC 1 vs 0'
Write-Host '  CPSC 2018       = same telemetry, AUC 1 vs 0'

# -------------------------------------------------------------------------
# Final result
# -------------------------------------------------------------------------
Write-Host "`n============================================================"
Write-Host ' FIGURE 5 FINAL-SYSTEM EVIDENCE: PASS'
Write-Host '============================================================'
Write-Host 'Interpretation boundary:'
Write-Host '  - U9/U10 show PRESERVE failure under shared adaptive use.'
Write-Host '  - U10 HAC post-completion controls cross H > A + C after shared dependence is removed.'
Write-Host '  - U10 prospective verdict remains MECHANISM_NOT_CONFIRMED.'
Write-Host '  - U11 confirms the IDENTIFY information-closure witness.'
Write-Host '  - MATLAB should now render these frozen GitHub results; it should not refreeze the science.'
