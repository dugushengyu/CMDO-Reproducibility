function value = cmdo_summary_value(T, identifier, valueColumn)
%CMDO_SUMMARY_VALUE Select one scalar from a method/candidate summary table.

names = string(T.Properties.VariableNames);
idCandidates = ["method","candidate","method_code","observer","selected_method"];
idIndex = find(ismember(lower(names), lower(idCandidates)), 1, 'first');
if isempty(idIndex)
    error('CMDO:MissingIdentifierColumn', 'No method/candidate identifier column was found.');
end
valueIndex = find(strcmpi(names, string(valueColumn)), 1, 'first');
if isempty(valueIndex)
    error('CMDO:MissingValueColumn', 'Column not found: %s', valueColumn);
end
idName = T.Properties.VariableNames{idIndex};
valueName = T.Properties.VariableNames{valueIndex};
mask = strcmpi(string(T.(idName)), string(identifier));
if nnz(mask) ~= 1
    error('CMDO:SummarySelection', 'Expected one row for %s; found %d.', identifier, nnz(mask));
end
raw = T.(valueName)(mask);
value = double(raw(1));
end
