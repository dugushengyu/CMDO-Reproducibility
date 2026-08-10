# U0-U1 notebook repair note

The Drive source with file ID `1TKS1JCt8bi6h2-79BWlxWHvA_WkOpbul` is not valid JSON: one embedded base85 payload is followed by a literal CRLF inside a JSON string at raw character 13,976.

- `legacy/original_authoritative/u0_u1/...` preserves the imported source content (with repository line-ending normalization) for provenance.
- `legacy/repaired_runnable/u0_u1/..._REPAIRED.ipynb` changes only that literal CRLF to the escaped JSON sequence `\\r\\n`.
- The embedded payload, expected SHA-256 value and scientific code are unchanged.
- The repaired notebook is a packaging repair, not a new analytical version.
