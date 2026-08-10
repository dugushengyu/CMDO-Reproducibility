# Cleanup safety boundary

`drive_cleanup_manifest.csv` is a proposal, not a deletion authorization. Every row
contains the exact Drive file ID, current path, size, proposed disposition, backup
evidence and the next required gate. All rows currently have
`delete_authorized=false` and `second_backup_verified=false`.

The inventory covers only the five targeted roots recorded in
`provenance/drive_inventory_summary.json`; it is not a full Drive or raw-data
inventory. Therefore nothing outside those exact rows may be inferred to be safe to
delete.

The only direct delete candidate is generated Python bytecode. Legacy notebooks,
old rendered figures and earlier migration packages are archive candidates, not
delete candidates. Actual Drive mutation requires a separate, explicit confirmation
after the package, GitHub snapshot, replay report and second backup all pass.
