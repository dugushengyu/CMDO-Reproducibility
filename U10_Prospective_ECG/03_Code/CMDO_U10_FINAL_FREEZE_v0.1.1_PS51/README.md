# CMDO U10 Final Scientific Freeze v0.1.1 PS5.1

This package freezes U10 **before any manuscript reframing or further theory development**.

It does not alter the experiment. It verifies the already-established chain:
- PREOUTCOME seal
- locked evaluation spec
- prospective result
- two post-hoc diagnostic stages
- source model/split and target artifacts referenced by the PREOUTCOME seal

Then it creates a read-only evidence capsule containing:
- `SEALS/`
- `PRESEAL/`
- `UNSEAL/`
- locally used U10 code packages when found
- final chronology
- final evidence ledger
- SHA256 manifest

The large public `data/` tree is not duplicated into the capsule.

## Quick scientific freeze

```powershell
$zip = "$HOME\Downloads\CMDO_U10_FINAL_FREEZE_v0.1.zip"
$work = "$HOME\CMDO-U10-FINAL-FREEZE-v0.1"

Set-Location $HOME
if (Test-Path -LiteralPath $work) { Remove-Item $work -Recurse -Force }
Expand-Archive -LiteralPath $zip -DestinationPath $work -Force

$pkg = Join-Path $work "CMDO_U10_FINAL_FREEZE_v0.1"
Set-Location $pkg

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_FINAL_FREEZE.ps1" `
  -Root "$HOME\CMDO-U10-ECG"
```

## Deep raw-data hash seal (optional, slower)

Use this if you want SHA256 for every raw `.mat/.hea` file:

```powershell
powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_FINAL_FREEZE.ps1" `
  -Root "$HOME\CMDO-U10-ECG" `
  -DeepDataHash
```

The scientific rule after freezing is simple: do not edit U10 frozen artifacts in place.
Any future analysis must go into a new versioned post-hoc/theory directory.


## v0.1.1 compatibility fix

The scientific freeze logic is unchanged.

This patch only replaces the .NET Core method
`[System.IO.Path]::GetRelativePath()` with a `System.Uri`-based helper that works in
Windows PowerShell 5.1 / .NET Framework.

The failed v0.1 run stopped immediately after the first hash verification and did not
modify U10 scientific artifacts. v0.1.1 creates a new timestamped freeze directory.
