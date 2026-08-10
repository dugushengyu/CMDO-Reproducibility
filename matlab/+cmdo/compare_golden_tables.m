function report = compare_golden_tables(expected, actual, keyColumns, tolerance, throwOnMismatch)
%COMPARE_GOLDEN_TABLES Compare a MATLAB port output against frozen CSV truth.

if nargin < 3 || isempty(keyColumns), keyColumns = {}; end
if nargin < 4 || isempty(tolerance), tolerance = 1e-12; end
if nargin < 5, throwOnMismatch = false; end
if ischar(expected) || isstring(expected)
    expected = readtable(expected, 'VariableNamingRule','preserve', 'TextType','string');
end
if ischar(actual) || isstring(actual)
    actual = readtable(actual, 'VariableNamingRule','preserve', 'TextType','string');
end
expectedNames = string(expected.Properties.VariableNames);
actualNames = string(actual.Properties.VariableNames);
if ~isequal(expectedNames, actualNames)
    error('CMDO:SchemaMismatch', 'Golden and candidate table schemas differ.');
end
if height(expected) ~= height(actual)
    error('CMDO:RowCountMismatch', 'Golden rows=%d; candidate rows=%d.', ...
        height(expected), height(actual));
end
if ~isempty(keyColumns)
    expected = sortrows(expected, keyColumns);
    actual = sortrows(actual, keyColumns);
end

n = width(expected);
column = expectedNames(:);
kind = strings(n,1);
passed = false(n,1);
max_abs_difference = NaN(n,1);
mismatch_count = zeros(n,1);
for j = 1:n
    name = expected.Properties.VariableNames{j};
    e = expected.(name);
    a = actual.(name);
    if isnumeric(e) || islogical(e)
        kind(j) = "numeric";
        e = double(e); a = double(a);
        sameNaN = isnan(e) & isnan(a);
        difference = abs(e-a);
        difference(sameNaN) = 0;
        bad = difference > tolerance | xor(isnan(e),isnan(a));
        finiteDifference = difference(isfinite(difference));
        if isempty(finiteDifference)
            max_abs_difference(j) = 0;
        else
            max_abs_difference(j) = max(finiteDifference);
        end
        mismatch_count(j) = nnz(bad);
    else
        kind(j) = "text";
        bad = string(e) ~= string(a);
        mismatch_count(j) = nnz(bad);
    end
    passed(j) = mismatch_count(j) == 0;
end
report = table(column,kind,passed,max_abs_difference,mismatch_count);
if throwOnMismatch && ~all(passed)
    failed = strjoin(column(~passed), ', ');
    error('CMDO:GoldenMismatch', 'Golden comparison failed for columns: %s', failed);
end
end
