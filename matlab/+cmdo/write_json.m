function write_json(path, value)
%WRITE_JSON Write deterministic UTF-8 JSON where supported.

parent = fileparts(path);
if ~isempty(parent) && ~isfolder(parent)
    mkdir(parent);
end
try
    text = jsonencode(value, 'PrettyPrint', true);
catch
    text = jsonencode(value);
end
fid = fopen(path, 'w', 'n', 'UTF-8');
if fid < 0
    error('CMDO:WriteFailed', 'Could not write: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fwrite(fid, text, 'char');
fwrite(fid, newline, 'char');
end
