# T2-KR Windows LF-byte adapter

The archival continuation passed T2-J and then stopped at T2-KR before the scientific computation because the authoritative Python pipeline materialises three immutable embedded text artefacts with `Path.write_text(..., encoding="utf-8")`.

The historical SHA-256 commitments were created from LF bytes. On Windows, default text-mode newline translation writes CRLF bytes and therefore violates the immutable SHA immediately. The frozen embedded content itself is unchanged: the LF byte hashes of the embedded preregistration, method and lexicon equal the authoritative `EXPECTED` commitments.

The non-destructive runtime adapter changes only the adapted T2-KR execution copy from text-mode writing to `write_bytes(text.encode("utf-8"))`. The authoritative source bytes, embedded strings, expected hashes, scientific thresholds, data, model logic and gates are unchanged.

Known CRLF residue hashes from the interrupted Windows run are handled conflict-safely: only files with those exact derived hashes may be removed so the adapted runtime can rematerialise the frozen LF bytes. Unknown files are never overwritten or deleted.
