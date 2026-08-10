# Local data mount

Do not commit raw data or canonical ZIP archives here. A complete portable
handoff bundle may contain the seven verified small-result archives under
`data/canonical_records/`; Git ignores that directory. A normal Git clone
should configure the archives' real local location in
`config/local_paths.json` or copy them into that ignored directory.

Expected canonical archives:

- `StageU4C_Canonical_Records_v1.1.zip`
- `StageU5B_Canonical_Records_v1.0.zip`
- `StageU5D_Canonical_Records_v1.0.zip`
- `StageU5E_Canonical_Records_v1.0.zip`
- `StageU5F_Canonical_Records_v1.0.zip`
- `StageU6_Canonical_Records_v1.0.zip`
- `StageU7_Canonical_Records_v1.0.zip`
