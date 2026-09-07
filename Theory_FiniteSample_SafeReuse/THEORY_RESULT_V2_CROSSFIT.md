# Theory result v2 — reciprocal cross-fitting does not automatically restore safety

Status: exploratory theorem. Frozen CMDO manuscript and U10 verdicts remain unchanged.

## 1. Why this extension is needed

V1 established a sharp tension:

- unrestricted same-audit adaptation cannot be protected by a borrowing-magnitude cap alone;
- a one-way honest decision/evaluation split restores a finite-sample certificate;
- but the split can make full-budget certification infeasible.

The natural response is to ask whether ordinary reciprocal cross-fitting recovers the withheld information while preserving the independence needed for safety.

The answer, in general, is **no**.

---

## 2. Two-fold reciprocal construction

Let two current direct estimates be

`D1 = theta + e1`, `D2 = theta + e2`,

where `(e1,e2)` are independent and identically distributed, `E[e_i]=0`, `E[e_i^2]=V`.

Let each fold choose a weight from its own data:

`W1 = g(D1)`, `W2 = g(D2)`.

Apply each weight to the opposite fold and average:

`A_CF = 1/2 * [ (1-W1)D2 + W1 H + (1-W2)D1 + W2 H ]`.

This is the natural two-fold reciprocal analogue of honest role separation: `W1` is independent of `D2`, and `W2` is independent of `D1`.

However, each decision fold also re-enters the aggregate as the direct component of the opposite term.

---

## 3. Proposition: exact two-fold cross-fit risk identity

Let

`mu = E[W]`, `q = E[W^2]`, `c = E[W e]`, `B = H-theta`, `Lambda = B^2/V`.

Then

`R(A_CF) = 1/2 * { V(1-2mu+q) + B^2 q + c^2 + 2B(1-mu)c + B^2 mu^2 }`.

The full two-fold direct estimator

`D_full = (D1+D2)/2`

has risk `V/2`. Therefore

`2[R(A_CF)-R(D_full)]/V`

`= -2mu + (1+Lambda)q + c^2/V + 2(B/V)(1-mu)c + Lambda mu^2`.

### Derivation

Write

`T1=(1-W2)e1 + B W2`,

`T2=(1-W1)e2 + B W1`,

so `A_CF-theta=(T1+T2)/2`.

The diagonal terms satisfy

`E[T1^2]=E[T2^2]=V(1-2mu+q)+B^2q`

because `W2` is independent of `e1` and vice versa.

The cross term is

`E[T1 T2] = c^2 + 2B(1-mu)c + B^2 mu^2`,

because the reciprocal construction pairs each fold's weight with that same fold's error in the cross product. Combining diagonal and cross terms gives the identity.

### Interpretation

Foldwise independence is not the same as aggregate independence. Reciprocal cross-fitting removes the direct within-term coupling, but the final average contains a residual dependence channel through `c=E[We]`.

---

## 4. Theorem 4: reciprocal cross-fitting can be harmful even when every fixed weight under the same cap is safe

**Theorem 4.** For every cap `omega` satisfying

`0 < omega < 2/3`,

there exists a bounded scalar performance problem and a two-fold reciprocal cross-fitted rule with `0<=W_i<=omega` such that:

1. every fixed borrowing weight `w in [0,omega]` is MSE non-inferior to the full two-fold direct estimator; but
2. the reciprocal cross-fitted adaptive estimator has strictly larger MSE than the full direct estimator.

### Proof

Choose `theta=1/2` and let each fold error be `e_i=+/-a` with equal probability. Let

`H=theta+r a`,

where `r>1`. Choose `a` small enough that all quantities remain in `[0,1]`.

The full direct variance is `a^2/2`. For a fixed weight `w`,

`A_w=(1-w)D_full+wH`,

so

`R(A_w)-R(D_full)`

`= -a^2 w + (a^2/2 + r^2 a^2)w^2`.

Thus every fixed `w<=omega` is safe whenever

`omega <= 2/(1+2r^2)`.

Because `omega<2/3`, one can choose

`1 < r < sqrt[(2/omega - 1)/2]`,

so this fixed-weight safety condition holds.

Now choose

`W_i=omega` when `e_i=+a`, and `W_i=0` when `e_i=-a`.

Direct enumeration of the four equally likely fold pairs gives

`R(A_CF)-R(D_full)`

`= (a^2 omega/8) * [3 omega r^2 - 2 omega r + 3 omega + 4r - 4]`.

The bracket is strictly positive because `r>1` and `omega>0`. Hence reciprocal cross-fitting is harmful despite the fact that every fixed weight under the same cap is safe. QED.

---

## 5. Consequence for the current research route

A naive strategy of

`split -> learn weights on one fold -> apply to the other fold -> swap -> average`

is **not** a universal solution to the v1 split-tax problem.

The current theory therefore identifies three distinct regimes:

### Same-audit reuse

Uses all current outcomes but admits unrestricted weight–error coupling. Magnitude control alone cannot guarantee no-harm.

### One-way honest role separation

Restores conditional independence and enables a finite-sample certificate, but withholds decision outcomes from the evaluation estimator and therefore pays a split tax.

### Reciprocal cross-fitting

Reuses both folds, but the aggregate reintroduces a dependence term. Cross-fitting alone does not restore a universal magnitude-only guarantee.

This is the first clean form of the **safety–information tension** emerging from the branch.

---

## 6. What would count as a real Route-A success now

A stronger construction must do more than ordinary reciprocal cross-fitting. It would need to control or remove the aggregate dependence term while recovering most of the current-data information.

Possible mathematical directions include:

1. an orthogonal correction that explicitly cancels the `E[We]` contribution;
2. a predictable/sequential construction with a provable martingale risk bound;
3. a restricted adaptive-weight class with a finite-sample dependence bound that is observable before target truth is known;
4. a selective certificate that controls false certification rather than claiming uniform MSE dominance.

If none of these yields a non-vacuous full-budget result, the branch should pivot to a general impossibility/possibility theorem rather than presenting cross-fitting as a repair.

---

## 7. Novelty caution

Cross-fitting, sample splitting, and data-reuse bias are classical ideas, and recent PPI work already studies finite-sample single-sample versus sample-splitting behavior. The potential CMDO contribution is therefore not 'cross-fitting can fail'.

The potentially distinct statement is the combined boundary for **potentially biased completed historical performance evidence**:

- fixed historical value can be useful;
- same-audit adaptation can destroy that value even under a fixed-safe cap;
- honest separation restores certifiability but spends current information;
- reciprocal reuse of the held-out information can reintroduce the dependence that safety required removing.

Priority language remains prohibited until a broader literature audit is completed.