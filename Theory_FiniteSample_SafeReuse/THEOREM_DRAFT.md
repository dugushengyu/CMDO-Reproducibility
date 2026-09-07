# Draft finite-sample safe-reuse theory

## 1. Setup

Let the target performance be `theta`.

Let the direct current estimator be

`D = theta + e`,

with

`E[e] = 0`, `E[e^2] = V < infinity`.

Let the completed historical estimate be fixed at

`H = theta + B`.

Let `W` be a random borrowing weight with `0 <= W <= omega <= 1`, and define

`A = (1-W) D + W H`.

Then

`A - theta = (1-W)e + WB`.

The objective is to compare finite-sample squared-error risk `R(A)=E[(A-theta)^2]` with the same-budget direct risk `V`.

---

## 2. Proposition A: exact role-separated risk identity

**Proposition A (finite-sample role-separated adaptive risk).**
Assume `W` is independent of `D` (equivalently of `e`). Define

`mu = E[W]`, `q = E[W^2]`, `Lambda = B^2 / V`.

Then, exactly,

`R(A) - V = -2 V mu + (V + B^2) q`

or

`R(A)/V - 1 = -2 mu + (1 + Lambda) q`.

Therefore, if `mu > 0`,

`R(A) <= V`

if and only if

`q / mu <= 2 / (1 + Lambda)`.

### Proof

Under independence,

`E[(1-W)^2 e^2] = E[(1-W)^2] E[e^2]`

and

`E[W(1-W)e] = E[W(1-W)]E[e] = 0`.

Hence

`R(A) = V E[(1-W)^2] + B^2 E[W^2]`

`= V(1 - 2mu + q) + B^2 q`,

which gives the result.

No Gaussian assumption, asymptotic approximation, or continuous outcome model is used.

---

## 3. Corollary A1: a hard finite-sample safe cap

Because `0 <= W <= omega`,

`W^2 <= omega W`,

so

`q <= omega mu`.

Thus a sufficient condition for no harm is

`omega <= 2 / (1 + Lambda)`.

If only an upper bound `Lambda <= Lambda_U` is available, the stronger cap

`omega <= 2 / (1 + Lambda_U)`

is sufficient.

The practical rule would therefore be

`W_safe = min(W_raw, 2/(1+Lambda_U))`.

This is only deployment-usable if `Lambda_U` is itself available without target-truth leakage. Constructing such a finite-sample upper bound is a major remaining proof obligation.

---

## 4. Proposition B: exact coupling correction

The role-separated result does not apply when `W` depends on the same direct-estimation error `e`.

Without any independence assumption,

`R(A) - V = -2 V mu + (V+B^2)q + C_dep`,

where

`C_dep = -2 Cov(W,e^2) + Cov(W^2,e^2) + 2B Cov(W,e) - 2B Cov(W^2,e)`.

Equivalently, define the independent-weight safety margin

`M = 2V mu - (V+B^2)q`.

Then

`R(A) <= V`

if and only if

`C_dep <= M`.

This exact identity is the natural finite-sample bridge to the existing CMDO adaptive-composition decomposition: weight heterogeneity determines the baseline margin, while weight–error dependence can consume or reverse that margin.

### Proof sketch

Expand

`R(A)=E[(1-W)^2e^2] + 2B E[W(1-W)e] + B^2E[W^2]`

and add/subtract `mu V` and `qV` in the `e^2` terms. Because `E[e]=0`, the remaining first-moment terms are covariances. Collecting terms gives the expression above.

---

## 5. Counterexample: the safe cap fails under same-audit coupling

The role-separation assumption is substantive, not cosmetic.

Take a bounded scalar performance example:

- `theta = 0.5`;
- `D = 0.25` or `0.75` with equal probability, so `e = -0.25` or `+0.25` and `V=0.0625`;
- `H = 1`, so `B=0.5` and `Lambda = B^2/V = 4`;
- the role-separated oracle cap is `omega_safe = 2/(1+4)=0.4`.

Now choose a same-audit rule

- `W=0.4` when `D=0.75`;
- `W=0` when `D=0.25`.

Then the two squared errors are

- when `D=0.75`: `[(1-0.4)(0.25)+0.4(0.5)]^2 = 0.35^2 = 0.1225`;
- when `D=0.25`: `(-0.25)^2 = 0.0625`.

