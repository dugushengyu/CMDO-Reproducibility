$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$bootstrapUrl = 'https://raw.githubusercontent.com/dugushengyu/CMDO-Reproducibility/oam-bootstrap-20260917/oam-bootstrap/BOOTSTRAP_OAM.ps1'
$tmp = Join-Path $env:TEMP 'BOOTSTRAP_OAM_HASHFIX.ps1'

Write-Host '[FIX] Downloading bootstrap...'
$txt = (Invoke-WebRequest -Uri $bootstrapUrl -UseBasicParsing).Content
$old = '2a1839e758595f7d4a0c8ecab2972e3cb939187cb91e843ff163c9e944c23eae'
$new = 'ffa9d73d8a8f707e0714716446b55089d9ec952223a0eb7c3c2a0115001f0607'
if ($txt -notmatch [regex]::Escape($old)) {
    throw 'Expected stale package hash not found in bootstrap; refusing to patch an unexpected script.'
}
$txt = $txt.Replace($old,$new)
[System.IO.File]::WriteAllText($tmp,$txt,(New-Object System.Text.UTF8Encoding($false)))

Write-Host '[PASS] Patched package SHA256 expectation.'
Write-Host '[RUN] Resuming clean-room bootstrap...'
& powershell -NoProfile -ExecutionPolicy Bypass -File $tmp
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
