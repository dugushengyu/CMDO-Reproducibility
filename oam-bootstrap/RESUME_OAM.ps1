$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$owner = 'dugushengyu'
$repo  = 'MelaninAnchored-DeltaMap-Reproducibility'
$repoFull = "$owner/$repo"
$gh = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'
if (-not (Test-Path $gh)) { throw "GitHub CLI not found at $gh" }

Write-Host '[AUTH] Checking local GitHub CLI login...'
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $gh auth status *> $null
$loggedIn = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldEap

if (-not $loggedIn) {
    Write-Host '[AUTH] Browser login will open. Complete GitHub login, then return here.'
    & $gh auth login --web --git-protocol https
    if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI login failed.' }
}

Write-Host '[GITHUB] Ensuring private reproducibility repo exists...'
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $gh repo view $repoFull *> $null
$repoExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldEap

if (-not $repoExists) {
    & $gh repo create $repoFull --private --description 'Melanin-anchored Delta-map OAM reproducibility pipeline'
    if ($LASTEXITCODE -ne 0) { throw 'Could not create private GitHub repo.' }
}

$bootstrapUrl = 'https://raw.githubusercontent.com/dugushengyu/CMDO-Reproducibility/oam-bootstrap-20260917/oam-bootstrap/BOOTSTRAP_OAM.ps1'
$bootstrap = Join-Path $env:TEMP 'BOOTSTRAP_OAM.ps1'
Invoke-WebRequest -Uri $bootstrapUrl -OutFile $bootstrap -UseBasicParsing

Write-Host '[RUN] Authentication/repo prerequisites satisfied. Restarting bootstrap...'
& powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap
exit $LASTEXITCODE
