function T = read_canonical_table(stageDir, fileName)
%READ_CANONICAL_TABLE Read one uniquely named CSV, including CSV.GZ files.

path = cmdo.find_unique_file(stageDir, fileName);
if endsWith(lower(path), '.gz')
    plainPath = extractBefore(path, strlength(path) - 2);
    plainPath = char(plainPath);
    if ~isfile(plainPath)
        outputs = gunzip(path, fileparts(path));
        plainPath = outputs{1};
    end
    path = plainPath;
end
T = readtable(path, 'VariableNamingRule', 'preserve', 'TextType', 'string');
end
