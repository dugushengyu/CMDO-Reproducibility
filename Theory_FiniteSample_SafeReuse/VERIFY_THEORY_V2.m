function out = VERIFY_THEORY_V2()
%VERIFY_THEORY_V2 Deterministic checks for THEORY_RESULT_V2.
%
% Base-MATLAB only. No random simulation is required.
% This script does not modify any frozen CMDO/U10 artifact.

    fprintf('============================================================\n');
    fprintf(' VERIFY THEORY V2: finite-sample certifiability\n');
    fprintf('============================================================\n');

    tol = 1e-12;

    %% Theorem 1: fixed weights all help; same-audit any positive cap hurts.
    theta = 0.5;
    p1 = 0.8; d1 = 0.6;
    p2 = 0.2; d2 = 0.1;
    H = 0.65;
    V = p1*(d1-theta)^2 + p2*(d2-theta)^2;
    B = H-theta;
    Lambda = B^2/V;

    wgrid = linspace(0,1,1001)';
    fixedDiff = -2*V*wgrid + (V+B^2).*wgrid.^2;
    assert(max(fixedDiff(2:end)) < tol, ...
        'Theorem 1 fixed-weight claim failed.');

    omegaGrid = [1e-6 1e-3 0.05 0.2 0.5 1.0];
    adaptiveDiff = zeros(size(omegaGrid));
    for j = 1:numel(omegaGrid)
        om = omegaGrid(j);
        A1 = (1-om)*d1 + om*H;
        A2 = d2; % W=0 in second state
        R = p1*(A1-theta)^2 + p2*(A2-theta)^2;
        adaptiveDiff(j) = R-V;
        exactFormula = om*(om+4)/500;
        assert(abs(adaptiveDiff(j)-exactFormula) < 1e-12, ...
            'Theorem 1 adaptive formula mismatch.');
        assert(adaptiveDiff(j) > 0, ...
            'Theorem 1 adaptive harm claim failed.');
    end

    fprintf('[PASS] Theorem 1 bounded magnitude-only impossibility.\n');
    fprintf('       V=%.8f, B=%.8f, Lambda=%.8f\n',V,B,Lambda);

    %% Theorem 4: one-decision-standard-error boundary.
    sigma2 = 0.04;
    ms = 40;
    me = 160;
    M = ms+me;
    delta = ms/M;
    Ve = sigma2/me;
    Vf = sigma2/M;
    Vs = sigma2/ms;

    % Numerically maximize tolerable B^2 over w.
    w = linspace(1e-5,1,200000)';
    b2tol = Ve .* (2*w - w.^2 - delta) ./ (w.^2);
    b2tol(2*w-w.^2-delta < 0) = NaN;
    [mx,idx] = max(b2tol,[],'omitnan');
    wNum = w(idx);
    assert(abs(mx-Vs) < 2e-7, ...
        'Theorem 4 maximum mismatch radius failed.');
    assert(abs(wNum-delta) < 2e-4, ...
        'Theorem 4 maximizing weight failed.');

    % Exact risk difference at w=delta.
    Btest = sqrt(Vs);
    Rdelta = Ve*(1-delta)^2 + Btest^2*delta^2;
    assert(abs(Rdelta-Vf) < 1e-12, ...
        'Theorem 4 boundary equality failed.');

    fprintf('[PASS] Theorem 4 one-standard-error boundary.\n');
    fprintf('       delta=%.6f, max B^2=%.8g, Vs=%.8g\n',delta,mx,Vs);

    %% Bernoulli safe interval roots.
    Hacc = 0.973208152049;
    msAcc = 128;
    disc = sqrt(1 + 4*msAcc*Hacc*(1-Hacc));
    thLo = (2*msAcc*Hacc + 1 - disc)/(2*(msAcc+1));
    thHi = (2*msAcc*Hacc + 1 + disc)/(2*(msAcc+1));
    qLo = msAcc*(Hacc-thLo)^2 - thLo*(1-thLo);
    qHi = msAcc*(Hacc-thHi)^2 - thHi*(1-thHi);
    assert(abs(qLo) < 1e-11 && abs(qHi) < 1e-11, ...
        'Bernoulli safe-set roots failed.');
    fprintf('[PASS] Bernoulli accuracy safe-set roots.\n');

    %% Theorem 5: Gaussian certification-power ceiling.
    alpha = 0.05;
    Phi = @(x) 0.5*(1+erf(x/sqrt(2)));
    boundaryProb = @(c) Phi(c-1)-Phi(-c-1);
    cAlpha = fzero(@(c) boundaryProb(c)-alpha,[0,1]);
    piStar = 2*Phi(cAlpha)-1;
    assert(abs(cAlpha-0.1033184796725569) < 1e-10, ...
        'Gaussian c_alpha mismatch.');
    assert(abs(piStar-0.0822897905513917) < 1e-10, ...
        'Gaussian power ceiling mismatch.');
    fprintf('[PASS] Theorem 5 Gaussian power ceiling.\n');
    fprintf('       alpha=%.3f, c_alpha=%.10f, pi*=%.10f\n', ...
        alpha,cAlpha,piStar);

    %% U10 iid benchmark: maximum oracle decision-audit size.
    cohort = {'Georgia';'CPSC_2018'};
    thetaU = [0.955110765643; 0.942125927003];
    HU = [0.973208152049; 0.973208152049];
    sigma2U = thetaU.*(1-thetaU);
    BU = HU-thetaU;
    msMax = sigma2U./(BU.^2);

    assert(abs(msMax(1)-130.9074067539) < 1e-8, ...
        'Georgia iid boundary mismatch.');
    assert(abs(msMax(2)-56.4376344431) < 1e-8, ...
        'CPSC iid boundary mismatch.');

    TU10 = table(cohort,thetaU,HU,BU,sigma2U,msMax, ...
        'VariableNames',{'cohort','theta','H','B','sigma2','max_oracle_decision_budget_iid'});
    fprintf('[PASS] U10-like iid oracle decision-budget boundary.\n');
    disp(TU10);

    %% Output bundle.
    out = struct();
    out.theorem1.V = V;
    out.theorem1.B = B;
    out.theorem1.Lambda = Lambda;
    out.theorem1.omega = omegaGrid;
    out.theorem1.adaptiveRiskDifference = adaptiveDiff;
    out.theorem4.delta = delta;
    out.theorem4.maxMismatchSquared = mx;
    out.theorem4.decisionVariance = Vs;
    out.theorem5.alpha = alpha;
    out.theorem5.cAlpha = cAlpha;
    out.theorem5.maxPerfectMatchCertificationProbability = piStar;
    out.u10_iid = TU10;

    outDir = fullfile(fileparts(mfilename('fullpath')),'outputs');
    if ~isfolder(outDir), mkdir(outDir); end
    writetable(TU10,fullfile(outDir,'U10_IID_ONE_SE_BOUNDARY.csv'));

    fprintf('============================================================\n');
    fprintf(' ALL DETERMINISTIC V2 CHECKS PASSED\n');
    fprintf('============================================================\n');
end