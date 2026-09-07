function T = VERIFY_CROSSFIT_V2()
%VERIFY_CROSSFIT_V2 Verify the reciprocal cross-fit limitation theorem.
%
% The script checks several omega values below 2/3. For each value it
% constructs r in the theorem's admissible interval, verifies that every
% fixed weight up to omega is non-inferior to full direct, and then enumerates
% the four adaptive reciprocal-crossfit fold pairs.

    omegaGrid = [0.05 0.10 0.20 0.35 0.50 0.65];
    rows = zeros(numel(omegaGrid),8);

    for i = 1:numel(omegaGrid)
        omega = omegaGrid(i);
        assert(omega < 2/3,'Theorem-4 construction requires omega<2/3.');

        rUpper = sqrt((2/omega - 1)/2);
        r = 0.5*(1+rUpper);
        a = min(0.20,0.49/r);
        B = r*a;

        Vhalf = a^2;
        Vfull = Vhalf/2;
        fixedCap = 2/(1+2*r^2);
        assert(omega < fixedCap + 1e-12, ...
            'Chosen omega is not inside the full-direct fixed safe interval.');

        w = linspace(0,omega,1001);
        fixedExcess = -a^2*w + (a^2/2 + B^2).*w.^2;
        assert(max(fixedExcess) <= 1e-12, ...
            'At least one fixed weight is harmful.');

        eVals = [-a,+a];
        sq = zeros(4,1);
        z = 0;
        for i1 = 1:2
            for i2 = 1:2
                z = z+1;
                e1 = eVals(i1);
                e2 = eVals(i2);
                w1 = omega * double(e1>0);
                w2 = omega * double(e2>0);
                err = 0.5*((1-w1)*e2+w1*B + (1-w2)*e1+w2*B);
                sq(z)=err^2;
            end
        end
        Rcf = mean(sq);
        excess = Rcf-Vfull;

        closedForm = a^2*omega/8 * ...
            (3*omega*r^2 - 2*omega*r + 3*omega + 4*r - 4);

        assert(excess > 0,'Cross-fit adaptive construction is not harmful.');
        assert(abs(excess-closedForm) < 1e-12, ...
            'Closed-form cross-fit excess risk does not match enumeration.');

        rows(i,:) = [omega,r,a,fixedCap,Vfull,Rcf,excess,closedForm];
    end

    T = array2table(rows,'VariableNames', ...
        {'omega','r','a','fixed_safe_cap_vs_full','direct_full_risk', ...
         'crossfit_adaptive_risk','crossfit_excess_risk','closed_form_excess'});

    fprintf('============================================================\n');
    fprintf(' Reciprocal cross-fit limitation theorem checks\n');
    fprintf('============================================================\n');
    disp(T);

    outDir = fullfile(fileparts(mfilename('fullpath')),'outputs');
    if ~isfolder(outDir), mkdir(outDir); end
    writetable(T,fullfile(outDir,'THEOREM4_CROSSFIT_COUNTEREXAMPLE_CHECKS.csv'));

    fprintf('\nPASS: Theorem 4 checks completed.\n');
end
