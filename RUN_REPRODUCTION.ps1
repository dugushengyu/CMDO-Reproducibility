$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $repoRoot "RUN_REPRODUCTION.py") @args
