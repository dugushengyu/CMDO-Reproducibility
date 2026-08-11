# T2-F archival numerical boundary

The separate `archival-continuation` profile originally attempted to re-execute
Stage T2-F from byte-verified accepted historical T2-D/T2-E parents. On the
published Windows/Python 3.11 replay baseline, all 13 target formal-revision
loops executed, but the immutable AMW-U exact-parent reproduction check failed:

`len(audit) == 27 * 100 and max(abs(parent - recomputed)) < 1e-10`.

The historical Stage T2-F run was produced under Linux/Python 3.12.13 with
NumPy 2.0.2, pandas 2.2.2, SciPy 1.16.3 and scikit-learn 1.6.1. Its preserved
2700-row exact-parent audit had maximum absolute difference
`4.99933427989e-13`, well inside the frozen `1e-10` assertion.

The current-runtime failure is therefore retained as an archival numerical
reproducibility boundary. The exact-parent assertion is not removed, weakened,
or reinterpreted. Stage T2-F is not claimed to have reproduced in the current
runtime.

For the distinct purpose of downstream historical implementation audit, the
portable reviewer bundle includes a byte-verified accepted historical T2-F
parent bundle containing the exact T2-F records required by T3-PF/T2-G, plus
the historical execution-environment and exact-parent audit evidence. The
`archival-continuation` executable frontier therefore begins at T3-PF from
accepted historical T2-D/T2-E/T2-F parents.

This archival mode remains separate from the fresh raw-to-science claim and
does not create a prospective or confirmatory claim.
