function report = VERIFY_P0_SUBMISSION_INPUTS(varargin)
%VERIFY_P0_SUBMISSION_INPUTS Final CMDO submission-scope integrity checks.
%
% This check is intentionally narrow: it validates the reviewer-facing
% sources added/changed during the final P0 freeze, including the Figure 4
% data-driven source, the 185-state admissibility source, U10 decomposition,
% and the post-completion Figure 5 Monte Carlo stability diagnostic.

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

%% Figure 4 tracked source
f4=fullfile(repoRoot,'source_data','figure4_submission', ...
    'CMDO_Figure4_PRESERVE_Source_v1.csv');
assert(isfile(f4),'Missing Figure 4 tracked source CSV.');
T=readtable(f4,'VariableNamingRule','preserve');
assert(height(T)==12,'Figure 4 source must contain 12 cohort-budget rows.');

fixed=double(T.fixed_risk); adaptive=double(T.adaptive_risk);
report.figure4AdaptiveWorse=nnz(adaptive>fixed);
report.figure4BenefitToHarm=nnz((fixed<1)&(adaptive>1));

B=T(ismember(string(T.dataset),["georgia","cpsc_2018"]),:);
H=mean(double(B.H_contribution));
A=mean(double(B.A_contribution));
C=mean(double(B.C_contribution));
report.H=H; report.A=A; report.C=C;
report.sharedMargin=H-A-C;
report.pairingDisruptedC=0.03214915;
report.pairingDisruptedMargin=H-A-report.pairingDisruptedC;

okF4 = report.figure4AdaptiveWorse==12 && ...
       report.figure4BenefitToHarm==7 && ...
       abs(H-0.08614018)<5e-7 && ...
       abs(A-0.01403814)<5e-7 && ...
       abs(C-0.21760208)<5e-7 && ...
       abs(report.sharedMargin+0.14550004)<5e-7 && ...
       abs(report.pairingDisruptedMargin-0.03995289)<5e-7;
report.figure4FingerprintPass=okF4;
fprintf('Figure 4 tracked source             : %s\n',string(okF4));

%% 185-state admissibility source
adm=fullfile(repoRoot,'source_data','figure6_admissibility', ...
    'CMDO_Admissibility_State_MSE_Audit.csv');
assert(isfile(adm),'Missing 185-state admissibility source.');
A185=readtable(adm,'VariableNamingRule','preserve');
report.admissibilityRows=height(A185);
report.admissibilityRowCountPass=(height(A185)==185);
fprintf('185-state admissibility rows        : %d\n',height(A185));

%% U10 decomposition source
u10=fullfile(repoRoot,'U10_Prospective_ECG','02_Posthoc_Diagnostics', ...
    'U10_DEPENDENCE_DECOMPOSITION.csv');
assert(isfile(u10),'Missing U10 dependence decomposition source.');
U=readtable(u10,'VariableNamingRule','preserve');
report.u10Rows=height(U);
report.u10RowCountPass=(height(U)==8);
fprintf('U10 decomposition rows              : %d\n',height(U));

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

%% Renderer is data-driven
renderer=fullfile(repoRoot,'matlab','submission_figures','Figure4_PRESERVE_Refined.m');
assert(isfile(renderer),'Missing Figure 4 renderer.');
txt=fileread(renderer);
report.figure4RendererUsesTrackedCsv=contains(txt,'CMDO_Figure4_PRESERVE_Source_v1.csv');
report.figure4RendererOldWinnerLogicAbsent=~contains(txt,'winnerAgreement') && ~contains(txt,'pred_ga');
fprintf('Figure 4 renderer reads tracked CSV : %s\n',string(report.figure4RendererUsesTrackedCsv));
fprintf('Old 7/8 winner logic absent         : %s\n',string(report.figure4RendererOldWinnerLogicAbsent));

report.pass = okF4 && report.admissibilityRowCountPass && ...
    report.u10RowCountPass && okMC && ...
    report.figure4RendererUsesTrackedCsv && report.figure4RendererOldWinnerLogicAbsent;

fprintf('------------------------------------------------------------\n');
fprintf('P0 INPUT INTEGRITY                  : %s\n',string(report.pass));
fprintf('============================================================\n\n');

if strict
    assert(report.pass,'One or more P0 submission integrity checks failed.');
end
end
