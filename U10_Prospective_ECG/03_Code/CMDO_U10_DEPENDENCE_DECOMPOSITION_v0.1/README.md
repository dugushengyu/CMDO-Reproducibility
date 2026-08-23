# CMDO U10 post-hoc dependence decomposition v0.1

This is explicitly exploratory and cannot replace the locked U10 prospective verdict.

The previous diagnostic showed:
- oracle fixed borrowing is beneficial at all eight target-budget cells;
- full-m and FPC variance recalibration do **not** restore the lost large-budget gains.

This package therefore asks whether the failure is caused by the *joint dependence* between
adaptive weights and audit error rather than by the average weight alone.

It computes:

1. **constant-mean-weight control** — preserves the observed average amount of borrowing but
   removes weight randomness;
2. **permuted-weight control** — preserves the full marginal distribution of adaptive weights
   but breaks their replicate-by-replicate pairing with audit error;
3. **exact shared adaptation-tax decomposition** into:
   - weight heterogeneity;
   - weight/error-magnitude covariance;
   - directional weight/error dependence;
4. **disjoint-half dependence** versus the exact finite-population correlation
   `-h/(N-h)`;
5. **independent-fold mechanistic control** — draws A and B independently from the finite target
   frame (overlap allowed). This is *not* an audit-budget-preserving deployment design; it exists
   only to isolate dependence created by disjoint sampling without replacement.

Interpretation:

- constant-mean positive, adaptive negative -> adaptation itself is the problem;
- permuted positive, adaptive negative -> weight-error pairing is the dominant problem;
- independent-fold improves strongly -> finite-population disjoint-fold dependence is implicated;
- all controls remain negative -> the problem is more basic than dependence and the direction
  should be killed.

Run:

```powershell
$zip  = "$HOME\Downloads\CMDO_U10_DEPENDENCE_DECOMPOSITION_v0.1.zip"
$work = "$HOME\CMDO-U10-DEPENDENCE-v0.1"
Set-Location $HOME
if (Test-Path -LiteralPath $work) { Remove-Item $work -Recurse -Force }
Expand-Archive -LiteralPath $zip -DestinationPath $work -Force
$pkg = Join-Path $work "CMDO_U10_DEPENDENCE_DECOMPOSITION_v0.1"
Set-Location $pkg

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_DEPENDENCE_DECOMPOSITION.ps1" `
  -Root "$HOME\CMDO-U10-ECG"
```
