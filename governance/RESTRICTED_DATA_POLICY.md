# Restricted and sensitive data policy

- Never commit eICU patient-level files, reserve-outcome vaults, credentials or local path files.
- U9 restricted material must remain below its generated `00_RESTRICTED_DO_NOT_SHARE` directory.
- Only the share-safe artifacts named in the U9 return checklist may leave the local machine.
- Before every push, inspect staged filenames and run `python scripts/verify_repository.py`.
- If sensitive data is ever staged or pushed, stop immediately; do not rely on a later ordinary deletion because Git history retains prior objects.
