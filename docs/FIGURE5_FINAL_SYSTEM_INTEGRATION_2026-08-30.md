# Figure 5 final-system integration — 2026-08-30

## Decision

Do **not** redesign the final Figure 5 from the old U5F/U6/U7 stopping point. The final evidence chain now extends through U9/U10 PRESERVE analysis and U11 information closure.

GitHub remains the scientific source of truth. Local MATLAB is a rendering layer only.

## Canonical integration file

`source_data/figure5_final_system/CMDO_Figure5_Final_System_v1.0.json`

Verify locally with:

```powershell
Set-Location $HOME\CMDO-Reproducibility
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\scripts\verify_figure5_final_system.ps1
```

The renderer should not be frozen until this verifier returns `PASS`.

## Final scientific boundary

### U9B

The external-system reserve shows that a fixed-use/scalar benefit can be consumed under adaptive composition. The frozen U9B pooled observer gain is negative and the budget-level composability decomposition contains positive downward Xi terms.

### U10 prospective

The locked prospective primary verdict remains:

`MECHANISM_NOT_CONFIRMED`

Georgia passes the locked per-target criterion; CPSC 2018 does not. This result must remain visible in the manuscript claim boundary.

### U10 post-completion HAC mechanism

The post-completion decomposition yields:

- `H = 0.08614018`
- `A = 0.01403814`
- `C_shared = 0.21760208`
- `C_permuted = 0.03214915`
- `C_role_separated_prediction = 0.03136104`

Therefore:

- shared: `H-(A+C) = -0.14550004`
- permutation control: `H-(A+C) = +0.03995289`
- role-separated prediction: `H-(A+C) = +0.04074100`

The scientifically supported interpretation is that shared adaptive composition lies on the fixed-rule-preferable side of the HAC frontier, while post-completion removal of shared composition dependence reduces `C` sufficiently to cross the frontier. This is mechanism evidence, not prospective confirmation of generality.

### U11 information closure

U11 primary verdict:

`INFORMATION_CLOSURE_WITNESS_CONFIRMED`

Both Georgia and CPSC 2018 have constructed WORLD+ / WORLD- pairs with byte-identical telemetry, matched prevalence and AUC 1 versus 0. These are constructive identification witnesses only; they are not claims about the real clinical outcomes of those cohorts.

## Figure 5 implication

A final Figure 5 should therefore show the **full system endpoint**, not merely estimator benchmarking:

1. fixed-use benefit / reuse evidence,
2. adaptive benefit consumption under shared audit coupling,
3. the `H` versus `A+C` preserve frontier,
4. the information-closure/system-boundary endpoint where appropriate.

The final plotting design remains intentionally unfrozen until the integration bundle is verified locally.
