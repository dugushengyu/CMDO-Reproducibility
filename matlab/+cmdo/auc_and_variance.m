function [auc, variance] = auc_and_variance(positiveScores, negativeScores)
%AUC_AND_VARIANCE U-statistic AUC and row/column variance approximation.

matrix = cmdo.auc_kernel(positiveScores, negativeScores);
auc = mean(matrix, 'all');
row = mean(matrix, 2);
column = mean(matrix, 1).';
if numel(row) > 1
    rowVariance = var(row, 0);
else
    rowVariance = 0;
end
if numel(column) > 1
    columnVariance = var(column, 0);
else
    columnVariance = 0;
end
variance = max(0, rowVariance/numel(row) + columnVariance/numel(column));
end
