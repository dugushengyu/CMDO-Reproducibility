function report = VERIFY_P0_SUBMISSION_INPUTS(varargin)
%VERIFY_P0_SUBMISSION_INPUTS Final CMDO submission-scope integrity checks.
%
% Validates reviewer-facing sources added/changed during the final P0 freeze,
% including the corrected common-empirical-risk Figure 4 frontier, the
% 185-state admissibility source, the U10 decomposition and exact finite-
% cohort check, and the post-completion Figure 5 Monte Carlo diagnostic.

p=inputParser;
addParameter(p,'Strict',true,@(x)islogical(x)||isnumeric(x));
parse(p,varargin{:});
strict=logical(p.Results.Strict);

thisFile=mfilename('fullpath');
repoRoot=fileparts(thisFile);

fprintf('\n============================================================\n');
fprintf(' CMDO P0 SUBMISSION INPUT INTEGRITY\n');
fprintf('============================================================\n');

report=struct();

%% Figure 4 tracked audit snapshot and authoritative U10 source
f4=fullfile(repoRoot,'source_data','figure4_submission', ...
    'CMDO_Figure4_PRESERVE_Source_v1.csv');
assert(isfile(f4),'Missing Figure 4 tracked audit snapshot CSV.');
T=readtable(f4,'VariableNamingRule','preserve');
assert(height(T)==12,'Figure 4 audit snapshot must contain 12 cohort-budget rows.');

f4prov=fullfile(repoRoot,'source_data','figure4_submission', ...
    'CMDO_Figure4_PRESERVE_Source_v1_provenance.json');
assert(isfile(f4prov),'Missing corrected Figure 4 provenance JSON.');

u10=fullfile(repoRoot,'U10_Prospective_ECG','02_Posthoc_Diagnostics', ...
    'U10_DEPENDENCE_DECOMPOSITION.csv');
assert(isfile(u10),'Missing U10 dependence decomposition source.');
U=readtable(u10,'VariableNamingRule','preserve');
report.u10Rows=height(U);
report.u10RowCountPass=(height(U)==8);
fprintf('U10 decomposition rows              : %d\n',height(U));

% Panel-A 12-state fingerprints come from the tracked snapshot.
fixed=double(T.fixed_risk); adaptive=double(T.adaptive_risk);
report.figure4AdaptiveWorse=nnz(adaptive>fixed);
report.figure4BenefitToHarm=nnz((fixed<1)&(adaptive>1));

% Recompute the corrected empirical Panel-B frontier directly from the
% authoritative U10 decomposition, using exactly the same common empirical
% risk measure as the final renderer.
u10B=double(U.B);
u10V=double(U.direct_mse);
u10MeanW=double(U.shared_constant_mean_weight);
u10FixedMSE=double(U.shared_constant_mean_mse);

u10Lambda=(u10B.^2)./u10V;
fixedRiskAtMean=u10FixedMSE./u10V;
denQ=2.*u10MeanW.*(1-u10MeanW);
assert(all(abs(denQ)>1e-12),'Cannot reconstruct Figure 4 empirical cross-term.');

u10Q=(fixedRiskAtMean-(1-u10MeanW).^2-u10Lambda.*u10MeanW.^2)./denQ;
quadTerm=1+u10Lambda-2*u10Q;
linearGain=1-u10Q;
assert(all(isfinite(quadTerm)&quadTerm>0), ...
    'Figure 4 empirical fixed-risk quadratic is not convex in all U10 states.');

u10Wstar=min(1,max(0,linearGain./quadTerm));
wGlobal=min(1,max(0,mean(linearGain,'omitnan')/mean(quadTerm,'omitnan')));
riskEmp=@(w) (1-w).^2 + u10Lambda.*w.^2 + 2.*w.*(1-w).*u10Q;

riskStar=riskEmp(u10Wstar);
riskGlobal=riskEmp(wGlobal.*ones(size(u10MeanW)));
riskMeanW=riskEmp(u10MeanW);

Hi=riskGlobal-riskStar;
Ai=riskMeanW-riskStar;
Ci=(double(U.shared_adaptive_mse)-u10FixedMSE)./u10V;

H=mean(Hi,'omitnan');
A=mean(Ai,'omitnan');
C=mean(Ci,'omitnan');
report.H=H; report.A=A; report.C=C;
report.sharedMargin=H-A-C;

% Reconstruct pairing-disruption composition excess directly from the same
% authoritative tracked U10 post-completion decomposition.
report.pairingDisruptedC=mean((double(U.shared_permuted_weight_mse) - ...
    u10FixedMSE)./u10V,'omitnan');
report.pairingDisruptedMargin=H-A-report.pairingDisruptedC;

% The tracked Figure-4 audit snapshot must agree statewise with the
% authoritative reconstruction for all eight Georgia/CPSC states.
Btab=T(ismember(string(T.dataset),["georgia","cpsc_2018"]),:);
Btab=sortrows(Btab,{'dataset','budget'});
Us=table(string(U.dataset),double(U.budget),Hi,Ai,Ci,Ai+Ci, ...
    'VariableNames',{'dataset','budget','H','A','C','cost'});
Us=sortrows(Us,{'dataset','budget'});

snapH=double(Btab.H_contribution);
snapA=double(Btab.A_contribution);
snapC=double(Btab.C_contribution);
snapCost=double(Btab.cost_contribution);
report.figure4SnapshotResidual=max([ ...
    abs(snapH-Us.H); abs(snapA-Us.A); abs(snapC-Us.C); abs(snapCost-Us.cost)], ...
    [],'all','omitnan');
report.figure4SnapshotPass=report.figure4SnapshotResidual<5e-10;

