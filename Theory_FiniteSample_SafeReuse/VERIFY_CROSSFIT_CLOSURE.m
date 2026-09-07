function out = VERIFY_CROSSFIT_CLOSURE()
%VERIFY_CROSSFIT_CLOSURE Deterministic checks for CROSSFIT_CLOSURE.md.
%
% Base-MATLAB only. No random simulation. Does not modify frozen artifacts.

    fprintf('============================================================\n');
    fprintf(' VERIFY CROSSFIT CLOSURE\n');
    fprintf('============================================================\n');

    theta = 0.5;
    d = [0.6; 0.1];
    p = [0.8; 0.2];
    H = 0.65;
    e = d-theta;
    V = sum(p.*e.^2);
    B = H-theta;

    % W=1 on D=.6 and 0 on D=.1.
    W = [1;0];
    mu = sum(p.*W);
    q = sum(p.*W.^2);
    a = sum(p.*W.*e);

    % Exact identity.
    diffFormula = 0.5*(-2*V*mu + V*q + B^2*(q+mu^2) + ...
        a^2 + 2*B*(1-mu)*a);

    % Enumerate all four fold pairs exactly.
    Rcf = 0;
    Rfull = 0;
    for i = 1:2
        for j = 1:2
            pij = p(i)*p(j);
            d1 = d(i); d2 = d(j);
            w1 = W(i); w2 = W(j);
            Acf = 0.5*((1-w1)*d2+w1*H + (1-w2)*d1+w2*H);
            Dfull = 0.5*(d1+d2);
            Rcf = Rcf + pij*(Acf-theta)^2;
            Rfull = Rfull + pij*(Dfull-theta)^2;
        end
    end

    assert(abs(Rfull - V/2) < 1e-14, 'Full-direct risk mismatch.');
    assert(abs((Rcf-Rfull)-diffFormula) < 1e-14, ...
        'Cross-fit risk identity mismatch.');
    assert(abs(diffFormula-29/5000) < 1e-14, ...
        'Counterexample exact risk difference mismatch.');
    assert(abs(Rcf-0.0258) < 1e-14, 'Counterexample risk mismatch.');
    assert(Rcf > Rfull, 'Expected cross-fit harm did not occur.');

    % Verify every fixed convex weight is beneficial vs half direct.
    wgrid = linspace(0,1,1001)';
    fixedDiff = -2*V*wgrid + (V+B^2).*wgrid.^2;
    assert(max(fixedDiff(2:end)) < 1e-12, ...
        'Not every positive fixed weight is beneficial.');

    fprintf('[PASS] Exact two-fold cross-fit identity.\n');
    fprintf('[PASS] Bounded counterexample.\n');
    fprintf('       half-direct V = %.8f\n',V);
    fprintf('       full-direct risk = %.8f\n',Rfull);
    fprintf('       cross-fit risk = %.8f\n',Rcf);
    fprintf('       excess = %.8f (%.2f%%)\n',Rcf-Rfull,100*(Rcf/Rfull-1));

    out = struct('V_half',V,'R_full',Rfull,'R_crossfit',Rcf, ...
        'risk_difference',Rcf-Rfull,'relative_increase_pct',100*(Rcf/Rfull-1), ...
        'mu',mu,'q',q,'a',a);

    fprintf('============================================================\n');
    fprintf(' ALL CROSSFIT CLOSURE CHECKS PASSED\n');
    fprintf('============================================================\n');
end