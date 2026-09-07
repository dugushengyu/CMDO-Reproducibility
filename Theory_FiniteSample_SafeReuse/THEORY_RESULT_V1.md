# Finite-sample certifiability of adaptive historical reuse — v1

Status: exploratory theory result. This file does not revise any frozen CMDO claim or U6–U11 verdict.

## 1. Setup

Let the target performance be `theta`. Let the direct current estimator be

`D = theta + e`,

with `E[e]=0` and `E[e^2]=V(theta)>0`. Let the completed historical estimate be fixed at

`H = theta + B`.

For a borrowing weight `W in [0,1]`, define

`A = (1-W)D + W H`.

The primary comparator is squared-error risk.

---

## 2. Baseline lemma: fixed or role-separated reuse

If `W` is independent of `D`, define

`mu = E[W]`, `q = E[W^2]`, `Lambda = B^2/V`.

Then exactly

`R(A)/V - 1 = -2 mu + (1+Lambda) q`.

If `W=w` is fixed, this reduces to

`R(A)/V - 1 = -2w + (1+Lambda)w^2`,

so fixed reuse is non-inferior to direct evaluation iff

`0 <= w <= 2/(1+Lambda)`.

This is baseline bias–variance geometry and is not claimed as the main novelty.

---

## 3. Theorem 1: no magnitude-only safeguard under unrestricted same-audit adaptation

**Theorem 1 (magnitude-only safety is insufficient).** For every borrowing cap `omega` with `0 < omega < 1`, there exists a bounded scalar performance problem with `theta in (0,1)`, an unbiased direct estimator `D in [0,1]`, a historical value `H in [0,1]`, and a data-dependent rule `W=W(D) in [0,omega]` such that:

1. every fixed weight `w in [0,omega]` is non-inferior to direct evaluation in MSE; but
2. the adaptive estimator `A=(1-W)D+WH` has strictly larger MSE than direct evaluation.

### Proof

Fix `omega in (0,1)`. Choose any

`1 < r < sqrt(2/omega - 1)`.

This interval is non-empty because `omega<1`. Set `theta=1/2`. Choose `a>0` small enough that

`D = theta +/- a`

and

`H = theta + r a`

all lie in `[0,1]`. Let the two values of `D` occur with equal probability. Then `D` is unbiased, `V=a^2`, `B=ra`, and `Lambda=r^2`.

For every fixed `w <= omega`,

`R_w/V - 1 = -2w + (1+r^2)w^2 <= 0`,

because `omega < 2/(1+r^2)` by construction.

Now define the same-audit rule

`W=omega` when `D=theta+a`, and `W=0` when `D=theta-a`.

Its risk difference is

`R(A)-V = (a^2/2) * [(1 + omega(r-1))^2 - 1] > 0`,

because `r>1` and `omega>0`. Therefore a pointwise borrowing cap that is sufficient for every fixed rule need not protect a same-audit adaptive rule. QED.

### Interpretation

The failure is structural: controlling only the magnitude of borrowing cannot provide a universal finite-sample no-harm guarantee when the borrowing decision is allowed to depend on the same estimation noise it modifies.

---

## 4. Exact dependence correction

Without independence,

`R(A)-V = -2V mu + (V+B^2)q + C_dep`,

where

`C_dep = -2 Cov(W,e^2) + Cov(W^2,e^2) + 2B Cov(W,e) - 2B Cov(W^2,e)`.

Define the independent-weight safety margin

`M = 2V mu - (V+B^2)q`.

Then exactly

`R(A) <= V  <=>  C_dep <= M`.

Thus Theorem 1 is not a paradox: same-audit dependence can consume a positive fixed/independent safety margin.

---

## 5. Theorem 2: observable high-probability finite-sample certificate under honest role separation

Let `S` be a decision audit independent of the evaluation estimator `D`. Suppose `C_alpha(S)` is a finite-sample confidence set satisfying

`P_theta(theta in C_alpha(S)) >= 1-alpha`.

Define the observable worst-case mismatch coordinate

`Lambda_U(S) = sup_{t in C_alpha(S)} (H-t)^2 / V(t)`.

Let `w(S)` be any measurable rule satisfying

`0 <= w(S) <= min{1, 2/(1+Lambda_U(S))}`.

Define

`A_S = (1-w(S))D + w(S)H`.

**Theorem 2.** Under the stated independence and unbiasedness assumptions,

`P_S( E_theta[(A_S-theta)^2 | S] <= V(theta) ) >= 1-alpha`.

### Proof

On the event `theta in C_alpha(S)`, by definition

`Lambda(theta)=(H-theta)^2/V(theta) <= Lambda_U(S)`.

Conditional on `S`, the chosen weight is fixed and independent of `D`. Therefore

`E[(A_S-theta)^2|S]/V(theta) - 1`

`= -2w(S) + (1+Lambda(theta))w(S)^2`

