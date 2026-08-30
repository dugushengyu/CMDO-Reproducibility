param(
    [ValidateSet('U6','U7','Both')]
    [string]$Stage = 'Both',
    [string]$CanonicalDir = '',
    [string]$CacheDir = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$pyScript = Join-Path $PSScriptRoot 'reconstruct_figure5_u6_u7_hash_locked.py'
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing reconstruction script: $pyScript"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python not found on PATH.'
}

Write-Host '============================================================'
Write-Host ' CMDO FIGURE 5 HASH-LOCKED U6/U7 RECONSTRUCTION'
Write-Host ' no comparator; exact frozen score hashes required'
Write-Host '============================================================'
Write-Host "Repository : $repo"
Write-Host "Stage      : $Stage"
if ($CanonicalDir) {
    Write-Host "Canonical  : $CanonicalDir"
} else {
    Write-Host 'Canonical  : auto-resolve from CMDO config/environment'
}
if ($CacheDir) {
    Write-Host "Cache      : $CacheDir"
} else {
    Write-Host 'Cache      : %LOCALAPPDATA%\CMDO\figure5_hash_locked_reconstruction'
}

$argsList = @(
    $pyScript,
    '--repo', $repo,
    '--stage', $Stage
)
if ($CanonicalDir) {
    $argsList += @('--canonical-dir', $CanonicalDir)
}
if ($CacheDir) {
    $argsList += @('--cache-dir', $CacheDir)
}

Write-Host "`n[1] Running reconstruction audit"
Write-Host 'NOTE: U6 may download MedMNIST, CIFAR-10 and ACS public data on first run.'
Write-Host '      U7 downloads the UCI Diabetes 130-US Hospitals public dataset.'
& $python.Source @argsList
$code = $LASTEXITCODE

$outDir = Join-Path $repo 'source_data\figure5_final_system\comparator_reconstruction'
$auditCsv = Join-Path $outDir 'CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.csv'
$auditJson = Join-Path $outDir 'CMDO_Figure5_Hash_Locked_Reconstruction_Audit_v0.1.json'

if (Test-Path -LiteralPath $auditCsv) {
    Write-Host "`n[2] Reconstruction audit table"
    Import-Csv -LiteralPath $auditCsv |
        Select-Object stage,family,target_or_stratum,n,score_hash_match,membership_hash_match,label_count_match,truth_match,transport_descriptor_match,passed |
        Format-Table -AutoSize
}

if (Test-Path -LiteralPath $auditJson) {
    $J = Get-Content -LiteralPath $auditJson -Raw | ConvertFrom-Json
    Write-Host "`n[3] Compact result"
    Write-Host ("  Overall : {0}" -f [string]$J.status)
    Write-Host ("  U6      : {0}" -f [string]$J.stage_status.U6)
    Write-Host ("  U7      : {0}" -f [string]$J.stage_status.U7)
    if ($J.generated_reconstruction_files.U6) {
        Write-Host ("  U6 file : {0}" -f [string]$J.generated_reconstruction_files.U6)
    }
    if ($J.generated_reconstruction_files.U7) {
        Write-Host ("  U7 file : {0}" -f [string]$J.generated_reconstruction_files.U7)
    }
}

Write-Host "`nInterpretation boundary:"
Write-Host '  - No U-stat / DeLong / Plug-in comparator is run here.'
Write-Host '  - Exact score SHA256 equality is required; approximate numerical agreement is insufficient.'
Write-Host '  - U7 row-membership SHA256 must also match exactly.'
Write-Host '  - Any later U6/U7 comparator replay is post-completion, never prospective.'
Write-Host '  - Frozen CMDO U6/U7 prospective records remain unchanged.'

Write-Host "`nGit status:"
git status --short

if ($code -ne 0) {
    throw "Hash-locked reconstruction audit did not pass (exit code $code). Review the mismatch/package output above."
}
