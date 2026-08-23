param(
  [string]$Root = "$HOME\CMDO-U10-ECG",
  [string]$FastPkg = "$HOME\CMDO-U10-FAST-v0.2.1\CMDO_U10_ECG_FAST_v0.2.1",
  [int]$Workers = 64
)

$ErrorActionPreference = "Stop"
$ExpectedSeal = "efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949"
$ExpectedSpec = "25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$specSource = Join-Path $scriptDir "U10_LOCKED_EVALUATION_SPEC_v0.1.json"
$evalPy = Join-Path $scriptDir "CMDO_U10_EVALUATE_v01.py"
$seal = Join-Path $Root "SEALS\U10_PREOUTCOME_SEAL.json"
$unsealDir = Join-Path $Root "UNSEAL"
$lockedSpec = Join-Path $unsealDir "U10_LOCKED_EVALUATION_SPEC_v0.1.json"
$marker = Join-Path $unsealDir "U10_UNSEAL_STARTED.json"

Write-Host "============================================================"
Write-Host " CMDO U10 ONE-SHOT UNSEAL + PROSPECTIVE EVALUATION v0.1.1 RESUMABLE"
Write-Host "============================================================"

if (-not (Test-Path -LiteralPath $seal)) { throw "Missing pre-outcome seal: $seal" }
$sealHash = (Get-FileHash -LiteralPath $seal -Algorithm SHA256).Hash.ToLower()
if ($sealHash -ne $ExpectedSeal) {
    throw "PREOUTCOME SEAL HASH MISMATCH. Expected $ExpectedSeal, got $sealHash"
}
Write-Host "[1] PREOUTCOME seal verified: $sealHash"

$specHash = (Get-FileHash -LiteralPath $specSource -Algorithm SHA256).Hash.ToLower()
if ($specHash -ne $ExpectedSpec) {
    throw "Bundled evaluation spec hash mismatch. Expected $ExpectedSpec, got $specHash"
}
New-Item -ItemType Directory -Force -Path $unsealDir | Out-Null
Copy-Item -LiteralPath $specSource -Destination $lockedSpec -Force
Write-Host "[2] Locked evaluation spec copied BEFORE target unseal: $specHash"

if (Test-Path -LiteralPath $marker) {
    $m = Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json
    if ($m.preoutcome_seal_sha256 -ne $sealHash -or $m.locked_evaluation_spec_sha256 -ne $specHash) {
        throw "Existing UNSEAL marker does not match the current seal/spec."
    }
    Write-Host "[3] Existing matching one-shot marker found; resuming the SAME unseal run."
}
else {
    $markerObj = [ordered]@{
        schema = "CMDO_U10_UNSEAL_STARTED_v0.1.1"
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        preoutcome_seal_sha256 = $sealHash
        locked_evaluation_spec_sha256 = $specHash
        statement = "This marker was written before Georgia/CPSC target headers were downloaded."
    }
    $markerObj | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $marker -Encoding UTF8
    Write-Host "[3] One-shot marker written BEFORE target labels."
}

$fastScript = Join-Path $FastPkg "CMDO_U10_FAST.ps1"
if (-not (Test-Path -LiteralPath $fastScript)) {
    throw "FAST downloader not found: $fastScript"
}

Write-Host "[4] UNSEAL: downloading Georgia/CPSC .hea target headers (resumable)."
$geoHea = 0
$cpsHea = 0
for ($attempt = 1; $attempt -le 30; $attempt++) {
    Write-Host "    attempt $attempt / 30"
    try {
        powershell -ExecutionPolicy Bypass -File $fastScript `
            -Phase unseal `
            -Root $Root `
            -Workers $Workers
    }
    catch {
        Write-Host "    downloader returned an error; completed files are retained and the same one-shot run will continue."
    }

    $geoHea = (Get-ChildItem "$Root\data\georgia" -Recurse -File -Filter *.hea -ErrorAction SilentlyContinue | Measure-Object).Count
    $cpsHea = (Get-ChildItem "$Root\data\cpsc_2018" -Recurse -File -Filter *.hea -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "    current target headers: Georgia=$geoHea / 10344 ; CPSC=$cpsHea / 6877"

    if ($geoHea -eq 10344 -and $cpsHea -eq 6877) {
        break
    }
}

Write-Host "[5] Target header counts: Georgia=$geoHea CPSC=$cpsHea"
if ($geoHea -ne 10344 -or $cpsHea -ne 6877) {
    throw "Incomplete target-header unseal after 30 resumable attempts. Re-run this SAME v0.1.1 package; the matching marker permits continuation."
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python not found." }

Write-Host "[6] Running the already-locked prospective evaluation."
& $python.Source $evalPy --root $Root --spec $lockedSpec
if ($LASTEXITCODE -ne 0) { throw "Prospective evaluation failed with code $LASTEXITCODE" }