`<= -2w(S) + (1+Lambda_U(S))w(S)^2 <= 0`.

The coverage event has probability at least `1-alpha`. QED.

### Bounded-loss corollary

If `theta`, `D`, `H`, and hence `A_S`, lie in `[0,1]`, then squared error is at most 1. Consequently

`R(A_S) <= V(theta) + alpha`.

This unconditional additive bound is secondary; the main object is the finite-sample high-probability conditional no-harm certificate.

---

## 6. Theorem 3: same-total-budget certifiability boundary

Role separation spends current outcomes on the decision audit. Let `D_eval` be the evaluation-only direct estimator with variance `V_eval(theta)`. Let `D_full` be the direct estimator using the full current-outcome budget, with

`V_full(theta) = rho * V_eval(theta)`,

where `0 < rho <= 1` is known and does not depend on `theta`. Define the split tax

`delta = 1-rho`.

On the confidence event, use the same `Lambda_U(S)` but normalize mismatch by `V_eval`.

For a fixed conditional weight `w`, worst-case risk over the confidence set is bounded by

`V_eval(theta) * [(1-w)^2 + Lambda_U(S) w^2]`.

Therefore comparison with full-budget direct evaluation requires

`(1+Lambda_U)w^2 - 2w + delta <= 0`.

**Theorem 3 (finite-sample certifiability boundary).** A non-empty weight interval can be certified against full-budget direct evaluation iff

`delta <= 1/(1+Lambda_U)`.

Equivalently, define the certifiability margin

`Psi = 1/(1+Lambda_U) - delta`.

Then:

- `Psi > 0`: a non-degenerate certified interval exists;
- `Psi = 0`: exactly one certified weight exists;
- `Psi < 0`: no weight can be certified against full-budget direct evaluation under the stated confidence set and role-separated design.

When feasible, the certified interval is

`w_minus <= w <= w_plus`,

where

`w_+/- = [1 +/- sqrt(1-(1+Lambda_U)delta)]/(1+Lambda_U)`.

### Proof

The quadratic in `w` has leading coefficient `1+Lambda_U>0`. Its minimum occurs at

`w_star = 1/(1+Lambda_U)`,

with minimum value

`delta - 1/(1+Lambda_U)`.

Hence a solution exists iff that minimum is non-positive. The roots give the interval. QED.

### Interpretation

This is a feasibility result, not merely a tuning rule. Even perfect role separation cannot certify reuse against a full-budget direct estimator if the finite-sample uncertainty about historical mismatch is too large relative to the information spent creating independence.

---

## 7. Binary-accuracy corollary for an iid audit split

For Bernoulli correctness with total current-outcome budget `M`, decision budget `m_s`, and independent evaluation budget `m_e=M-m_s`,

`V_eval(theta)=theta(1-theta)/m_e`,

`V_full(theta)=theta(1-theta)/M`.

Thus

`rho=m_e/M`, `delta=m_s/M`.

If `C_alpha=[L,U]` is an exact binomial confidence interval from the decision audit, then

`Lambda_U = m_e * sup_{t in [L,U]} (H-t)^2/[t(1-t)]`.

For `0<L<U<1`, the function has no interior maximum; therefore

`Lambda_U = m_e * max{ (H-L)^2/[L(1-L)], (H-U)^2/[U(1-U)] }`.

If the confidence set touches a zero-variance boundary, the conservative certificate may become infinite and force fallback.

The full-budget feasibility condition simplifies to

`Lambda_U <= M/m_s - 1`.

For a 50:50 split this becomes `Lambda_U <= 1`.

---

## 8. What is new here if it survives literature review

The candidate contribution is **not** the ordinary fixed-weight bias–variance identity. The potentially distinct theoretical package is:

1. a general bounded counterexample proving that no borrowing-magnitude cap alone can ensure no-harm under unrestricted same-audit adaptation, even when every fixed weight under that same cap is safe;
2. an observable finite-sample high-probability risk certificate obtained from an independent current audit;
3. a same-total-budget feasibility boundary showing when the cost of creating independence makes certified reuse impossible.

This package should be described as a theory of **certifiable reuse**, not as the first finite-sample theory of adaptive borrowing in general.

---

## 9. Remaining proof / research obligations

Before manuscript use:

1. audit Theorem 1 against decision-theoretic admissibility and adaptive-shrinkage literature;
2. verify exact confidence-set construction for the sampling design actually claimed;
3. test whether Theorem 2 is non-vacuous under realistic budgets;
4. test Theorem 3 against frozen U10 only as a post-completion diagnostic;
5. determine whether a dependence-controlled construction can recover most of the full-budget information without invalidating the certificate;
6. if all non-oracle full-budget certificates collapse to fallback in realistic states, promote the feasibility boundary/impossibility result rather than forcing a nominally safe but operationally useless method.