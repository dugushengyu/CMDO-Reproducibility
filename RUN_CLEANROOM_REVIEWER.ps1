param(
    [string]$Workspace = "",
    [string]$Matlab = ""
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
Write-Host " CMDO SUBMISSION-V2 BUILD + CLEAN-ROOM REVIEWER TEST"
Write-Host " Static frozen-science audit + current 8-display MATLAB acceptance only"
Write-Host " Historical deep/full-claim/archival replay is not a reviewer requirement"
Write-Host "===================================================================================================="

Write-Host "`n[1/3] Build lean reviewer submission candidate"
& $py .\scripts\build_submission_candidate.py
if ($LASTEXITCODE -ne 0) { throw "Submission-v2 candidate build failed" }

$portable = Join-Path $repo "dist\CMDO-Reproducibility-Reviewer-Portable-v2.1.1.zip"
if (-not (Test-Path -LiteralPath $portable)) {
    throw "Portable reviewer package was not built: $portable"
}

$origin = (git remote get-url origin).Trim()
$ref = (git rev-parse HEAD).Trim()

Write-Host "`n[2/3] Fresh-clone stranger-style submission-v2 acceptance"
Write-Host "Clean-room workspace: $Workspace"

$cleanArgs = @(
    ".\scripts\run_cleanroom_reviewer_test.py",
    "--repository-url", $origin,
    "--ref", $ref,
    "--workspace", $Workspace,
    "--force"
)

if (-not [string]::IsNullOrWhiteSpace($Matlab)) {
    $cleanArgs += @("--matlab", $Matlab)
}

& $py @cleanArgs
if ($LASTEXITCODE -ne 0) { throw "Submission-v2 clean-room acceptance failed" }

Write-Host "`n[3/3] Final artifact inventory"
Get-ChildItem -LiteralPath (Join-Path $repo "dist") -File |
    Where-Object {
        $_.Name -like "CMDO-Reproducibility-Reviewer-Portable-v2.1.1*" -or
        $_.Name -like "CMDO-Submission-Candidate-v2.1.1*"
    } |
    Select-Object Name, Length, LastWriteTime

Write-Host ""
Write-Host "===================================================================================================="
Write-Host " CMDO SUBMISSION-V2 CLEAN-ROOM REVIEWER CANDIDATE: PASS"
Write-Host "===================================================================================================="
Write-Host "Canonical Git commit : $ref"
Write-Host "Clean-room workspace : $Workspace"
Write-Host "Report               : $(Join-Path $Workspace 'CMDO_CLEANROOM_REVIEWER_REPORT.json')"
Write-Host "Rendered figures     : $(Join-Path $Workspace 'rendered')"
Write-Host "Submission artifacts : $(Join-Path $repo 'dist')"
Write-Host "===================================================================================================="
