function [grid, fit, lower, upper] = cmdo_lowess_bootstrap(x, y, cluster, span, nBootstrap, seed)
%CMDO_LOWESS_BOOTSTRAP Local-linear smoother with cluster bootstrap bands.

x = double(x(:));
y = double(y(:));
cluster = string(cluster(:));
keep = isfinite(x) & isfinite(y) & ~ismissing(cluster);
x = x(keep); y = y(keep); cluster = cluster(keep);
if numel(x) < 3
    error('CMDO:TooFewPoints', 'LOWESS requires at least three finite observations.');
end
if nargin < 4 || isempty(span), span = 0.42; end
if nargin < 5 || isempty(nBootstrap), nBootstrap = 300; end
if nargin < 6 || isempty(seed), seed = 20260728; end

grid = linspace(min(x), max(x), 160).';
fit = local_linear(x, y, grid, span);
clusters = unique(cluster, 'stable');
nClusters = numel(clusters);
bootstrapFits = NaN(numel(grid), nBootstrap);

previousRng = rng;
cleanup = onCleanup(@() rng(previousRng));
rng(seed, 'twister');
for b = 1:nBootstrap
    sampled = clusters(randi(nClusters, nClusters, 1));
    xb = []; yb = [];
    for j = 1:nClusters
        mask = cluster == sampled(j);
        xb = [xb; x(mask)]; %#ok<AGROW>
        yb = [yb; y(mask)]; %#ok<AGROW>
    end
    bootstrapFits(:,b) = local_linear(xb, yb, grid, span);
end

lower = column_quantile(bootstrapFits, 0.025);
upper = column_quantile(bootstrapFits, 0.975);
end

function fitted = local_linear(x, y, grid, span)
n = numel(x);
neighbors = max(3, min(n, ceil(span*n)));
fitted = NaN(size(grid));
for i = 1:numel(grid)
    distance = abs(x-grid(i));
    ordered = sort(distance);
    bandwidth = ordered(neighbors);
    if bandwidth <= 0
        positive = ordered(ordered > 0);
        if isempty(positive)
            fitted(i) = mean(y);
            continue;
        end
        bandwidth = positive(1);
    end
    u = min(distance/bandwidth, 1);
    weights = (1-u.^3).^3;
    dx = x-grid(i);
    X = [ones(n,1), dx];
    weightedX = X .* weights;
    normal = X' * weightedX;
    rhs = X' * (weights .* y);
    if rcond(normal) < 1e-12
        fitted(i) = sum(weights.*y) / sum(weights);
    else
        beta = normal \ rhs;
        fitted(i) = beta(1);
    end
end
end

function q = column_quantile(values, probability)
q = NaN(size(values,1),1);
for i = 1:size(values,1)
    q(i) = cmdo_quantile(values(i,:), probability);
end
end
