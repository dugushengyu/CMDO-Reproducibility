function out = VERIFY_THEORY_V1()
%VERIFY_THEORY_V1 Deterministic checks for THEORY_RESULT_V1.
%
% This script verifies:
%   1) Theorem 1 counterexample over several borrowing caps.
%   2) Theorem 3 quadratic roots and certifiability boundary.
%   3) Binary-accuracy endpoint formula for Lambda_U.
%
% It does not modify frozen CMDO artifacts.

    fprintf('============================================================\n');
    fprintf(' CMDO finite-sample safe-reuse theory v1 verification\n');
    fprintf('============================================================\n');

    %% Theorem 1: magnitude-only impossibility
    omegaGrid = [0.05 0.10 0.35 0.80 0.99];
    T1 = table('Size',[numel(omegaGrid),7], ...
        'VariableTypes',repmat({'double'},1,7), ...
        'VariableNames',{'omega','r','a','Lambda','fixed_safe_cap', ...
                         'adaptive_excess_risk','min_fixed_gain'});

    for i = 1:numel(omegaGrid)
        omega = omegaGrid(i);
        rUpper = sqrt(2/omega - 1);
        r = 0.5*(1 + rUpper); % strictly between 1 and rUpper
        a = min(0.20, 0.49/r);
        B = r*a;
        V = a^2;
        Lambda = B^2/V;
        fixedCap = 2/(1+Lambda);

        w = linspace(0,omega,1001);
        fixedExcess = V .* (-2*w + (1+Lambda).*w.^2);
        minFixedGain = -max(fixedExcess); % >=0 means no fixed harm

        adaptiveRisk = 0.5*((a + omega*(B-a))^2 + a^2);
        adaptiveExcess = adaptiveRisk - V;

        assert(omega < fixedCap + 1e-12, ...
            'Theorem 1 construction failed: omega is not under fixed safe cap.');
        assert(max(fixedExcess) <= 1e-12, ...
            'Theorem 1 construction failed: a fixed weight is harmful.');
        assert(adaptiveExcess > 0, ...
            'Theorem 1 construction failed: adaptive rule is not harmful.');

        T1{i,:} = [omega r a Lambda fixedCap adaptiveExcess minFixedGain];
    end

    fprintf('\n[Theorem 1] magnitude-only impossibility checks\n');
    disp(T1);

    %% Theorem 3: full-budget certifiability boundary
    lambdaGrid = [0 0.25 0.5 1 2 4 8]';
    deltaGrid = [0.10 0.25 0.50]';
    rows = [];
    for i = 1:numel(lambdaGrid)
        L = lambdaGrid(i);
        for j = 1:numel(deltaGrid)
            delta = deltaGrid(j);
            margin = 1/(1+L) - delta;
            feasible = margin >= -1e-12;
            if feasible
                disc = max(0,1-(1+L)*delta);
                wLo = (1-sqrt(disc))/(1+L);
                wHi = (1+sqrt(disc))/(1+L);
                wStar = 1/(1+L);
                qStar = (1+L)*wStar^2 - 2*wStar + delta;
                assert(qStar <= 1e-12, 'Feasible quadratic has positive minimum.');
                assert(wLo <= wHi + 1e-12, 'Invalid certified interval.');
            else
                wLo = NaN; wHi = NaN;
                wStar = 1/(1+L);
                qStar = (1+L)*wStar^2 - 2*wStar + delta;
                assert(qStar > -1e-12, 'Infeasible quadratic unexpectedly negative.');
            end
            rows = [rows; L delta margin double(feasible) wLo wHi wStar qStar]; %#ok<AGROW>
        end
    end
    T3 = array2table(rows,'VariableNames', ...
        {'Lambda_U','delta','certifiability_margin','feasible', ...
         'w_lower','w_upper','w_star','quadratic_at_w_star'});

    fprintf('\n[Theorem 3] certifiability-boundary checks\n');
    disp(T3);

    %% Binary endpoint maximum check
    Hgrid = [0.20 0.50 0.95];
    intervals = [0.10 0.40; 0.30 0.80; 0.80 0.99];
    maxErr = 0;
    for h = Hgrid
        for k = 1:size(intervals,1)
            L = intervals(k,1); U = intervals(k,2);
            t = linspace(L,U,200001);
            f = (h-t).^2 ./ (t.*(1-t));
            brute = max(f);
            endpoint = max((h-L)^2/(L*(1-L)), (h-U)^2/(U*(1-U)));
            maxErr = max(maxErr, abs(brute-endpoint));
        end
    end
    assert(maxErr < 1e-8, 'Endpoint formula verification failed.');
    fprintf('\n[Binary corollary] endpoint maximum error = %.3g\n', maxErr);

    out = struct();
    out.theorem1 = T1;
    out.theorem3 = T3;
    out.binary_endpoint_max_error = maxErr;

    outDir = fullfile(fileparts(mfilename('fullpath')),'outputs');
    if ~isfolder(outDir), mkdir(outDir); end
    writetable(T1,fullfile(outDir,'THEOREM1_COUNTEREXAMPLE_CHECKS.csv'));
    writetable(T3,fullfile(outDir,'THEOREM3_CERTIFIABILITY_GRID.csv'));

    fprintf('\nPASS: deterministic v1 theory checks completed.\n');
end
