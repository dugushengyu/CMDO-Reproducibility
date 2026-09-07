function T = ANALYZE_U10_SAFE_REUSE()
%ANALYZE_U10_SAFE_REUSE Read-only diagnostic against frozen U10 summaries.
%
% This analysis is explicitly post-completion. It does not alter U10.
% It computes the oracle role-separated safe cap from frozen target truth
% and compares it with the observed mean shared weight and completed risks.
%
% The main diagnostic is whether a modest mean weight below the oracle cap
% can still be harmful under same-audit adaptation. If so, weight magnitude
% alone is not sufficient; dependence must enter the safety condition.

    moduleDir = fileparts(mfilename('fullpath'));
    repoRoot = fileparts(moduleDir);
    src = fullfile(repoRoot, 'U10_Prospective_ECG', ...
        '02_Posthoc_Diagnostics', 'U10_DEPENDENCE_DECOMPOSITION.csv');

    if ~isfile(src)
        error('ANALYZE_U10_SAFE_REUSE:MissingSource', ...
            'Frozen U10 source not found: %s', src);
    end

    U = readtable(src, 'VariableNamingRule', 'preserve');

    theta = U.theta;
    B = U.B;
    N = U.N;
    m = U.budget;

    % Exact finite-population variance of simple-random-sample accuracy.
    V_fpc = theta .* (1-theta) .* (N-m) ./ (m .* (N-1));
    Lambda_oracle = (B.^2) ./ V_fpc;
    omega_oracle = min(1, 2 ./ (1 + Lambda_oracle));

    mean_w_shared = U.shared_constant_mean_weight;
    below_oracle_cap = mean_w_shared <= omega_oracle + 1e-12;
    shared_harm = U.shared_adaptive_gain_pct < 0;
    matched_fixed_benefit = U.shared_constant_mean_gain_pct > 0;
    fixed_benefit_to_adaptive_harm = matched_fixed_benefit & shared_harm;

    T = table(U.dataset, m, theta, B, V_fpc, Lambda_oracle, ...
        omega_oracle, mean_w_shared, below_oracle_cap, ...
        U.shared_constant_mean_gain_pct, U.shared_adaptive_gain_pct, ...
        U.shared_permuted_weight_gain_pct, ...
        fixed_benefit_to_adaptive_harm, ...
        'VariableNames', { ...
        'dataset','budget','theta','B','V_fpc','Lambda_oracle', ...
        'omega_oracle','mean_w_shared','below_oracle_cap', ...
        'matched_fixed_gain_pct','shared_adaptive_gain_pct', ...
        'permuted_weight_gain_pct','fixed_benefit_to_adaptive_harm'});

    fprintf('============================================================\n');
    fprintf(' U10 oracle safe-cap diagnostic (POST-COMPLETION ONLY)\n');
    fprintf('============================================================\n');
    disp(T);

    fprintf('\nStates with mean shared weight <= oracle role-separated cap: %d/%d\n', ...
        sum(below_oracle_cap), height(T));
    fprintf('States with matched-fixed benefit:                         %d/%d\n', ...
        sum(matched_fixed_benefit), height(T));
    fprintf('States with shared-adaptive harm:                          %d/%d\n', ...
        sum(shared_harm), height(T));
    fprintf('Fixed benefit -> adaptive harm:                            %d/%d\n', ...
        sum(fixed_benefit_to_adaptive_harm), height(T));

    if all(below_oracle_cap) && any(shared_harm)
        fprintf(['\nKEY DIAGNOSTIC: all mean shared weights are below the oracle\n' ...
                 'role-separated cap, yet shared-adaptive harmful states occur.\n' ...
                 'This is consistent with the coupling-correction term being\n' ...
                 'scientifically necessary; a cap alone cannot certify same-audit reuse.\n']);
    end

    outDir = fullfile(moduleDir, 'outputs');
    if ~isfolder(outDir)
        mkdir(outDir);
    end
    writetable(T, fullfile(outDir, 'U10_SAFE_REUSE_ORACLE_DIAGNOSTIC.csv'));
end