Therefore

`R(A) = (0.1225+0.0625)/2 = 0.0925 > 0.0625 = V`.

Thus even a weight that never exceeds the role-separated safe cap can be harmful when the borrowing decision is coupled to the current-estimation error.

This is directly relevant to the U10 observation that mean borrowing levels can look modest while adaptive risk exceeds matched fixed risk.

---

## 6. U10 diagnostic prediction

Using the frozen U10 target accuracy `theta`, historical accuracy `H`, cohort size `N`, and full audit budget `m`, the exact simple-random-sampling-without-replacement variance of direct accuracy is

`V_FPC = theta(1-theta)(N-m) / [m(N-1)]`.

Define the post-completion oracle coordinate

`Lambda_oracle = (H-theta)^2 / V_FPC`

and the corresponding role-separated safe cap

`omega_oracle = min(1, 2/(1+Lambda_oracle))`.

The initial diagnostic asks:

1. Are the observed U10 mean shared weights below `omega_oracle`?
2. If yes, do shared-adaptive harmful states still occur?
3. Do constant-mean-weight comparators remain beneficial in those same states?

If all three occur, U10 becomes a clean empirical illustration of Proposition B: magnitude control alone is insufficient; dependence can consume the independent-weight safety margin.

This diagnostic is strictly post-completion and cannot be used as prospective validation of the theorem.

---

## 7. Stronger target: data-derived finite-sample certificate

The baseline proposition is not enough for the manuscript because `Lambda` contains target truth.

A publishable upgrade would require a non-oracle object `Lambda_U(S)` computed from a **decision sample `S` independent of the evaluation estimator `D`**, such that

`P[Lambda <= Lambda_U(S)] >= 1-alpha`.

On the event `Lambda <= Lambda_U(S)`, choosing

`W <= 2/(1+Lambda_U(S))`

gives conditional finite-sample no-harm relative to the evaluation-sample direct estimator.

For bounded metrics, the failure event can additionally yield a PAC-style bound of the form

`R(A) <= V + alpha * L_max`

under an appropriate bounded-loss argument. This needs a careful proof; it is not yet established here.

The main technical obstacle is that `Lambda=B^2/V` requires both an upper bound on historical mismatch and enough information about the direct-estimation variance. For finite-cohort accuracy, `V(theta)` is known once `theta` is known, so an exact finite-population confidence set for `theta` may permit

`Lambda_U = sup_{theta in C_alpha} (H-theta)^2 / V(theta)`.

If the confidence set approaches a zero-variance boundary, `Lambda_U` may become infinite, correctly forcing fallback `W=0`. Whether this construction is sharp enough to be useful is an empirical/theoretical question for the next stage.

---

## 8. Full-budget direct comparator and split tax

Role separation can protect against coupling but spends outcomes on the decision sample. If the evaluation estimator has variance `V_eval` while a direct estimator using the entire outcome budget has variance `V_full < V_eval`, then no-harm relative to **full-budget** direct evaluation requires

`V_eval - 2 V_eval mu + (V_eval+B^2)q <= V_full`.

Equivalently,

`2 V_eval mu - (V_eval+B^2)q >= V_eval - V_full`.

The right-hand side is the finite-audit split tax.

This makes explicit why simple role separation may be safe relative to the same evaluation half but still inferior to full-budget direct evaluation. A useful theorem must either pay this tax through sufficient historical-information gain or recover efficiency through a construction whose dependence remains controlled.

---

## 9. Proof obligations before any manuscript use

1. Verify every identity symbolically and numerically.
2. Determine whether Proposition A is already standard in random-shrinkage / historical-borrowing literature; do not claim novelty if it is only an immediate extension.
3. Derive a nontrivial, finite-sample `Lambda_U` or an alternative directly observable certificate.
4. Prove the confidence statement under the exact sampling design being claimed.
5. Decide the comparator: same evaluation sample versus same total outcome budget.
6. Test whether the certificate is non-vacuous on frozen U10 and other already-completed states without retuning them.
7. If role separation makes the guarantee trivial but operationally useless, stop.
8. If arbitrary same-audit coupling prevents any nontrivial universal guarantee, formalize the impossibility result rather than hiding it.
