# Draft non-oracle finite-sample certificate

This note strengthens the baseline role-separated identity into a **data-derived high-probability safety certificate** and makes the full-budget split tax explicit.

## Theorem C: confidence-set safe reuse

Let `S` be a decision sample and let `D` be a direct estimator computed from an evaluation sample independent of `S`.

Assume:

1. `E[D | theta] = theta`;
2. the finite-sample variance of `D` is a known function `V(theta) > 0` for the claimed evaluation design;
3. `H` is a fixed completed historical estimate;
4. from `S`, construct a confidence set `C_alpha(S)` satisfying

   `P_theta[theta in C_alpha(S)] >= 1-alpha`;

5. define

   `Lambda_U(S) = sup_{t in C_alpha(S)} (H-t)^2 / V(t)`;

6. choose an adaptive weight `W(S)` satisfying

   `0 <= W(S) <= min(1, 2/(1+Lambda_U(S)))`.

Define

`A = (1-W(S))D + W(S)H`.

Then, with probability at least `1-alpha` over the decision sample `S`,

`E[(A-theta)^2 | S] <= V(theta)`.

### Proof

On the confidence event `theta in C_alpha(S)`,

`(H-theta)^2 / V(theta) <= Lambda_U(S)`.

Conditional on `S`, the weight `W(S)` is fixed and independent of evaluation noise. Therefore

`E[(A-theta)^2 | S]`

`= (1-W)^2 V(theta) + W^2(H-theta)^2`

`<= V(theta)[(1-W)^2 + W^2 Lambda_U]`.

The bracket is at most one whenever

`W <= 2/(1+Lambda_U)`.

The confidence event occurs with probability at least `1-alpha`.

### Interpretation

This is an exact finite-sample **conditional** no-harm certificate. It is not an unconditional MSE dominance theorem because the confidence event can fail with probability `alpha`.

For a bounded performance quantity and bounded estimator, the failure event can be converted into an additive PAC-style unconditional excess-risk bound, but that extension must be stated separately.

---

## Corollary C1: bounded accuracy / Bernoulli mean

For an independent evaluation sample of size `m_e` under an iid Bernoulli model,

`V(t) = t(1-t)/m_e`.

For a finite population of size `N` evaluated by simple random sampling without replacement,

`V(t) = t(1-t)(N-m_e) / [m_e(N-1)]`.

For either form, the ratio

`(H-t)^2 / V(t)`

is a positive constant times

`(H-t)^2 / [t(1-t)]`.

On an interval `C=[L,U]` strictly inside `(0,1)`, the supremum occurs at an endpoint, so

`Lambda_U = max{ (H-L)^2/V(L), (H-U)^2/V(U) }`.

If the confidence set reaches a zero-variance boundary (`L=0` or `U=1`), the conservative certificate sets `Lambda_U = infinity`, forcing `W=0`.

Thus an exact or conservative finite-sample confidence interval for current accuracy can be converted directly into a safe borrowing cap without revealing target truth.

---

# Theorem D: full-budget direct comparator and split-tax feasibility

Theorem C compares reuse against direct evaluation using the **evaluation sample only**. If a separate decision sample consumes outcome budget, the relevant benchmark may instead be direct evaluation using the entire budget.

Let

- `V_e(theta)` be direct-estimation variance using the evaluation sample;
- `V_f(theta) < V_e(theta)` be direct-estimation variance using the full outcome budget;
- `Lambda_U` be a valid upper bound on `(H-theta)^2 / V_e(theta)` on the confidence event.

Conditional on the decision sample, a sufficient worst-case condition for

`E[(A-theta)^2 | S] <= V_f(theta)`

is

`W[2 - (1+Lambda_U)W] >= delta`,

where

`delta = 1 - V_f(theta)/V_e(theta)`

is the fractional split tax relative to the evaluation-only variance.

## Feasibility condition

The left-hand side is a concave quadratic with maximum

`1/(1+Lambda_U)`.

Therefore a finite-sample certificate against **full-budget direct evaluation exists only if**

`delta <= 1/(1+Lambda_U)`.

If this condition fails, no weight can be certified against the full-budget direct comparator using only the stated mismatch bound.

When it holds, the certified weight interval is

`W_- <= W <= W_+`,

with

`W_± = [1 ± sqrt(1 - (1+Lambda_U)delta)] / (1+Lambda_U)`.

This is qualitatively different from the usual upper-cap result: once a decision sample creates a split tax, safe reuse may require **enough borrowing to pay the tax but not so much that historical mismatch dominates**.

---

## Corollary D1: iid accuracy with a fixed total outcome budget

Let the total outcome budget be `M`, split into

- decision budget `m_d`;
- evaluation budget `m_e = M-m_d`.

Under iid Bernoulli accuracy,

`V_f/V_e = m_e/M`,

so

`delta = m_d/M`.

Hence full-budget safety is certifiable only if

`m_d/M <= 1/(1+Lambda_U)`.

The decision sample therefore creates a genuine design trade-off:

- larger `m_d` can tighten the confidence set and reduce `Lambda_U`;
- larger `m_d` also increases the split tax `delta`.

A nontrivial safe design must balance these two effects.

This may provide a principled explanation for why simple role separation dramatically reduced coupling in CMDO but paid a large finite-audit cost.

---

## Immediate U10 oracle check

For the existing half-split style comparison, using revealed U10 truth only as a post-completion diagnostic, the oracle full-budget feasibility condition is satisfied for Georgia at budget 128 but fails for the remaining seven cohort-budget states. This is consistent with the observed large direct split tax and shows why an independence-only solution is unlikely to be operationally adequate without a more efficient design.

This is **not** prospective validation and must not be reported as such.

---

## What would make this manuscript-grade

The strongest path now appears to be a paired result:

1. **Impossibility / limitation:** unrestricted same-audit coupling prevents a nontrivial cap-only no-harm guarantee.
2. **Constructive restoration:** an independent decision certificate gives finite-sample conditional safety, with an explicit feasibility condition against the full-budget direct comparator.

The remaining question is whether a practical design can control dependence without paying a prohibitive split tax. Cross-fitting restores data efficiency but can reintroduce interaction terms, so any cross-fitted theorem must control those terms rather than assuming them away.
