function rho = cmdo_spearman(x, y)
%CMDO_SPEARMAN Spearman rank correlation with tied ranks.

x = double(x(:));
y = double(y(:));
keep = isfinite(x) & isfinite(y);
x = x(keep); y = y(keep);
if numel(x) < 2
    rho = NaN;
    return;
end
rx = local_tied_rank(x);
ry = local_tied_rank(y);
C = corrcoef(rx, ry);
rho = C(1,2);
end

function ranks = local_tied_rank(values)
[sorted, order] = sort(values);
ranks = zeros(size(values));
i = 1;
while i <= numel(sorted)
    j = i;
    while j < numel(sorted) && sorted(j+1) == sorted(i)
        j = j + 1;
    end
    ranks(order(i:j)) = (i+j)/2;
    i = j + 1;
end
end
