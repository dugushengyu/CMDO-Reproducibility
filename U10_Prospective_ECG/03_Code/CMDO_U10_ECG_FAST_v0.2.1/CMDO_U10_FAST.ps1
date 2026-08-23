param(
    [ValidateSet("preseal","unseal","status","verify-local")]
    [string]$Phase = "preseal",
    [string]$Root = "$HOME\CMDO-U10-ECG",
    [int]$Workers = 48
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $scriptDir "cmdo_u10_physionet_fast_v02.py"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python 3 not found on PATH." }

# Probe 'requests' without letting Windows PowerShell turn Python stderr
# into a terminating NativeCommandError.
$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $python.Source -c "import requests" *> $null
$requestsOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldEap

if (-not $requestsOk) {
    Write-Host "[setup] Python package 'requests' is missing or broken."
    Write-Host "[setup] Installing/upgrading requests + urllib3..."
    & $python.Source -m pip install --user --upgrade requests urllib3
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requests/urllib3."
    }

    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $python.Source -c "import requests, urllib3; print('requests', requests.__version__, 'urllib3', urllib3.__version__)" 
    $requestsOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $oldEap
    if (-not $requestsOk) {
        throw "requests still cannot be imported after installation."
    }
}

Write-Host "============================================================"
Write-Host " CMDO U10 PHYSIONET FAST DOWNLOADER v0.2.1"
Write-Host " Phase   : $Phase"
Write-Host " Root    : $Root"
Write-Host " Workers : $Workers"
Write-Host "============================================================"

if ($Phase -eq "preseal") {
    & $python.Source $py preseal --root $Root --workers $Workers
}
elseif ($Phase -eq "status") {
    & $python.Source $py status --root $Root
}
elseif ($Phase -eq "verify-local") {
    & $python.Source $py verify-local --root $Root
}
elseif ($Phase -eq "unseal") {
    $seal = Join-Path $Root "SEALS\U10_PREOUTCOME_SEAL.json"
    if (-not (Test-Path -LiteralPath $seal)) {
        throw "Refusing to unseal: missing $seal"
    }
    & $python.Source $py unseal --root $Root --workers $Workers --seal $seal
}

if ($LASTEXITCODE -ne 0) {
    throw "FAST downloader exited with code $LASTEXITCODE"
}
