# CMDO reproducibility repository

CMDO reviewer package with a single Python entry point and explicit separation of
**engineering verification**, **fresh scientific replay**, and **archival historical
continuation**.

## Reviewer entry points

```bash
python RUN_REPRODUCTION.py audit
python RUN_REPRODUCTION.py smoke --allow-network
python RUN_REPRODUCTION.py frozen
python RUN_REPRODUCTION.py full-claim --plan
python RUN_REPRODUCTION.py archival-continuation --plan
```

Detailed commands and exit semantics are in
[docs/REVIEWER_QUICKSTART.md](docs/REVIEWER_QUICKSTART.md).

One-command engineering acceptance for an ordinary Git clone:

```bash
python scripts/final_reviewer_acceptance.py --skip-runtime
```

For the reviewer **Portable** bundle, additionally require all seven canonical
archives:

```bash
python scripts/final_reviewer_acceptance.py --skip-runtime --require-canonical
```

Omit `--skip-runtime` on the intended Python 3.11/MATLAB replay workstation.

## Scientific boundary

The original historical T2-D v0.1 certificate passed 11/11 frozen gates. The
reference fresh current-runtime replay executes T2-D successfully but does not
reproduce the historical G4 authorisation gate (10/11). The runner therefore records
`SCIENTIFIC_DIVERGENCE_BOUNDARY`, returns exit code `4`, preserves the scientific
artifacts, and prohibits downstream stages from being represented as a fresh
accepted chain. No threshold is relaxed to force a pass.

A separate `archival-continuation` profile starts from byte-verified accepted
historical T2-D/T2-E parents to audit downstream historical implementation. That mode
is explicitly **not** fresh raw-to-science reproduction.

Machine-readable disclosure: `provenance/scientific_boundaries.json`.

## Portable versus GitHub clone

The reviewer **Portable** ZIP carries seven canonical result archives plus
`bootstrap_inputs/portable/`, which contains large byte-verified historical bootstrap
records. Those bytes are deliberately Git-ignored. A bare GitHub clone supports code,
provenance, audit/smoke, and user-supplied data workflows, but the deepest fresh and
archival reviewer paths should be launched from the portable distribution.

Stage11C historical official receipt bytes are not redistributed. Their exact names,
sizes, and hashes are declared in `provenance/historical_receipts.json` and verified
at full-claim preflight.

## Immutable evidence and runtime adaptation

Authoritative source bytes under `legacy/original_authoritative/` are never edited.
The runner creates adapted execution copies, records source/adapted hashes, redirects
legacy Colab paths, constrains the numerical Python stack, and rebinds runtime parent
hash commitments to byte-verified freshly produced upstream artifacts. Engineering
failure cleanup is transactional; scientific-boundary artifacts are never rolled
back.

## Governance

All default reviewer paths are retrospective. U9/eICU is excluded. The package does
not accept provider terms, redistribute restricted raw data, create a new prospective
claim, or delete Drive/GitHub content.

See also:

- [Reviewer quickstart](docs/REVIEWER_QUICKSTART.md)
- [End-to-end reproduction contract](docs/END_TO_END_REPRODUCTION.md)
- [Data/license gates](docs/DATA_LICENSE_GATES.md)