okF4 = report.figure4AdaptiveWorse==12 && ...
       report.figure4BenefitToHarm==7 && ...
       abs(H-0.08286653)<5e-7 && ...
       abs(A-0.01508453)<5e-7 && ...
       abs(C-0.21760208)<5e-7 && ...
       abs(report.sharedMargin+0.14982008)<5e-7 && ...
       abs(report.pairingDisruptedC-0.03214915)<5e-7 && ...
       abs(report.pairingDisruptedMargin-0.03563284)<5e-7 && ...
       report.figure4SnapshotPass;
report.figure4FingerprintPass=okF4;
fprintf('Figure 4 corrected fingerprints     : %s\n',string(okF4));
fprintf('Figure 4 H / A / C                  : %.8f / %.8f / %.8f\n',H,A,C);
fprintf('Pairing-disruption C from U10       : %.8f\n',report.pairingDisruptedC);
fprintf('Figure 4 snapshot max residual      : %.3e\n',report.figure4SnapshotResidual);

%% Exact finite-cohort U10 Supplementary diagnostic
try
    exactSummary=RUN_U10_EXACT_FINITE_COHORT_CHECK( ...
        'RepoRoot',repoRoot,'VerifyOnly',true,'Strict',true);
    report.u10ExactRows=height(exactSummary);
    report.u10ExactPass=(height(exactSummary)==8);
catch ME
    report.u10ExactRows=0;
    report.u10ExactPass=false;
    report.u10ExactError=string(ME.message);
    if strict
        rethrow(ME);
    end
end
fprintf('U10 exact finite-cohort check       : %s\n',string(report.u10ExactPass));

%% 185-state admissibility source
adm=fullfile(repoRoot,'source_data','figure6_admissibility', ...
    'CMDO_Admissibility_State_MSE_Audit.csv');
assert(isfile(adm),'Missing 185-state admissibility source.');
A185=readtable(adm,'VariableNamingRule','preserve');
report.admissibilityRows=height(A185);
report.admissibilityRowCountPass=(height(A185)==185);
fprintf('185-state admissibility rows        : %d\n',height(A185));

%% Figure 5 MC stability source
mc=fullfile(repoRoot,'source_data','figure5_submission','diagnostics', ...
    'CMDO_Figure5_MC_Stability_5x200.csv');
assert(isfile(mc),'Missing Figure 5 Monte Carlo stability source.');
M=readtable(mc,'VariableNamingRule','preserve');
report.mcBlocks=height(M);
report.mcCmdoUstatMatched=all(abs(double(M.cmdo_lambda_star)-double(M.ustat_lambda_star))<1e-12);
report.mcAdvMin=min(double(M.cmdo_minus_ustat_gain_pp));
report.mcAdvMax=max(double(M.cmdo_minus_ustat_gain_pp));
report.mcWinAll=all(abs(double(M.cmdo_higher_fraction)-0.80)<1e-12);
okMC = height(M)==5 && report.mcCmdoUstatMatched && report.mcWinAll && ...
       report.mcAdvMin>1.091 && report.mcAdvMax<1.102;
report.mcStabilityPass=okMC;
fprintf('Figure 5 MC stability blocks        : %d\n',height(M));
fprintf('CMDO/U-stat matched boundaries      : %s\n',string(report.mcCmdoUstatMatched));
fprintf('CMDO-U-stat efficiency range (pp)   : %.4f to %.4f\n',report.mcAdvMin,report.mcAdvMax);
fprintf('80%% matched-state win in all blocks : %s\n',string(report.mcWinAll));

%% Renderer provenance checks
renderer=fullfile(repoRoot,'matlab','submission_figures','Figure4_PRESERVE_Refined.m');
assert(isfile(renderer),'Missing Figure 4 renderer.');
txt=fileread(renderer);
report.figure4RendererUsesTrackedU10=contains(txt,'U10_DEPENDENCE_DECOMPOSITION.csv');
report.figure4RendererUsesTrackedU9B=contains(txt,'U9B_external_composability_decomposition.csv');
report.figure4RendererUsesEmpiricalCrossTerm=contains(txt,'u10Q') && contains(txt,'riskEmp');
report.figure4RendererPairingCNotHardcoded=~contains(txt,'Cperm=0.03214915') && ...
    ~contains(txt,'Cperm = 0.03214915');
report.figure4RendererOldWinnerLogicAbsent=~contains(txt,'winnerAgreement') && ~contains(txt,'pred_ga');
fprintf('Figure 4 renderer reads U10 source : %s\n',string(report.figure4RendererUsesTrackedU10));
fprintf('Figure 4 renderer reads U9B source : %s\n',string(report.figure4RendererUsesTrackedU9B));
fprintf('Empirical cross-term reconstruction: %s\n',string(report.figure4RendererUsesEmpiricalCrossTerm));
fprintf('Pairing C plotting value hardcoded : %s\n',string(~report.figure4RendererPairingCNotHardcoded));
fprintf('Old 7/8 winner logic absent         : %s\n',string(report.figure4RendererOldWinnerLogicAbsent));

report.pass = okF4 && report.admissibilityRowCountPass && ...
    report.u10RowCountPass && report.u10ExactPass && okMC && ...
    report.figure4RendererUsesTrackedU10 && ...
    report.figure4RendererUsesTrackedU9B && ...
    report.figure4RendererUsesEmpiricalCrossTerm && ...
    report.figure4RendererPairingCNotHardcoded && ...
    report.figure4RendererOldWinnerLogicAbsent;

fprintf('------------------------------------------------------------\n');
fprintf('P0 INPUT INTEGRITY                  : %s\n',string(report.pass));
fprintf('============================================================\n\n');

if strict
    assert(report.pass,'One or more P0 submission integrity checks failed.');
end
end
