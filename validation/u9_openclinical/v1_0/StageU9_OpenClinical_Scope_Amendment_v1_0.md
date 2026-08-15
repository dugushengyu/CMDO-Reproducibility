# Stage U9 Open Clinical — pre-outcome scope amendment v1.0

## Status

**Frozen before execution of U9A or U9B in this package.**

This amendment changes the manuscript-facing U9 validation route because the previously prepared eICU branch depends on credentialed data access that may not arrive on the manuscript schedule. No eICU reserve outcome is used by this amendment.

The existing eICU protocol, code and hashes remain preserved as historical pre-outcome evidence. They are not silently overwritten. eICU is reassigned to a deferred confirmatory multicentre replication role.

## New U9 hierarchy

### U9A — multicentre bridge / falsification

Dataset: UCI Heart Disease.

Centres:
- Cleveland — source;
- Hungary — external target;
- Switzerland — external target;
- VA Long Beach — external target.

U9A is a bridge and falsification test. It is not permitted to change any frozen U9B parameter after U9A results are observed.

### U9B — primary external-system reserve

Dataset: PhysioNet/Computing in Cardiology Challenge 2019 v1.0.0.

Official data provenance states that the public data are drawn from two hospital systems. Training set A is the source system; training set B is the external target system.

U9B is the claim-bearing external clinical-system test.

## Governance

The code, protocol, configuration, seeds, budgets, weight cap, outcome definition, preprocessing, model family, threshold rule, observer rule and success gates are sealed together before either branch is executed.

U9A results must not be used to tune U9B.

After first execution, subsequent reruns are reconstructions and must be labelled as such.

No failure may be converted into a pass by relaxing a budget, threshold, gate, seed, confidence level or transport-weight cap.
