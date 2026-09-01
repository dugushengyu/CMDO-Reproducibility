# Controlled AUC stress-test reconstruction — 2026-09-01

The original local `CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA.py` used for the 2026-08-31 post-completion stress run is no longer available. The new script `scripts/CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py` is explicitly a **faithful reconstruction**, not a byte-identical recovery.

It uses two frozen authorities: the final manuscript-locked stress design and the frozen Stage-U5E pair-complete observer formulas/hyperparameters. The locked design is true AUCs 0.55/0.65/0.75; balanced budgets 8/16/32/64/128; 500 deterministic direct-variance calibrations per AUC-budget pair; Lambda 0/0.25/0.50/0.75/1/1.5/2/4; both mismatch directions for nonzero Lambda; 225 states per method; 200 deterministic replicates per state. U5E constants retained include `DELTA_BLOCK=0.025`, `MAX_WEIGHT=0.35`, and `RISK_COEFFICIENT=8`, with pair-complete AA/AB/BA/BB and opposite-block sensor logic.

The reconstruction writes `CMDO_SystemStress_AUC_StateSummary_v1_1.csv`, the schema consumed by the dense-Lambda MATLAB Figure-5 renderer. It must not be used to rewrite historical provenance of the original 2026-08-31 run. Before a new submission tag replaces any historical frozen stress result, compare the regenerated output against the original frozen summary/hash if that artifact is available.

Run on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.ps1
```

This remains a post-completion comparator analysis, not prospective confirmation or observer tuning.
