function summary = RUN_U10_EXACT_FINITE_COHORT_CHECK(varargin)
%RUN_U10_EXACT_FINITE_COHORT_CHECK Exact finite-cohort U10 shared-audit check.
%
%   RUN_U10_EXACT_FINITE_COHORT_CHECK
%   RUN_U10_EXACT_FINITE_COHORT_CHECK('VerifyOnly',true,'Strict',true)
%
% This reviewer-facing diagnostic evaluates the locked scalar shared-audit
% rule exactly under finite-cohort simple random sampling. It uses only the
% tracked U10 post-completion decomposition file for N, theta and H and does
% not access raw patient records.
%
% The locked rule is
%   Vhat = max(D*(1-D)/m, 1e-8)
%   W    = min(0.35, Vhat/(Vhat + (D-H)^2))
%   T    = (1-W)*D + W*H
%
% where D = X/m and X ~ Hypergeom(N,K,m), K = N*theta.
%
% The check is conditional on the frozen U10 binary correctness rosters and
% does not alter the prespecified U10 mechanism verdict.

p = inputParser;
addParameter(p,'RepoRoot','',@(x)ischar(x) || isstring(x));
addParameter(p,'VerifyOnly',true,@(x)islogical(x) || isnumeric(x));
addParameter(p,'Strict',true,@(x)islogical(x) || isnumeric(x));
parse(p,varargin{:});
opt = p.Results;

if strlength(string(opt.RepoRoot)) == 0
    thisFile = mfilename('fullpath');
    repoRoot = fileparts(thisFile);
else
    repoRoot = char(opt.RepoRoot);
end

src = fullfile(repoRoot,'U10_Prospective_ECG','02_Posthoc_Diagnostics', ...
    'U10_DEPENDENCE_DECOMPOSITION.csv');
outCsv = fullfile(repoRoot,'source_data','figure4_submission', ...
    'U10_ExactFiniteCohort_Check_v1.csv');

assert(isfile(src),'Missing tracked U10 decomposition: %s',src);
T = readtable(src,'VariableNamingRule','preserve','TextType','string');

need = {'dataset','budget','N','theta','H'};
for i = 1:numel(need)
    assert(any(strcmp(T.Properties.VariableNames,need{i})), ...
        'Missing required U10 field: %s',need{i});
end

nState = height(T);
assert(nState == 8,'Expected eight Georgia/CPSC U10 cohort-budget states.');

Dset = strings(nState,1);
budget = zeros(nState,1);
N = zeros(nState,1);
K = zeros(nState,1);
theta = zeros(nState,1);
Hist = zeros(nState,1);
B = zeros(nState,1);
V = zeros(nState,1);
lambda = zeros(nState,1);
meanWeight = zeros(nState,1);
wStar = zeros(nState,1);
adaptiveMSE = zeros(nState,1);
matchedFixedMSE = zeros(nState,1);
adaptiveNormRisk = zeros(nState,1);
matchedFixedNormRisk = zeros(nState,1);
independentWeightMSE = zeros(nState,1);
independentWeightNormRisk = zeros(nState,1);

for i = 1:nState
    Dset(i) = string(T.dataset(i));
    budget(i) = double(T.budget(i));
    N(i) = double(T.N(i));
    K(i) = round(N(i) * double(T.theta(i)));
    theta(i) = K(i) / N(i);
    Hist(i) = double(T.H(i));
    B(i) = Hist(i) - theta(i);

    m = budget(i);
    xLo = max(0, m - (N(i)-K(i)));
    xHi = min(m, K(i));
    x = (xLo:xHi)';

    logp = local_logchoose(K(i),x) + ...
        local_logchoose(N(i)-K(i),m-x) - ...
        local_logchoose(N(i),m);
    logp = logp - max(logp);
    prob = exp(logp);
    prob = prob ./ sum(prob);

    D = x ./ m;
    Vhat = max(D .* (1-D) ./ m, 1e-8);
    W = min(0.35, Vhat ./ (Vhat + (D-Hist(i)).^2));

    errAdaptive = (1-W).*D + W.*Hist(i) - theta(i);
    adaptiveMSE(i) = sum(prob .* errAdaptive.^2);

    meanWeight(i) = sum(prob .* W);
    errFixed = (1-meanWeight(i)).*D + meanWeight(i).*Hist(i) - theta(i);
    matchedFixedMSE(i) = sum(prob .* errFixed.^2);

    V(i) = theta(i)*(1-theta(i))/m * (N(i)-m)/(N(i)-1);
    lambda(i) = B(i)^2 / V(i);
    wStar(i) = 1 / (1 + lambda(i));

    adaptiveNormRisk(i) = adaptiveMSE(i) / V(i);
    matchedFixedNormRisk(i) = matchedFixedMSE(i) / V(i);

    % Idealized independent-weight construction: preserve the exact marginal
    % distribution of W while making it independent of the direct error.
    Ew = meanWeight(i);
    Ew2 = sum(prob .* W.^2);
    e = D - theta(i);
    Ee = sum(prob .* e);
    Ee2 = sum(prob .* e.^2);
    independentWeightMSE(i) = ...
        (1 - 2*Ew + Ew2)*Ee2 + ...
        Ew2*B(i)^2 + ...
        2*(Ew-Ew2)*B(i)*Ee;
    independentWeightNormRisk(i) = independentWeightMSE(i) / V(i);
