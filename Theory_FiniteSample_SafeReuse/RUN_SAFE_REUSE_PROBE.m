function RUN_SAFE_REUSE_PROBE()
%RUN_SAFE_REUSE_PROBE Self-contained checks for the draft safe-reuse result.
%
% The script checks three things:
%   A) exact role-separated risk identity by Monte Carlo;
%   B) no-harm below the oracle cap and possible harm above it;
%   C) a bounded same-audit counterexample showing that the cap is not
%      sufficient when W depends on the direct-estimation error.
%
% No frozen CMDO result is modified.

    fprintf('============================================================\n');
    fprintf(' CMDO finite-sample safe-reuse exploratory probe\n');
    fprintf('============================================================\n');

    rng(20260907, 'twister');

    %% A. Role-separated random weight: exact identity
    theta = 0.50;
    V = 0.04;
    B = 0.30;
    H = theta + B;
    lambda = B^2 / V;
    omegaSafe = safe_reuse_cap(B, V);

    n = 500000;
    e = sqrt(V) * randn(n,1);
    D = theta + e;

    % Independent decision signal generates an adaptive random weight.
    U = rand(n,1);
    omega = 0.90 * omegaSafe;
    W = omega * U;

    A = (1-W).*D + W.*H;
    Rmc = mean((A-theta).^2);
    mu = mean(W);
    q = mean(W.^2);
    Ridentity = V - 2*V*mu + (V+B^2)*q;

    fprintf('\n[A] Role-separated identity\n');
    fprintf('Lambda                = %.6f\n', lambda);
    fprintf('oracle safe cap        = %.6f\n', omegaSafe);
    fprintf('used max weight        = %.6f\n', omega);
    fprintf('direct risk V          = %.8f\n', V);
    fprintf('MC adaptive risk       = %.8f\n', Rmc);
    fprintf('identity risk          = %.8f\n', Ridentity);
    fprintf('MC - identity          = %.3e\n', Rmc-Ridentity);
    fprintf('relative gain          = %.3f %%\n', 100*(1-Rmc/V));

    assert(abs(Rmc-Ridentity) < 5e-4, ...
        'Monte Carlo check did not agree with the exact identity.');
    assert(Rmc <= V + 5e-4, ...
        'Below-cap role-separated rule unexpectedly exceeded direct risk.');

    %% B. Above-cap constant weight can be harmful
    omegaHigh = min(1, 1.15 * omegaSafe);
    Whigh = omegaHigh * ones(n,1);
    Ahigh = (1-Whigh).*D + Whigh.*H;
    Rhigh = mean((Ahigh-theta).^2);

    fprintf('\n[B] Above-cap constant rule\n');
    fprintf('used weight            = %.6f\n', omegaHigh);
    fprintf('adaptive risk          = %.8f\n', Rhigh);
    fprintf('relative gain          = %.3f %%\n', 100*(1-Rhigh/V));
    fprintf('(Harm is possible above the cap; it is not guaranteed.)\n');

    %% C. Bounded same-audit coupling counterexample
    thetaC = 0.50;
    Dlo = 0.25;
    Dhi = 0.75;
    HC = 1.00;
    BC = HC-thetaC;
    VC = ((Dhi-thetaC)^2 + (Dlo-thetaC)^2)/2;
    omegaC = safe_reuse_cap(BC, VC); % exactly 0.4

    % Same-audit rule: borrow only when current direct estimate is high.
    errHi = (1-omegaC)*(Dhi-thetaC) + omegaC*BC;
    errLo = (Dlo-thetaC); % W=0
    Rcoupled = (errHi^2 + errLo^2)/2;

    fprintf('\n[C] Same-audit counterexample\n');
    fprintf('theta                  = %.3f\n', thetaC);
    fprintf('D support              = {%.2f, %.2f}\n', Dlo, Dhi);
    fprintf('historical H           = %.2f\n', HC);
    fprintf('direct risk V          = %.6f\n', VC);
    fprintf('Lambda                 = %.3f\n', BC^2/VC);
    fprintf('role-separated cap     = %.3f\n', omegaC);
    fprintf('coupled adaptive risk  = %.6f\n', Rcoupled);
    fprintf('risk inflation         = %.2f %%\n', 100*(Rcoupled/VC-1));

    assert(abs(omegaC-0.4) < 1e-12, 'Counterexample cap changed unexpectedly.');
    assert(Rcoupled > VC, ...
        'Counterexample failed to demonstrate coupling-induced harm.');

    fprintf('\nPASS: baseline theorem identity and coupling counterexample verified.\n');
end
