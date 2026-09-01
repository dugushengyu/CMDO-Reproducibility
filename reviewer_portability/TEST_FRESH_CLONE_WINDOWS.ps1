$ErrorActionPreference = 'Stop'

$Repo   = 'https://github.com/dugushengyu/CMDO-Reproducibility.git'
$Branch = 'codex/github-native-submission-20260901'
$Stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$Root   = Join-Path ([System.IO.Path]::GetTempPath()) ("CMDO_REVIEWER_E2E_" + $Stamp)

Write-Host '============================================================'
Write-Host ' CMDO FRESH-CLONE REVIEWER PORTABILITY TEST (Windows)'
Write-Host '============================================================'
Write-Host "Clone target: $Root"

& git clone --branch $Branch --single-branch $Repo $Root
if ($LASTEXITCODE -ne 0) { throw 'git clone failed.' }

$Matlab = $env:MATLAB_BIN
if ([string]::IsNullOrWhiteSpace($Matlab)) {
    $cmd = Get-Command matlab -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        throw 'MATLAB not found. Put matlab on PATH or set MATLAB_BIN to matlab.exe.'
    }
    $Matlab = $cmd.Source
}

$Escaped = $Root.Replace("'", "''")
$Batch = "cd('$Escaped'); RUN_REVIEWER_END_TO_END('Strict',true,'RunStressReplay',true)"

Write-Host "MATLAB: $Matlab"
& $Matlab -batch $Batch
if ($LASTEXITCODE -ne 0) { throw 'MATLAB reviewer end-to-end audit failed.' }

$Dirty = & git -C $Root status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'git status failed.' }
if (-not [string]::IsNullOrWhiteSpace(($Dirty -join "`n"))) {
    Write-Host $Dirty
    throw 'Fresh clone became Git-dirty.'
}

Write-Host ''
Write-Host '============================================================'
Write-Host ' FRESH GITHUB CLONE + END-TO-END AUDIT: PASS'
Write-Host ' Git clean: PASS'
Write-Host '============================================================'
Write-Host "Clone retained for inspection: $Root"
