# CMDO U10 post-hoc failure diagnostics v0.1

This package is explicitly **post-hoc exploratory analysis**. It does not modify or reinterpret
the locked U10 prospective verdict (`MECHANISM_NOT_CONFIRMED`).

It first verifies the exact hashes of:
- PREOUTCOME seal
- locked evaluation specification
- prospective result CSV
- prospective result JSON

Then it asks why the prospective mechanism test failed.

The main exploratory hypothesis is **variance-calibration mismatch in cross-fitting**:
the original cross-fit weight was learned on a half sample using the half-sample variance,
but the final cross-fit estimator averages both orientations and therefore has a full-budget
noise scale. Two post-hoc variants rescale the variance term to the final estimator:
1. FULLM
2. FULLM + finite-population correction

An oracle fixed-weight benchmark is included only to ask whether historical borrowing is
beneficial in principle; it is not deployable because it uses the true target accuracy.

Run:

```powershell
$zip  = "$HOME\Downloads\CMDO_U10_POSTHOC_FAILURE_DIAGNOSTICS_v0.1.zip"
$work = "$HOME\CMDO-U10-POSTHOC-v0.1"
Set-Location $HOME
if (Test-Path -LiteralPath $work) { Remove-Item $work -Recurse -Force }
Expand-Archive -LiteralPath $zip -DestinationPath $work -Force
$pkg = Join-Path $work "CMDO_U10_POSTHOC_FAILURE_DIAGNOSTICS_v0.1"
Set-Location $pkg

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_POSTHOC_FAILURE_DIAGNOSTICS.ps1" `
  -Root "$HOME\CMDO-U10-ECG"
```
