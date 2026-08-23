# U10 — Prospective external ECG falsification

This directory records the frozen U10 prospective ECG experiment for CMDO.

## Scientific status

- **Source:** PTB-XL, PhysioNet/CinC Challenge 2020 v1.0.2
- **External targets:** Georgia and CPSC 2018
- **Task:** atrial fibrillation present vs absent (SNOMED CT `164889003`)
- **Primary estimand:** fixed-threshold target accuracy
- **Prospective primary verdict:** `MECHANISM_NOT_CONFIRMED`
- **Interpretation rule:** the prospective verdict is immutable; post-hoc diagnostics are exploratory and may motivate theory but may not redefine the locked gate.

## Locked provenance chain

| Stage | SHA256 |
|---|---|
| PREOUTCOME seal | `efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949` |
| Locked evaluation specification | `25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449` |
| Prospective result CSV | `685be9c1a86b4ace5c41d1ff4564fc2fedd65a8f15e9555fe6b3886a6d3c4df9` |
| Prospective result JSON | `dd2624ba443c69ef2dd276f40eefdff8dadb97612e9838c77b019a4e15c9b090` |
| Post-hoc phase diagnostics CSV | `cae428a478cca74ca28e73cd986edba10ebdfff4c8bb89de82d2c696e1802afb` |
| Post-hoc phase diagnostics JSON | `3597fea4f9a0546705488a70003f91ca168d38cef92ef53928f0b94b27040f12` |
| Post-hoc dependence decomposition CSV | `580a0480391ea40cad021fc0264350f6eba357d24a219a670687163159470bcc` |
| Post-hoc dependence decomposition JSON | `95d9f1cf9cd20c493af94fce9d94bb7fff8e27ce601ee58e8af0fec767f54947` |

## Final scientific freeze

The final local U10 evidence capsule was created after all prospective and declared post-hoc analyses above were complete.

- Final evidence capsule SHA256: `773047301c940ca2aeb26ce4f72a118feeddf0ec65ff66b3fbb7ba59c45e88b7`
- Final evidence-capsule manifest SHA256: `f91164514012192883208f01c579077010cffaa5bd2ef160889ed8773a082503`
- Final raw-data state: PTB-XL `21837 .mat + 21837 .hea`; Georgia `10344 .mat + 10344 .hea`; CPSC 2018 `6877 .mat + 6877 .hea`.

## Prospective result

The locked prospective mechanism test did **not** meet its predeclared cross-target gate. Georgia satisfied the per-target criterion, whereas CPSC 2018 did not. This result is retained as a falsification result rather than retrospectively repaired.

Post-hoc analyses subsequently showed that constant-mean and weight-permutation controls recover much of the lost performance in several target-budget cells, motivating a deeper analysis of adaptive evidence composition. These analyses are explicitly separate from the prospective verdict.

## Repository policy

Raw public ECG waveforms/headers are not tracked in GitHub. Large derived feature arrays and the final evidence-capsule ZIP are also not duplicated here. This directory should contain the exact small protocol/result/provenance artifacts and frozen code needed to audit the U10 chronology. Any future U10 analysis must be added under a new versioned `POSTHOC` or `THEORY` path and must not overwrite the frozen prospective record.
