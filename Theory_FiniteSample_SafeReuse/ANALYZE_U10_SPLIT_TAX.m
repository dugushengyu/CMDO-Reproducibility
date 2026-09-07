function T = ANALYZE_U10_SPLIT_TAX()
%ANALYZE_U10_SPLIT_TAX Oracle post-completion split-tax diagnostic.
%
% Uses frozen U10 truth only to ask whether a half-budget decision/evaluation
% split could in principle be certified against the original full-budget
% direct estimator under the draft Theorem D geometry.
%
% This is NOT a prospective rule and does not modify U10.

    moduleDir = fileparts(mfilename('fullpath'));
    repoRoot = fileparts(moduleDir);
    src = fullfile(repoRoot, 'U10_Prospective_ECG', ...
        '02_Posthoc_Diagnostics', 'U10_DEPENDENCE_DECOMPOSITION.csv');

    U = readtable(src, 'VariableNamingRule', 'preserve');

    theta = U.theta;
    B = U.B;
    N = U.N;
    M = U.budget;
    me = M/2;

    Vfull = theta .* (1-theta) .* (N-M) ./ (M .* (N-1));
    Veval = theta .* (1-theta) .* (N-me) ./ (me .* (N-1));

    Lambda_eval = (B.^2) ./ Veval;
    delta = 1 - Vfull ./ Veval;
    feasibility_limit = 1 ./ (1 + Lambda_eval);
    feasible = delta <= feasibility_limit + 1e-12;

    wLower = nan(height(U),1);
    wUpper = nan(height(U),1);
    idx = feasible;
    disc = 1 - (1+Lambda_eval(idx)).*delta(idx);
    wLower(idx) = (1 - sqrt(max(0,disc))) ./ (1+Lambda_eval(idx));
    wUpper(idx) = (1 + sqrt(max(0,disc))) ./ (1+Lambda_eval(idx));
    wUpper = min(1,wUpper);

    T = table(U.dataset, M, me, Lambda_eval, delta, feasibility_limit, ...
        feasible, wLower, wUpper, ...
        'VariableNames', {'dataset','full_budget','eval_half_budget', ...
        'Lambda_eval_oracle','split_tax_delta','max_certifiable_split_tax', ...
        'full_budget_certificate_feasible','w_lower','w_upper'});

    fprintf('============================================================\n');
    fprintf(' U10 half-split full-budget safety feasibility (ORACLE)\n');
    fprintf('============================================================\n');
    disp(T);
    fprintf('\nFeasible states: %d/%d\n', sum(feasible), height(T));

    outDir = fullfile(moduleDir, 'outputs');
    if ~isfolder(outDir)
        mkdir(outDir);
    end
    writetable(T, fullfile(outDir, 'U10_HALF_SPLIT_TAX_FEASIBILITY.csv'));
end
