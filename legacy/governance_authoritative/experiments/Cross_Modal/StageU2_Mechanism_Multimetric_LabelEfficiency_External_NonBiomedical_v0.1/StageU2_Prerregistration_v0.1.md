# Stage U2 — Mechanism, Multimetric Scaling, Label Efficiency, and External Non-Biomedical Validation Preregistration v0.1

## Parent
Stage U0-U1 final scientific record:
`e18602ed16b242cfe5a220539ef46c525ca3c2f2046c16476afbaeb2cf8f5556`

## Primary questions
1. Is the medical direct-witness exponent 0.7164 explainable by ordinary finite-sample AUC estimation alone?
2. Does the medical evidence law improve sequential budget prediction over the root-n reference?
3. Does the evidence-scaling structure extend beyond biomedicine?
4. Do distinct performance functionals form one or more reproducible scaling regimes?
5. Does the frozen direct–transport fusion provide positive label leverage without external retuning?

## Mechanism kill tests
Score families:
- Gaussian
- Student-t with 3 degrees of freedom
- heteroscedastic Gaussian
- Gaussian mixture

Sampling protocols:
- balanced vs natural-prevalence witness
- independent vs nested budgets

Budgets:
8, 16, 32, 64, 128.

The observed medical exponent is considered not explained by the null panel only when it exceeds every preregistered null-cell 97.5th percentile.

## Medical label-efficiency gates
- Development and provider-separated median leverage at budget 32 must both exceed 1.5.
- Leave-one-target sequential-law MAE must improve over the root-n reference.

## External non-biomedical panel
- CIFAR-10 clean source/test environment
- CIFAR-10.1 v6 resampled test environment
- 12 CIFAR-10-C corruption families at severities 1, 3, and 5
- 38 total external target environments when acquisition succeeds

Binary task:
animals versus vehicles, frozen before external results.

Metrics:
- AUC
- AUPRC
- balanced accuracy
- Brier score
- log loss

## External gates
- Acquisition succeeds.
- AUC within-target fixed-effect collapse R² ≥ 0.80.
- External AUC exponent is within 0.15 of the frozen medical exponent or its bootstrap interval contains the medical exponent.
- Corruption-family holdout prediction improves on root-n.
- At least 3 performance functionals have within-target R² ≥ 0.75.
- Frozen 0.6 transport / 0.4 direct fusion has median leverage > 1 and positive leverage in at least 70% of budget-32 environments.

## Strong decision
Only all primary mechanism, medical, acquisition, scaling, holdout, and multimetric gates passing can yield:
`SEAL_STAGEU2_MECHANISM_AND_CROSS_DOMAIN_EVIDENCE_SCALING_SUPPORTED_AUTHORISE_NEW_RESERVE_FINAL_PREREGISTRATION_ONLY`

## Prohibitions
- No new blind access.
- No Stage 12.
- No tuning weights using external outcomes.
- No selection of DomainNet domains from observed performance.

