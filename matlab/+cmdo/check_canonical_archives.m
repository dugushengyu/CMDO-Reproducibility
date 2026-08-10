function report = check_canonical_archives(cfg, throwOnMissing)
%CHECK_CANONICAL_ARCHIVES Verify availability and byte identity of bundles.

if nargin < 1 || isempty(cfg)
    cfg = cmdo.load_config();
end
if nargin < 2
    throwOnMissing = false;
end
names = cmdo.canonical_archives();
found = false(size(names));
verified = false(size(names));
paths = strings(size(names));
messages = strings(size(names));
expectedBytes = NaN(size(names));
actualBytes = NaN(size(names));
expectedSha256 = strings(size(names));
actualSha256 = strings(size(names));

manifestPath = fullfile(cfg.repoRoot, 'provenance', ...
    'canonical_archives_manifest.csv');
if ~isfile(manifestPath)
    error('CMDO:MissingCanonicalManifest', ...
        'Canonical archive manifest not found: %s', manifestPath);
end
manifest = readtable(manifestPath, 'TextType', 'string');

for i = 1:numel(names)
    try
        paths(i) = string(cmdo.find_unique_file(cfg.canonicalRecordDir, names{i}));
        found(i) = true;
        row = manifest.archive == string(names{i});
        if nnz(row) ~= 1
            error('CMDO:CanonicalManifestRow', ...
                'Expected one manifest row for %s; found %d.', names{i}, nnz(row));
        end
        expectedBytes(i) = manifest.size_bytes(row);
        expectedSha256(i) = manifest.sha256(row);
        info = dir(paths(i));
        actualBytes(i) = info.bytes;
        actualSha256(i) = string(cmdo.sha256_file(paths(i)));
        verified(i) = actualBytes(i) == expectedBytes(i) && ...
            strcmpi(actualSha256(i), expectedSha256(i));
        if ~verified(i)
            messages(i) = sprintf( ...
                'Integrity mismatch: expected %d bytes / %s; found %d bytes / %s.', ...
                expectedBytes(i), expectedSha256(i), actualBytes(i), actualSha256(i));
        end
    catch ME
        messages(i) = string(ME.message);
    end
end
report = table(string(names), found, verified, paths, expectedBytes, ...
    actualBytes, expectedSha256, actualSha256, messages, ...
    'VariableNames', {'archive','found','verified','path','expected_bytes', ...
    'actual_bytes','expected_sha256','actual_sha256','message'});
if throwOnMissing && ~all(verified)
    invalid = strjoin(report.archive(~verified), ', ');
    error('CMDO:InvalidCanonicalArchives', ...
        'Missing or invalid canonical archives: %s', invalid);
end
end
