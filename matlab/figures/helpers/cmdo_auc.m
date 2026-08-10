function auc = cmdo_auc(positiveScores, negativeScores)
%CMDO_AUC Pairwise AUC with half credit for ties.

positiveScores = double(positiveScores(:));
negativeScores = double(negativeScores(:));
positiveScores = positiveScores(isfinite(positiveScores));
negativeScores = negativeScores(isfinite(negativeScores));
if isempty(positiveScores) || isempty(negativeScores)
    auc = NaN;
    return;
end
scores = [positiveScores; negativeScores];
ranks = local_tied_rank(scores);
nPos = numel(positiveScores);
nNeg = numel(negativeScores);
auc = (sum(ranks(1:nPos)) - nPos*(nPos+1)/2) / (nPos*nNeg);
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