end

wGlobal = 1 / mean(1 + lambda);

Hcontrib = zeros(nState,1);
Acontrib = zeros(nState,1);
Ccontrib = zeros(nState,1);
independentC = zeros(nState,1);

for i = 1:nState
    r = @(w) (1-w).^2 + lambda(i).*w.^2;
    Hcontrib(i) = r(wGlobal) - r(wStar(i));
    Acontrib(i) = r(meanWeight(i)) - r(wStar(i));
    Ccontrib(i) = adaptiveNormRisk(i) - r(meanWeight(i));
    independentC(i) = independentWeightNormRisk(i) - r(meanWeight(i));
end

summary = table( ...
    Dset,budget,N,K,theta,Hist,B,V,lambda,meanWeight,wStar, ...
    repmat(wGlobal,nState,1),adaptiveMSE,matchedFixedMSE, ...
    adaptiveNormRisk,matchedFixedNormRisk,Hcontrib,Acontrib,Ccontrib, ...
    independentWeightMSE,independentWeightNormRisk,independentC, ...
    'VariableNames',{ ...
    'dataset','budget','N','K','theta','H','B','V','lambda', ...
    'mean_weight','w_star','w_global','adaptive_mse','matched_fixed_mse', ...
    'adaptive_norm_risk','matched_fixed_norm_risk','H_contribution', ...
    'A_contribution','C_contribution','independent_weight_mse', ...
    'independent_weight_norm_risk','independent_C_contribution'});

Hagg = mean(Hcontrib);
Aagg = mean(Acontrib);
Cagg = mean(Ccontrib);
margin = Hagg - Aagg - Cagg;
Cind = mean(independentC);
marginInd = Hagg - Aagg - Cind;

fprintf('\n============================================================\n');
fprintf(' U10 EXACT FINITE-COHORT CHECK\n');
fprintf('============================================================\n');
fprintf('H                       : %.8f\n',Hagg);
fprintf('A                       : %.8f\n',Aagg);
fprintf('C shared                : %.8f\n',Cagg);
fprintf('H-(A+C) shared          : %.8f\n',margin);
fprintf('C independent-weight    : %.8f\n',Cind);
fprintf('H-(A+C) independent     : %.8f\n',marginInd);
fprintf('Adaptive > matched fixed: %d/%d\n', ...
    nnz(adaptiveNormRisk > matchedFixedNormRisk),nState);
fprintf('Fixed benefit -> harm   : %d/%d\n', ...
    nnz(matchedFixedNormRisk < 1 & adaptiveNormRisk > 1),nState);

if logical(opt.VerifyOnly)
    assert(isfile(outCsv),'Missing tracked exact-check CSV: %s',outCsv);
    R = readtable(outCsv,'VariableNamingRule','preserve','TextType','string');
    assert(height(R)==height(summary),'Exact-check state count mismatch.');
    assert(all(string(R.dataset)==summary.dataset),'Exact-check dataset mismatch.');
    assert(all(double(R.budget)==summary.budget),'Exact-check budget mismatch.');

    numericNames = summary.Properties.VariableNames(2:end);
    for j = 1:numel(numericNames)
        a = double(R.(numericNames{j}));
        b = double(summary.(numericNames{j}));
        scale = max(1,max(abs(b),[],'omitnan'));
        assert(max(abs(a-b),[],'omitnan') <= 5e-10*scale, ...
            'Exact-check mismatch in column %s.',numericNames{j});
    end
else
    writetable(summary,outCsv);
end

if logical(opt.Strict)
    assert(abs(Hagg - 0.0893981749753321) < 5e-12,'Exact H fingerprint mismatch.');
    assert(abs(Aagg - 0.0136448603600676) < 5e-12,'Exact A fingerprint mismatch.');
    assert(abs(Cagg - 0.219749173064403) < 5e-12,'Exact C fingerprint mismatch.');
    assert(abs(margin - (-0.143995858449139)) < 5e-12,'Exact margin fingerprint mismatch.');
    assert(abs(Cind - 0.0310440794801617) < 5e-12,'Independent-weight C fingerprint mismatch.');
    assert(abs(marginInd - 0.0447092351351028) < 5e-12,'Independent-weight margin fingerprint mismatch.');
    assert(nnz(adaptiveNormRisk > matchedFixedNormRisk)==8, ...
        'Expected adaptive risk to exceed matched-fixed risk in 8/8 exact states.');
    assert(nnz(matchedFixedNormRisk < 1 & adaptiveNormRisk > 1)==5, ...
        'Expected fixed-benefit to adaptive-harm reversal in 5/8 exact states.');
end

end

function y = local_logchoose(n,k)
% Base-MATLAB log binomial coefficient, vectorized in k.
y = -inf(size(k));
ok = (k >= 0) & (k <= n) & (abs(k-round(k)) < 1e-12);
kk = k(ok);
y(ok) = gammaln(n+1) - gammaln(kk+1) - gammaln(n-kk+1);
end
