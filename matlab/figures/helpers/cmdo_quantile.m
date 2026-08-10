function q = cmdo_quantile(values, probability)
%CMDO_QUANTILE Linear-interpolated sample quantile without extra toolboxes.

values = double(values(:));
values = sort(values(isfinite(values)));
probability = double(probability);
if isempty(values)
    q = NaN(size(probability));
    return;
end
probability = min(max(probability, 0), 1);
index = 1 + (numel(values)-1) .* probability;
lo = floor(index);
hi = ceil(index);
weight = index - lo;
q = (1-weight) .* values(lo) + weight .* values(hi);
end
