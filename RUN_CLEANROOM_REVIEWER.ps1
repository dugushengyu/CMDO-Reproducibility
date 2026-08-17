param(
    [string]$Workspace = "",
    [switch]$SkipNetwork,
    [switch]$SkipEnvironmentInstall,
    [switch]$SkipFrozen,
    [switch]$SkipMatlab
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
Set-Location $repo

if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    if (-not [string]::IsNullOrWhiteSpace($env:SystemDrive)) {
        $Workspace = "$($env:SystemDrive)\CMDO-CR-$stamp"
    }
    else {
        $Workspace = Join-Path $HOME "CMDO-CR-$stamp"
    }
}

$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $cmd = Get-Command python -ErrorAction Stop
    $py = $cmd.Source
}

Write-Host "===================================================================================================="
Write-Host " CMDO FINAL SUBMISSION BUILD + CLEAN-ROOM REVIEWER TEST"
Write-Host " Fresh clone; exact reviewer assets; new venv by default"
Write-Host " Windows clone path policy: short workspace + core.longpaths=true"
Write-Host "===================================================================================================="

Write-Host "`n[1/3] Build final submission candidate artifacts"
& $py .\scripts\build_submission_candidate.py
if ($LASTEXITCODE -ne 0) { throw "Submission candidate build failed" }

$asset = Join-Path $repo "dist\CMDO-Reviewer-Assets-v1.0.zip"
if (-not (Test-Path -LiteralPath $asset)) { throw "Reviewer asset bundle was not built: $asset" }

$origin = (git remote get-url origin).Trim()
$ref = (git rev-parse HEAD).Trim()

Write-Host "`n[2/3] Run stranger-style clean-room clone/reproduction"
Write-Host "Clean-room workspace: $Workspace"
$cleanArgs = @(
    ".\scripts\run_cleanroom_reviewer_test.py",
    "--repository-url", $origin,
    "--ref", $ref,
    "--asset-bundle", $asset,
    "--workspace", $Workspace,
    "--force"
)
if (-not $SkipNetwork) { $cleanArgs += "--allow-network" } else { $cleanArgs += "--skip-smoke" }
if ($SkipEnvironmentInstall) { $cleanArgs += "--skip-environment-install" }
if ($SkipFrozen) { $cleanArgs += "--skip-frozen" }
if ($SkipMatlab) { $cleanArgs += "--skip-matlab" }

& $py @cleanArgs
if ($LASTEXITCODE -ne 0) { throw "Clean-room reviewer acceptance failed" }

Write-Host "`n[3/3] Final artifact inventory"
Get-ChildItem -LiteralPath (Join-Path $repo "dist") -File |
    Where-Object { $_.Name -like "CMDO-*v1.0*" -or $_.Name -like "CMDO-Submission-Candidate-v1.0*" } |
    Select-Object Name, Length, LastWriteTime

Write-Host ""
Write-Host "===================================================================================================="
Write-Host " CMDO FINAL CLEAN-ROOM REVIEWER CANDIDATE: PASS"
Write-Host "===================================================================================================="
Write-Host "Canonical Git commit : $ref"
Write-Host "Clean-room workspace : $Workspace"
Write-Host "Report               : $(Join-Path $Workspace 'CMDO_CLEANROOM_REVIEWER_REPORT.json')"
Write-Host "Submission artifacts : $(Join-Path $repo 'dist')"
Write-Host "===================================================================================================="
