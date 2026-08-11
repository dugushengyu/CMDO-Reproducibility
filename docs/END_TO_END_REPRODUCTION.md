# End-to-end reproduction contract

## Evidence modes

| Profile | Starts from | Retrains | Meaning |
|---|---|---:|---|
| `audit` | repository bytes/manifests | No | engineering/provenance integrity |
| `smoke` | one official public dataset | small model | environment sanity only |
| `frozen` | canonical result ZIPs | No | fastest publication-figure verification |
| `full-claim` | official/public raw assets plus declared historical prerequisites | Yes | fresh retrospective raw-to-science replay, subject to scientific boundary |
| `archival-continuation` | byte-verified accepted historical T2-D/T2-E parents | downstream only | historical implementation audit; **not fresh reproduction** |
| `historical-replay` | broader legacy path | Yes | discovery-history audit |

The machine-readable graph is `provenance/reproduction_dag.json`. The fresh
`full-claim` plan declares 55 nodes. T3-PF is structurally positioned after T2-F and
before T2-G because T2-G and later development stages consume its activation record.
U9 is absent from the accepted/default paths.

## Historical bootstrap boundary

Several early records are frozen historical parents rather than stages that can be
regenerated without changing the accepted protocol chronology. The reviewer portable
bundle therefore includes byte-verified archives under `bootstrap_inputs/portable/`:

- Stage 7 parents required by Stage 8/9;
- Stage11E aborted pre-execution mixed-endpoint protocol record;
- T1-R historical representations and protocol parents;
- T2-D and T2-E historical protocol/preregistration parents;
- an archival accepted-parent bundle used only by `archival-continuation`.

These bytes are Git-ignored because of size/redistribution boundaries. The runner
verifies every member hash and refuses to overwrite a conflicting runtime file.

Stage11C also requires six historical official provider receipt files. Their exact
identity is declared in `provenance/historical_receipts.json`. They are prerequisites
for reconstructing the historical acquisition path; they are not described as fresh
downloads.

## Immutable originals and runtime adapters

`legacy/original_authoritative/` preserves imported evidence. Runtime adapters are
non-destructive. Immediately before each source stage, the runner regenerates the
adapted copy so SHA commitments to newly reproduced upstream parents can be rebound
from the actual byte-verified runtime files rather than stale historical hashes.

The adapter records every source/adapted SHA and semantic runtime adaptation. It also
contains two explicitly governed portability adaptations discovered by fresh replay:
Windows extended-length addressing for T1-R and a Stage11G invariant check that
preserves failed-gate identity instead of requiring an environment-sensitive exact
intermediate count. Neither adaptation relaxes T2-D/T2-E scientific gates.

## Numerical environment

The replay environment is constrained by `environment/replay-constraints.txt`.
Fresh diagnostics identified a localized Stage11E near-zero-variance conditioning
defect under a different execution stack; it is documented as a hardening candidate,
not used to retroactively claim that the historical T2-D authorisation reproduced.
No analogous constant-to-tiny discontinuity was found in Stage8/Stage8B.

## Scientific divergence semantics

The historical T2-D v0.1 certificate passed 11/11 frozen gates. On the reference
fresh current-runtime replay, T2-D executed to completion but passed 10/11 because
G4 (target-cluster exact sign-flip) did not reproduce the historical authorisation
boundary. After mechanism audits and predeclared development probes, no gate was
relaxed and further T2-D tuning on the observed development evidence was closed.

Accordingly, a non-authorising fresh T2-D result raises
`SCIENTIFIC_DIVERGENCE_BOUNDARY` and returns exit status `4`. The generated T2-D
artifacts are preserved, the ledger records the evidence, and fresh downstream
execution stops. This is deliberately distinct from an engineering failure (`1`) or
prerequisite block (`3`).

## Archival continuation

`archival-continuation` materializes accepted historical T2-D/T2-E parent records and
continues the declared downstream historical path. Its project root should be
separate from a fresh replay root. The runner writes an explicit archival
classification and sets `fresh_raw_to_science_reproduction=false`. Results from this
mode may audit downstream implementation, but must never be presented as successful
fresh reproduction of the raw-to-science chain.

## Resume and transactional cleanup

`run_state.json` is resumable. A stage is skipped only with `--resume` and status
`COMPLETE`. A sealed scientific boundary cannot be skipped into downstream fresh
stages. For engineering failures, the runner removes only newly created stage-owned
top-level output entries; pre-existing data and successfully completed scientific
boundary artifacts are preserved.

## What is never automatic

Provider-term acceptance, redistribution of restricted raw data, creation of a new
prospective claim, U9/eICU execution, and Drive/GitHub deletion are outside the
reviewer replay. Those are governance boundaries, not missing scientific steps.
