function path = find_unique_file(root, fileName)
%FIND_UNIQUE_FILE Locate one exact filename and reject ambiguous inputs.

root = char(string(root));
fileName = char(string(fileName));
direct = fullfile(root, fileName);
if isfile(direct)
    path = direct;
    return;
end
if ~isfolder(root)
    error('CMDO:MissingDirectory', 'Directory not found: %s', root);
end
hits = dir(fullfile(root, '**', fileName));
hits = hits(~[hits.isdir]);
if isempty(hits)
    error('CMDO:MissingFile', 'Could not find %s below %s', fileName, root);
end
paths = strings(numel(hits), 1);
for i = 1:numel(hits)
    paths(i) = string(fullfile(hits(i).folder, hits(i).name));
end
paths = unique(paths, 'stable');
if numel(paths) ~= 1
    error('CMDO:AmbiguousFile', 'Found %d copies of %s below %s. Configure a narrower canonicalRecordDir.', ...
        numel(paths), fileName, root);
end
path = char(paths(1));
end
