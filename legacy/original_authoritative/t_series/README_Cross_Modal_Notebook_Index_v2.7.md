# Cross-Modal Diagnostic Observability — Notebook Index v2.7

## Active notebook

**CrossModal_StageT4-FG_Dynamic_Direct_Transport_Fusion_MethodV3_v0.1_SELF_CONTAINED.ipynb**

Purpose: transparent development and provider-separated validation of Method v3. The notebook replaces static cross-target residual prediction with a development-calibrated convex fusion of frozen transport evidence and direct target-witness AUC, and validates the frozen rule across independent target environments and nested witness budgets.

Expected completion banner:

```text
========== STAGE T4-FG COMPLETE ==========
```

Expected result directory:

```text
06_Data_Records/Cross_Modal/StageT4-FG_Dynamic_Direct_Transport_Fusion_MethodV3_v0.1
```

## Frozen scope

- 21 independent target environments and 51 directed edges.
- 18 transparent development targets.
- 3 provider-separated targets excluded from weight calibration.
- Primary target-witness budget: 32.
- Dynamic checkpoints: 8, 16, 32, 64, 128.
- Direct-witness weight grid: 0.0 to 0.5 in steps of 0.1.
- Validation unit: target environment, not replicate row.

## Decision boundary

A strong result authorizes design of a new reserve only. It does not authorize access to a new blind reserve and does not authorize Stage 12. Stage T3-A remains failed and may not be reinterpreted.

## Retained prior notebooks

- Stage T4-DE: baseline-anchored multi-functional audit Method v2; sealed partial support.
- Stage T4-ABC: decomposed observability and Method v1; sealed theory support and method failure.

## Required parent records

The notebook verifies the sealed Stage T4-DE final record, the exact Stage T4-DE frozen RA-CB application, and the Stage T2-D, Stage T2-KR, Stage T2-L, and Stage T2-N multi-budget replicate ledgers before analysis.
