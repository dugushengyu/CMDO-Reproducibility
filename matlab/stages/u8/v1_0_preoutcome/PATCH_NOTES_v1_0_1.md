# CMDO U8 package patch v1.0.1

Date: 2026-08-09

## Correction

The v1.0 preflight function incorrectly included `predict` in a list checked
with `exist(name, 'file')`. In this pipeline, `predict` is dispatched as a
method of the fitted `ClassificationLinear` object. A valid installation of
Statistics and Machine Learning Toolbox can therefore fail that standalone
path check even though model prediction is available.

Patch v1.0.1 removes only that invalid preflight item and adds `perfcurve`,
which the pipeline actually calls as a standalone function.

## Scientific and governance impact

- No reserve outcome was accessed by the reported failure.
- The failure occurred before directory creation, download, model fitting,
  scoring or seal generation.
- No scientific configuration, model, estimand, audit design, random seed,
  budget, decision gate, authorization rule or one-shot boundary changed.
- The protocol and output schema remain v1.0; the seal records the corrected
  source-code hash.
