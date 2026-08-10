# U9 return checklist

## After `RUN_PREPARE.m` — safe files to return for authorization

Return exactly these files from `CMDO_U9_eICU_Workdir_v1_0`:

1. `04_Logs/StageU9_SELFTEST_COMPLETE_v1_0.json`
2. `00_Data_Adapter/StageU9_Data_Adapter_Seal_v1_0.json`
3. `01_PreOutcome_Seal/StageU9_PreOutcome_Seal_v1_0.json`
4. `01_PreOutcome_Seal/StageU9_AUTHORIZATION_REVIEW_RECORD_v1_0.json`
5. `04_Logs/StageU9_DATA_ADAPTER_COMPLETE_v1_0.txt`
6. `04_Logs/StageU9_PREPARE_COMPLETE_v1_0.txt`

Also paste or screenshot the MATLAB command-window output from `RUN_SELFTEST.m`, `RUN_DATA_ADAPTER.m`, and `RUN_PREPARE.m`.

Do **not** return the roster, target-score CSV, `.mat` model, decompression cache, mapping, development-outcome file, reserve-outcome vault, or any official eICU table.

The reviewer will return `StageU9_EXECUTION_AUTHORIZATION_v1_0.json`. Place it at:

`CMDO_U9_eICU_Workdir_v1_0/01_PreOutcome_Seal/StageU9_EXECUTION_AUTHORIZATION_v1_0.json`

Do not edit it.

## After authorized `RUN_UNSEAL.m`

Return only:

1. `CMDO_U9_eICU_Workdir_v1_0/CMDO_U9_Canonical_Shareable_Record_v1_0.zip`
2. `CMDO_U9_eICU_Workdir_v1_0/StageU9_Canonical_Zip_Commit_v1_0.json`
3. The final MATLAB command-window output.

The canonical ZIP is assembled by an allowlist and rejects filenames associated with restricted row-level scores, outcomes, mappings, or raw identifiers.
