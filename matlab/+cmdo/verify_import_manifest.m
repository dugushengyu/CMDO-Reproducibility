function report = verify_import_manifest(throwOnMismatch)
%VERIFY_IMPORT_MANIFEST Verify normalized repository copies of Drive code.

if nargin < 1
    throwOnMismatch = false;
end
root = cmdo.repo_root();
manifestPath = fullfile(root, 'provenance', 'drive_import_manifest.csv');
if ~isfile(manifestPath)
    error('CMDO:MissingManifest', 'Import manifest not found: %s', manifestPath);
end
M = readtable(manifestPath, 'TextType', 'string');
actual = strings(height(M), 1);
exists = false(height(M), 1);
matches = false(height(M), 1);
for i = 1:height(M)
    path = fullfile(root, char(M.repository_path(i)));
    exists(i) = isfile(path);
    if exists(i)
        actual(i) = string(cmdo.sha256_file(path));
        matches(i) = strcmpi(actual(i), M.repository_sha256(i));
    end
end
report = table(M.repository_path, exists, M.repository_sha256, actual, matches, ...
    'VariableNames', {'repository_path','exists','expected_sha256','actual_sha256','matches'});
if throwOnMismatch && ~all(matches)
    error('CMDO:ImportHashMismatch', '%d imported source files failed repository hash verification.', nnz(~matches));
end
end
