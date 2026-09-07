function T = PROBE_U10_NONORACLE_TRIGGER()
%PROBE_U10_NONORACLE_TRIGGER Exact binomial decision-audit trigger diagnostic.
%
% This is a post-completion theory diagnostic using only frozen U10 theta/H
% values as parameter settings. It does NOT claim that the actual finite-cohort
% U10 sampling design is iid binomial. The purpose is to ask whether the
% simple Theorem-3 construction (independent decision/evaluation split + exact
% Clopper-Pearson confidence set) is operationally non-vacuous at U10-like
% effect sizes and budgets.
%
% Trigger probabilities are enumerated exactly over the decision-sample
% binomial count distribution; no Monte Carlo is used.

    moduleDir = fileparts(mfilename('fullpath'));
    repoRoot = fileparts(moduleDir);
    src = fullfile(repoRoot,'U10_Prospective_ECG','02_Posthoc_Diagnostics', ...
        'U10_DEPENDENCE_DECOMPOSITION.csv');
    U = readtable(src,'VariableNamingRule','preserve');

    alphaGrid = [0.05 0.10];
    fracGrid = 0.05:0.05:0.80;
    rows = [];

    % One row per cohort/budget/alpha, retaining the split with maximum trigger.
    for i = 1:height(U)
        theta = U.theta(i);
        H = U.H(i);
        M = U.budget(i);

        for ia = 1:numel(alphaGrid)
            alpha = alphaGrid(ia);
            bestTrigger = -1;
            bestInvalid = NaN;
            bestFrac = NaN;
            bestMs = NaN;
            bestMe = NaN;

            for f = fracGrid
                ms = max(1,round(M*f));
                if ms >= M, continue; end
                me = M-ms;
                delta = ms/M;

                triggerProb = 0;
                invalidProb = 0;

                for k = 0:ms
                    pk = binom_pmf_exact(k,ms,theta);
                    [L,Uci] = clopper_pearson(k,ms,alpha);
                    covered = (theta >= L) && (theta <= Uci);

                    if L <= 0 || Uci >= 1
                        LambdaU = Inf;
                    else
                        a = me*(H-L)^2/(L*(1-L));
                        b = me*(H-Uci)^2/(Uci*(1-Uci));
                        LambdaU = max(a,b);
                    end

                    feasible = isfinite(LambdaU) && ...
                        (delta <= 1/(1+LambdaU) + 1e-14);
                    if feasible
                        triggerProb = triggerProb + pk;
                        if ~covered
                            invalidProb = invalidProb + pk;
                        end
                    end
                end

                if triggerProb > bestTrigger
                    bestTrigger = triggerProb;
                    bestInvalid = invalidProb;
                    bestFrac = f;
                    bestMs = ms;
                    bestMe = me;
                end
            end

            rows = [rows; i M alpha bestFrac bestMs bestMe bestTrigger bestInvalid]; %#ok<AGROW>
        end
    end

    T = array2table(rows,'VariableNames', ...
        {'u10_row','full_budget','alpha','best_decision_fraction', ...
         'decision_budget','evaluation_budget','max_trigger_probability', ...
         'global_invalid_certificate_probability'});
    T.dataset = U.dataset(T.u10_row);
    T = movevars(T,'dataset','Before','full_budget');

    fprintf('============================================================\n');
    fprintf(' U10-like non-oracle full-budget certificate trigger probe\n');
    fprintf(' iid binomial decision/evaluation design; post-completion only\n');
    fprintf('============================================================\n');
    disp(T);

    outDir = fullfile(moduleDir,'outputs');
    if ~isfolder(outDir), mkdir(outDir); end
    writetable(T,fullfile(outDir,'U10_NONORACLE_TRIGGER_PROBE.csv'));
end

function p = binom_pmf_exact(k,n,theta)
    if theta == 0
        p = double(k==0); return;
    elseif theta == 1
        p = double(k==n); return;
    end
    logc = gammaln(n+1)-gammaln(k+1)-gammaln(n-k+1);
    p = exp(logc + k*log(theta) + (n-k)*log1p(-theta));
end

function [L,U] = clopper_pearson(k,n,alpha)
    if k == 0
        L = 0;
    else
        L = betaincinv(alpha/2,k,n-k+1);
    end
    if k == n
        U = 1;
    else
        U = betaincinv(1-alpha/2,k+1,n-k);
    end
end
