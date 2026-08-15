# CMDO U8/U9 final integration audit — 15 August 2026

## Manuscript mapping

The final manuscript mapping is:

- Figures 1–4: retained canonical/main-article figures.
- Figure 5: integrated frozen U6+U7 confirmation.
- Figure 6: U8 natural-prevalence temporal confirmation plus completed U9 open external-clinical boundary.

The older repository mapping `Figure 5 = U7+U8` is superseded for the current manuscript. The earlier eICU U9 pre-outcome directory remains preserved as historical evidence and is **not** overwritten by the completed Open Clinical U9 branch.

## U8 audit

U8 uses NHANES 2011–2012 for source development, 2013–2014 for transparent historical evidence, and 2015–2016, 2017–2018 and August 2021–August 2023 as temporal reserves. Budgets are 128, 256, 512 and 1,024 randomly screened cases at natural prevalence, with 200 replicates per cycle-budget state.

Frozen summary:

- observer/direct MAE: `0.01810784293904858 / 0.020136109954008146`;
- relative reduction: `10.072784761268316%`;
- improved states: `12/12`; improved cycles: `3/3`;
- worst state regret: `-0.000794723969197435`;
- mean/minimum simultaneous coverage: `0.9683333333333334 / 0.94`;
- covered-event certificate violations: `0`;
- mean transport weight: `0.116411384109451`;
- direct root-budget slope: `-0.531444237112`;
- maximum fallback residual: `0`.

The final v1.1.0 output is a disclosed deterministic post-unseal reconstruction after an identifier-container comparison error. The reviewed target-score seal was reproduced before reconstruction and no scientific parameter was changed.

Hashes:

- pre-outcome seal: `5b6cab9bddd614b610a3acf5e69af0e1c304f14c4f38c55b62808be3835579cf`;
- completion record: `b642fdb275343ea603a0aa9f1e5c2be94bf290ee3d3a9726d163e1cccd170474`;
- canonical archive: `761d6f0720b204ddd15a0a811bf3868d9ab28005f989aea955887c52678de0ce`.

## U9 governance

The completed manuscript-facing U9 is a versioned **Open Clinical** programme sealed before either branch executed. It does not rewrite the earlier credentialed eICU protocol.

### U9A bridge

Cleveland is source; Hungary, Switzerland and VA Long Beach are external centres.

- pooled direct/observer MAE: `0.05748508448094686 / 0.05754893861859677`;
- pooled relative gain: `-0.11107948822981814%`;
- improved centres: `2/3`;
- centre gains: Hungary `+0.95%`, Switzerland `-3.64%`, VA Long Beach `+1.84%`;
- certificate violations: `0`; maximum fallback residual: `0`;
- frozen verdict: `BRIDGE_FALSIFICATION_SIGNAL`.

### U9B primary external-system reserve

PhysioNet Challenge 2019 public System A is source (`n=20,336`); System B is the external target (`n=20,000`). Target outcomes did not train or tune the model, threshold, observer or gates. A one-shot marker was written before System-B labels were read into analysis.

Transport mismatch:

- prevalence `0.0880 -> 0.0571`;
- historical/target AUC `0.7569 -> 0.5743`;
- historical accuracy/target truth `0.61627 -> 0.74850`;
- historical accuracy bias `-0.13223`.

Frozen summary:

- direct/observer MAE: `0.019876816406249994 / 0.02060547741737384`;
- relative gain: `-3.665883893231158%`;
- worst **budget-mean** regret: `0.0010474783257509634`;
- mean transport weight: `0.05110091647784553`;
- mean/minimum simultaneous coverage: `0.970 / 0.945`;
- covered-event certificate violations: `0`;
- maximum fallback residual: `0`;
- direct root-budget slope: `-0.49550986646467715`;
- frozen verdict: `PARTIAL_EXTERNAL_CERTIFICATION_EFFICIENCY_NOT_CONFIRMED`.

Replicate-level forensic recomputation also found that U9B MSE was worse than same-budget direct evaluation; the boundary is therefore not an MAE-only sign reversal. The confidence-event guarantee is blockwise and is not re-labelled as a universal aggregate-risk theorem.

Hashes:

- original Open Clinical pre-outcome package manifest: `5b63033bbb11cb2e5f3e65629c45b96e9f52ed907221ebbef0d8623119fbb684`;
- final U9 canonical ZIP: `32e05cd2b507bfa839257a49e9b307dce4c3529180c02c3717c182538c0e4e54`;
- share-safe forensic export: `c2e1c59c8378be842a4398eb227c3d250ef0e21e176922bfeb446682ce640919`.

## Interpretation locked for the manuscript

The evidence sequence is not “every benchmark improves”. It is:

`beneficial reuse (U6/U7/U8) -> heterogeneous reuse (U9A) -> external admissibility boundary (U9B)`.

Performance observability and historical-evidence reuse efficiency are distinct. Target outcomes restore information about current performance. Historical borrowing can improve finite-budget efficiency only when the transported evidence is sufficiently admissible; U9B demonstrates the external boundary while retaining exact direct fallback and the prespecified blockwise confidence-event integrity checks.

## Data-governance boundary

No raw patient-level PhysioNet PSV files are committed or redistributed. Repository-visible U9 records are share-safe summaries, state tables, protocol/config/seal evidence and one-shot provenance. The credentialed eICU branch remains deferred independent confirmation.
