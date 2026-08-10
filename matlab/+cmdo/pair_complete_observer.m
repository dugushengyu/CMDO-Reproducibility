function result = pair_complete_observer(positiveScores, negativeScores, ...
    transportAUC, support, risk, trueAUC, varargin)
%PAIR_COMPLETE_OBSERVER Native MATLAB analytical core of frozen U6 observer.
%
% This ports the PC_PAIRED_HOEFFDING calculation. Random permutations use
% MATLAB's generator, so exact cross-language replicate matching requires
% supplying/recording a MATLAB-specific seed or explicit future fixtures.

p = inputParser;
addParameter(p, 'Seed', 20260724, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'MaxWeight', 0.35, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'RiskCoefficient', 8.0, @(x) isnumeric(x) && isscalar(x));
addParameter(p, 'DeltaBlock', 0.025, @(x) isnumeric(x) && isscalar(x));
parse(p, varargin{:});
opt = p.Results;

positiveScores = double(positiveScores(:));
negativeScores = double(negativeScores(:));
if numel(positiveScores) ~= numel(negativeScores) || mod(numel(positiveScores),2) ~= 0
    error('CMDO:PairCompleteCounts', ...
        'Pair-complete observer requires equal, even positive/negative counts.');
end
if isempty(positiveScores) || any(~isfinite([positiveScores;negativeScores]))
    error('CMDO:InvalidScores', 'Scores must be nonempty and finite.');
end

previousRng = rng;
cleanup = onCleanup(@() rng(previousRng));
rng(opt.Seed, 'twister');
positiveScores = positiveScores(randperm(numel(positiveScores)));
negativeScores = negativeScores(randperm(numel(negativeScores)));
half = numel(positiveScores)/2;

blocks = struct();
blocks.AA = {positiveScores(1:half), negativeScores(1:half)};
blocks.AB = {positiveScores(1:half), negativeScores(half+1:end)};
blocks.BA = {positiveScores(half+1:end), negativeScores(1:half)};
blocks.BB = {positiveScores(half+1:end), negativeScores(half+1:end)};
names = {'AA','AB','BA','BB'};
opposite = struct('AA','BB','BB','AA','AB','BA','BA','AB');

blockAUC = struct();
blockVariance = struct();
sensors = struct();
for i = 1:numel(names)
    name = names{i};
    scores = blocks.(name);
    [blockAUC.(name), blockVariance.(name)] = ...
        cmdo.auc_and_variance(scores{1}, scores{2});
    sensors.(name) = paired_sensor(scores{1}, scores{2});
end
[fullAUC, fullVariance] = cmdo.auc_and_variance(positiveScores, negativeScores);
blockValues = cellfun(@(n) blockAUC.(n), names);
identityResidual = abs(mean(blockValues)-fullAUC);

trueBiasSquared = (double(transportAUC)-double(trueAUC))^2;
weights = struct();
upperBounds = struct();
coverage = false(1,numel(names));
geometry = false(1,numel(names));
sensorGaps = zeros(1,numel(names));
estimates = zeros(1,numel(names));
for i = 1:numel(names)
    name = names{i};
    sensor = sensors.(opposite.(name));
    radius = min(1, sqrt(log(2/opt.DeltaBlock)/(2*sensor.n)));
    upper = min(1, abs(sensor.value-transportAUC)+radius)^2;
    variance = blockVariance.(name);
    weight = double(support) * min(opt.MaxWeight, ...
        variance/(variance+upper+opt.RiskCoefficient*double(risk)+1e-12));
    trueRisk = (1-weight)^2*variance + weight^2*trueBiasSquared;

    weights.(name) = weight;
    upperBounds.(name) = upper;
    coverage(i) = upper+1e-15 >= trueBiasSquared;
    geometry(i) = trueRisk <= variance+1e-14;
    sensorGaps(i) = abs(sensor.value-transportAUC);
    estimates(i) = (1-weight)*blockAUC.(name) + weight*transportAUC;
end
weightValues = cellfun(@(n) weights.(n), names);
upperValues = cellfun(@(n) upperBounds.(n), names);

result = struct();
result.estimate = mean(estimates);
result.direct_full_auc = fullAUC;
result.direct_full_variance = fullVariance;
result.identity_residual = identityResidual;
result.mean_weight = mean(weightValues);
result.max_weight = max(weightValues);
result.simultaneous_coverage = all(coverage);
result.block_no_harm_rate = mean(geometry);
result.mean_bias_upper_sq = mean(upperValues);
result.mean_sensor_abs_gap = mean(sensorGaps);
result.weights = weights;
end

function sensor = paired_sensor(positiveScores, negativeScores)
n = min(numel(positiveScores), numel(negativeScores));
p = positiveScores(randperm(numel(positiveScores), n));
q = negativeScores(randperm(numel(negativeScores), n));
values = double(p > q) + 0.5*double(p == q);
sensor = struct('value',mean(values), 'variance',0, 'n',n);
if n > 1
    sensor.variance = var(values,0);
end
end
