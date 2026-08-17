# Final Figure 5/6 reproducibility audit — 17 August 2026

## Scope

The current manuscript Figure 5 and Figure 6 are now sealed renderers. They do not read any scientific input from `Downloads`, a manuscript working folder, Google Drive, or another machine-specific path at render time.

This design deliberately separates two questions:

1. **Can a reviewer regenerate the exact manuscript figures from frozen derived results?** Yes: `Figure5.m` and `Figure6.m` embed the frozen values needed for rendering and run without external scientific input files.
2. **Does this by itself constitute a fresh raw-to-science replay of U8/U9?** No. The sealed render path reproduces the frozen manuscript figures and audits their numerical identities. It does not relabel the deeper historical/restricted-data replay as fresh prospective reproduction.

## Current main-figure files

- `matlab/figures/main/Figure5.m` — U8 temporal reserve, U9A multicentre bridge/falsification, U9B external reserve.
- `matlab/figures/main/Figure6.m` — evidence-admissibility theory, state-level theory/observation synthesis, U9B composability displacement, and strict-split mechanistic control.

Both renderers honor `CMDO_OUTPUT_ROOT` in reviewer batch mode and therefore write into the same `figures/main` output tree as Figure 4. In interactive use they fall back to the existing CMDO configuration when available.

## Figure 5 audit trail

Figure 5 keeps its final U8/U9A/U9B derived values embedded in the MATLAB source. The independent audit checks those values against the already tracked source records under `source_data/figure6_u8_u9/`:

- U8: 12 temporal budget-cycle states;
- U9A: three target-centre summaries;
- U9B: four audit-budget states and frozen summary metrics.

The runtime renderer does not read those files; they exist to make the embedded values independently auditable.

## Figure 6 audit trail

The exact 185-state synthesis table is retained at:

`source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv`

The originating full 26-column table had frozen identity:

`SHA-256 a0ad0c9f9feded26b9b32f732ae62d7639d5ff91be983cb54a04525b0efc6d03`

The Git-tracked six-column audit extract contains exactly the columns consumed by Figure 6 and has SHA-256:

`4ef09304a0dbb4110130b9543b05bd8a7d0f34f22dd0ecef1cb6ef758c6174c4`

State composition:

- U6: 80
- U7: 80
- U8: 12
- U9A: 9
- U9B: 4
- total: 185

The audit independently reconstructs the scalar identities and checks:

- max Psi reconstruction error < 1e-12;
- max scalar-risk-ratio reconstruction error < 1e-12;
- Spearman rho(log10 Lambda, observed MSE gain) = -0.5610382472233805;
- Spearman rho(scalar prediction, observed MSE gain) = +0.5875990296046397.

Panel-c and panel-d audit companions are also tracked under `source_data/figure6_admissibility/`. The strict-split analysis remains explicitly post-hoc mechanistic evidence; it does not change the frozen U9B verdict.

## Machine-readable seal

`provenance/final_figure56_seal.json` records SHA-256 and byte size for the two final MATLAB renderers and the 185-state synthesis table, plus the expected scientific summary invariants.

## Reviewer audit command

Run:

```bash
python scripts/audit_final_figure56.py
```

Expected final line:

```text
=== CMDO FINAL FIGURE 5/6 AUDIT PASS ===
```

The standard reviewer commands call this audit automatically after the repository update described here.

## Reviewer rendering path

After canonical assets are installed, the normal frozen route remains:

```bash
python RUN_REVIEWER.py frozen
```

or the one-command standard route:

```bash
python RUN_REVIEWER.py all --allow-network
```

`RUN_ALL_FIGURES.m` now invokes the current `Figure5()` and `Figure6()` directly rather than the superseded U6/U7 and U8/U9 legacy main-figure wrappers.
