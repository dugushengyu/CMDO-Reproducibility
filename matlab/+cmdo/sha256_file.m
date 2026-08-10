function hash = sha256_file(path)
%SHA256_FILE Compute SHA-256 over the exact bytes of a file.

path = char(string(path));
if ~isfile(path)
    error('CMDO:MissingFile', 'File not found: %s', path);
end

digest = java.security.MessageDigest.getInstance('SHA-256');
fid = fopen(path, 'rb');
if fid < 0
    error('CMDO:OpenFailed', 'Could not open file: %s', path);
end
cleanup = onCleanup(@() fclose(fid));

while true
    bytes = fread(fid, 1024 * 1024, '*uint8');
    if isempty(bytes)
        break;
    end
    digest.update(typecast(bytes(:), 'int8'));
end

raw = typecast(digest.digest(), 'uint8');
hash = lower(reshape(dec2hex(raw, 2).', 1, []));
end
