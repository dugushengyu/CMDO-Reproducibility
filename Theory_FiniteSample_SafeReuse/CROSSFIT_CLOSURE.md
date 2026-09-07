# Cross-fit closure — why symmetric cross-fitting does not remove full-budget dependence

Date: 2026-09-07

Status: exploratory theory result. No frozen CMDO/U10 artifact is modified.

## Question

Can ordinary symmetric two-fold cross-fitting escape the split-tax/coupling tension by letting each half choose the borrowing weight for the other half, while still using both halves in the final estimate?

## Setup

Let `D1=theta+e1` and `D2=theta+e2`, where `e1,e2` are iid, mean zero, with variance `V`. Let `H=theta+B` be a fixed historical value.

Let `W1=g(D1)` and `W2=g(D2)`, with the same measurable rule applied independently to the two folds. Define

`mu = E[W]`,

`q = E[W^2]`,

`a = E[W e]`.

The symmetric two-fold cross-fitted estimator is

`A_cf = 0.5 * { (1-W1)D2 + W1 H + (1-W2)D1 + W2 H }`.

Each weight is independent of the direct estimator it modifies. The fair current-only comparator is

`D_full = (D1+D2)/2`,

with risk `V/2`.

## Proposition CF1 — exact full-budget risk identity

The cross-fitted risk satisfies

`R(A_cf)-V/2`

`= 0.5 * { -2V mu + V q + B^2(q+mu^2) + a^2 + 2B(1-mu)a }`.

### Derivation

Write

`T1=(1-W1)e2+W1 B`,

`T2=(1-W2)e1+W2 B`,

so `A_cf-theta=(T1+T2)/2`.

Because `W1` is independent of `e2`,

`E[T1^2] = V(1-2mu+q)+B^2 q`,

and the same holds for `T2`.

For the cross term, independence of fold 1 and fold 2 gives

`E[T1 T2] = a^2 + 2B(1-mu)a + B^2 mu^2`.

Combining the terms yields the identity.

## Consequence

Foldwise role separation is not the same as aggregate independence.

The quantity

`a=E[W e]`

survives in the full cross-fitted risk because each fold is simultaneously:

- a decision sample for the opposite fold; and
- a direct-estimation component in the final aggregate.

Thus symmetric cross-fitting can reduce direct same-fold coupling, but it does **not** by itself produce a universal finite-sample no-harm guarantee against the full-data direct estimator.

## Bounded counterexample

Use the same bounded problem as the v2 magnitude-impossibility theorem:

- `theta=0.5`;
- `D=0.6` with probability `0.8` and `D=0.1` with probability `0.2`;
- `H=0.65`.

Then `V=0.04`, `B=0.15`, and every fixed convex weight `0<w<=1` toward `H` has lower MSE than the half-sample direct estimator.

Use the fold rule

- `W=1` when `D=0.6`;
- `W=0` when `D=0.1`.

For each fold separately, the weight is chosen from the opposite fold and is therefore independent of the estimator it modifies; conditional on the decision fold, the role-separated fold estimator is MSE non-inferior to its half-sample direct comparator.

Nevertheless, for the symmetric cross-fitted aggregate,

`R(A_cf)-R(D_full) = 29/5000 = 0.0058`.

Since `R(D_full)=V/2=0.02`,

`R(A_cf)=0.0258`,

which is a **29% risk increase** relative to full-data direct evaluation.

Therefore even a symmetric cross-fitted construction whose two foldwise estimators are individually protected relative to their own evaluation halves can be harmful after aggregation against the fair full-data direct comparator.

## Interpretation for CMDO

This closes one obvious escape route from the certifiability trilemma.

- Same-audit adaptation can be harmful because borrowing decisions depend on the estimation noise they modify.
- A one-way honest split restores independence but pays an explicit information tax.
- Symmetric two-fold cross-fitting reuses all observations, but the aggregate risk retains a dependence term because each observation serves both as a decision input and as part of the final direct estimate.

Cross-fitting may still be useful under additional orthogonality or moment restrictions; this proposition does **not** claim that all cross-fitted estimators are unsafe. It shows only that ordinary fold-swapping is not, by itself, a finite-sample safety theorem.

This is particularly relevant to the frozen U10 architecture, where cross-fitting reduced some coupling diagnostics but did not uniformly improve full-direct risk. The U10 evidence remains post-completion and is not used to validate this proposition prospectively.