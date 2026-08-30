# Figure 5 final-system evidence bundle

This folder is the canonical integration layer for redesigning the final CMDO Figure 5 after the system evidence chain reached U10/U11.

## Purpose

The previous Figure 5 source material stopped too early in the scientific chain. The final manuscript logic is not only **REUSE** (U5F/U6/U7), but also **PRESERVE** (U9/U10) and the **IDENTIFY information-closure boundary** (U11).

`CMDO_Figure5_Final_System_v1.0.json` binds the frozen upstream results needed for that final design. It is an integration summary, not a new experiment and not a replacement for the underlying result files.

## Scientific chain

1. **REUSE** — frozen historical-evidence reuse and transfer evidence.
2. **PRESERVE** — U9/U10 show that fixed-use benefit need not survive shared adaptive composition.
3. **HAC frontier** — post-completion U10 decomposition uses the condition `H > A + C` to separate adaptive-worthwhile from fixed-rule-preferable regimes.
4. **IDENTIFY closure** — U11 constructs outcome worlds with byte-identical telemetry but opposite AUC, confirming that outcome-independent monitoring cannot identify current performance.

## Critical claim boundary

The U10 prospective primary verdict remains **`MECHANISM_NOT_CONFIRMED`**. Georgia passed the locked per-target gate and CPSC 2018 did not. The HAC result in the integration JSON is a **post-completion mechanism analysis** and must not be rewritten as prospective confirmation.

The U10 post-completion fingerprints are:

- `H = 0.08614018`
- `A = 0.01403814`
- `C_shared = 0.21760208`
- `C_permuted = 0.03214915`
- `C_role_separated_prediction = 0.03136104`
- `H-(A+C_shared) = -0.14550004`
- `H-(A+C_permuted) = +0.03995289`
- `H-(A+C_role_separated_prediction) = +0.04074100`

Thus the original shared-adaptive composition is on the wrong side of the HAC frontier, while removing shared composition dependence crosses the frontier in post-completion controls.

U11 is also deliberately bounded: its two constructed worlds are identification witnesses, **not** claims about the true clinical outcomes of Georgia or CPSC 2018.

## Canonical upstream files

- `source_data/figure6_u8_u9/U9B_summary.json`
- `source_data/figure6_admissibility/U9B_external_composability_decomposition.csv`
- `U10_Prospective_ECG/01_Prospective_Result/U10_PRIMARY_RESULT.json`
- `U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv`
- `U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.json`
- `U11_Information_Closure/01_Result/U11_INFORMATION_CLOSURE_RESULT_v0.1.json`
- `U11_Information_Closure/01_Result/U11_RESULT_SHA256_MANIFEST_v0.1.csv`

## Local workflow

GitHub remains the scientific source of truth. Local MATLAB is only the rendering layer.

After pulling the repository, verify this bundle in PowerShell:

```powershell
Set-Location $HOME\CMDO-Reproducibility
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\scripts\verify_figure5_final_system.ps1
```

Do not redesign or freeze the final Figure 5 until this verifier returns `PASS`.
