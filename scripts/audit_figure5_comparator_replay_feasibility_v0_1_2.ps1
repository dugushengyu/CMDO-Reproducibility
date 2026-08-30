param(
    [string]$CanonicalDir = ""
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$pyScript = Join-Path $PSScriptRoot 'audit_figure5_comparator_replay_feasibility_v0_1_2.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing Python audit script: $pyScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python not found on PATH.'
}

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 COMPARATOR-REPLAY FEASIBILITY AUDIT v0.1.2'
Write-Host ' gzip-safe + corrected U7 frozen schema'
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

Write-Host "`n[1] Running corrected feasibility audit"
& $python.Source @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Comparator replay feasibility audit v0.1.2 failed with code $LASTEXITCODE"
}

$outDir = Join-Path $repo 'source_data\figure5_final_system\comparator_replay_feasibility'
$csvPath = Join-Path $outDir 'CMDO_Figure5_Comparator_Replay_Feasibility_v0.1.2.csv'
$jsonPath = Join-Path $outDir 'CMDO_Figure5_Comparator_Replay_Feasibility_v0.1.2.json'

foreach ($p in @($csvPath,$jsonPath)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Expected audit output missing: $p"
    }
}

Write-Host "`n[2] Feasibility table"
Import-Csv -LiteralPath $csvPath |
    Select-Object regime,targets_or_strata,per_example_scores_and_outcomes,transport_descriptors,completed_replicate_record,score_hashes_for_reconstruction,pipeline_route_present,replay_state,next_action |
    Format-Table -AutoSize

$J = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json

Write-Host "`n[3] Compact result"
Write-Host ("  Overall : {0}" -f [string]$J.overall)
foreach ($r in $J.regimes) {
    Write-Host ("  {0,-29} : {1}" -f [string]$r.regime,[string]$r.replay_state)
}

Write-Host "`nInterpretation boundary:"
Write-Host '  - This audit does not run any new comparator.'
Write-Host '  - U5 exact replay requires frozen per-example scores/labels and transport descriptors.'
Write-Host '  - U6/U7 reconstruction is acceptable only if every regenerated score hash exactly matches the frozen pre-outcome hash.'
Write-Host '  - Any U6/U7 comparator replay would be explicitly post-completion, not prospective.'
Write-Host '  - Frozen CMDO U6/U7 prospective results remain unchanged.'

Write-Host "`nGenerated local files:"
Write-Host "  $csvPath"
Write-Host "  $jsonPath"

Write-Host "`nGit status:"
git status --short
