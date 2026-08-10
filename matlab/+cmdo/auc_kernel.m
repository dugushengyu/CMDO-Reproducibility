function matrix = auc_kernel(positiveScores, negativeScores)
%AUC_KERNEL Pairwise AUC comparison matrix with half credit for ties.

positiveScores = double(positiveScores(:));
negativeScores = double(negativeScores(:));
if any(~isfinite(positiveScores)) || any(~isfinite(negativeScores))
    error('CMDO:NonFiniteScores', 'AUC scores must be finite.');
end
matrix = double(positiveScores > negativeScores.') + ...
    0.5 .* double(positiveScores == negativeScores.');
end
