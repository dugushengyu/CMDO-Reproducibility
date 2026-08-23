# U10 GitHub import policy

The GitHub record is intentionally smaller than the local frozen evidence capsule.

Tracked here:
- exact small protocol and result files;
- frozen text/code used for U10;
- final provenance ledger, chronology, and SHA256 manifest.

Not tracked here:
- public raw ECG `.mat` / `.hea` files;
- large derived `.npz` feature arrays;
- source model binary (`.joblib`);
- evidence-capsule ZIP.

Those omitted artifacts remain bound to the record by the PREOUTCOME seal and final freeze hashes. Future analyses must be added under new versioned `POSTHOC` or `THEORY` paths and must not overwrite prospective files.
