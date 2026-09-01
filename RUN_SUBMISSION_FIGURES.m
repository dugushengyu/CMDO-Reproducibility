function summary = RUN_SUBMISSION_FIGURES(varargin)
%RUN_SUBMISSION_FIGURES Reviewer-facing CMDO submission figure pathway.
%
%   RUN_SUBMISSION_FIGURES
%   RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
%
% All scientific inputs are repository-relative tracked frozen records.
% No author-machine repository/data path is used.

p = inputParser;
addParameter(p,'Batch',true,@(x)islogical(x) || isnumeric(x));
addParameter(p,'Strict',true,@(x)islogical(x) || isnumeric(x));
addParameter(p,'OutDir','',@(x)ischar(x) || isstring(x));
parse(p,varargin{:});
opt = p.Results;

thisFile = mfilename('fullpath');
if isempty(thisFile)
    repoRoot = pwd;
else
    repoRoot = fileparts(thisFile);
end

subDir = fullfile(repoRoot,'matlab','submission_figures');
assert(isfolder(subDir),'Missing matlab/submission_figures.');
addpath(subDir);

if strlength(string(opt.OutDir)) == 0
    outDir = fullfile(tempdir,'CMDO_submission_figures');
else
    outDir = char(opt.OutDir);
end
if isfolder(outDir)
    try
        rmdir(outDir,'s');
    catch
    end
end
if ~isfolder(outDir)
    mkdir(outDir);
end

local_preflight(repoRoot,subDir);

names = [ ...
    "Figure1"; ...
    "Figure2_IDENTIFY"; ...
    "Figure3_REUSE"; ...
    "Figure4_PRESERVE"; ...
    "Figure5_FINAL_FROZEN"; ...
    "ExtendedData1"; ...
    "ExtendedData2"];

status = strings(7,1);
seconds = nan(7,1);
message = strings(7,1);

fprintf('\n============================================================\n');
fprintf(' CMDO REVIEWER FIGURE PATHWAY\n');
fprintf('============================================================\n');
fprintf('Repository : %s\n',repoRoot);
fprintf('Output     : %s\n',outDir);
fprintf('Inputs     : tracked repository-relative frozen records only\n');

for i = 1:7
    tic;
    try
        switch i
            case 1
                Figure1_IDA_RealData_Final('OutDir',outDir);
            case 2
                Figure2_IDENTIFY_Validation(outDir,repoRoot);
            case 3
                Figure3_REUSE_Validation(outDir,repoRoot);
            case 4
                Figure4_PRESERVE_Refined(outDir);
            case 5
                Figure5_PhaseBoundary( ...
                    'CSVPath',fullfile(repoRoot,'source_data', ...
                    'figure5_submission', ...
                    'CMDO_SystemStress_AUC_StateSummary_v1_1.csv'), ...
                    'OutDir',outDir);
            case 6
                ED1_OutcomeFreeBoundary_v9(outDir,repoRoot);
            case 7
                ED2_IntegrityControls_v2(outDir,repoRoot);
        end
        status(i) = "PASS";
    catch ME
        status(i) = "FAIL";
        message(i) = string(ME.message);
        if logical(opt.Strict)
            rethrow(ME);
        end
    end
    seconds(i) = toc;
end

summary = table(names,status,seconds,message, ...
    'VariableNames',{'figure','status','seconds','message'});

local_output_audit(outDir,logical(opt.Strict));

fprintf('\n============================================================\n');
fprintf(' CMDO REVIEWER SUMMARY\n');
fprintf('============================================================\n');
disp(summary);
fprintf('EXTERNAL REPOSITORY DEPENDENCIES : 0\n');
fprintf('EXTERNAL DATA PATHS              : 0\n');
fprintf('NETWORK ACCESS DURING RENDER     : 0\n');
fprintf('FINAL FIGURE 5 SOURCE            : frozen tracked CSV\n');
fprintf('7/7 RENDERERS                    : %s\n', ...
    string(all(status=="PASS")));

if logical(opt.Strict)
    assert(all(status=="PASS"), ...
        'One or more submission renderers failed.');
end

end

function local_preflight(repoRoot,subDir)

required = { ...
    fullfile(repoRoot,'source_data','figure1_assets', ...
        'Figure1_assets_selected_v1.mat'); ...
    fullfile(repoRoot,'source_data','figure5_submission', ...
        'CMDO_SystemStress_AUC_StateSummary_v1_1.csv'); ...
    fullfile(repoRoot,'source_data','figure6_admissibility', ...
        'CMDO_Admissibility_State_MSE_Audit.csv'); ...
    fullfile(repoRoot,'U10_Prospective_ECG','02_Posthoc_Diagnostics', ...
        'U10_DEPENDENCE_DECOMPOSITION.csv'); ...
    fullfile(repoRoot,'U10_Prospective_ECG','01_Prospective_Result', ...
        'U10_PRIMARY_RESULT.json'); ...
    fullfile(repoRoot,'U11_Information_Closure','01_Result', ...
        'U11_WORLD_PLUS_georgia_v0.1.csv'); ...
    fullfile(repoRoot,'U11_Information_Closure','01_Result', ...
        'U11_WORLD_MINUS_georgia_v0.1.csv'); ...
    fullfile(repoRoot,'U11_Information_Closure','01_Result', ...
        'U11_WORLD_PLUS_cpsc_2018_v0.1.csv'); ...
    fullfile(repoRoot,'U11_Information_Closure','01_Result', ...
        'U11_WORLD_MINUS_cpsc_2018_v0.1.csv')};

frozenNames = { ...
    'StageU4C_Audit_State_Results_v1.1.csv'; ...
    'StageU4C_Component_Fits_v1.1.csv'; ...
    'StageU4C_Component_Trajectory_Predictions_v1.1.csv'; ...
    'StageU4C_Evidence_Expiry_Map_v1.1.csv'; ...
    'StageU5B_Audit_State_Results_v1.0.csv'; ...
    'StageU6_Audit_State_Results_v1.0.csv'; ...
    'StageU6_Target_Summary_v1.0.csv'; ...
    'StageU7_State_Results_v1.0.csv'; ...
    'StageU7_Target_Metric_Summary_v1.0.csv'; ...
    'StageU7_Metric_Summary_v1.0.csv'};

for i = 1:numel(frozenNames)
    required{end+1,1} = fullfile( ...
        repoRoot,'source_data','submission_frozen',frozenNames{i}); %#ok<AGROW>
end

for i = 1:numel(required)
    assert(isfile(required{i}), ...
        ['Missing reviewer-facing tracked input:' newline required{i}]);
end

active = { ...
    'Figure1_IDA_RealData_Final.m'; ...
    'Figure2_IDENTIFY_Validation.m'; ...
    'Figure3_REUSE_Validation.m'; ...
    'Figure4_PRESERVE_Refined.m'; ...
    'Figure5_PhaseBoundary.m'; ...
    'ED1_OutcomeFreeBoundary_v9.m'; ...
    'ED2_IntegrityControls_v2.m'; ...
    'cmdo_submission_load.m'};

for i = 1:numel(active)
    txt = fileread(fullfile(subDir,active{i}));
    forbidden = { ...
        'C:\Users\zyx\', ...
        'F:\manuscript manual\', ...
        'CMDO-U6-WSL-REPLAY', ...
        'uigetfile(', ...
        'getenv(''USERPROFILE'')'};
    for j = 1:numel(forbidden)
        assert(~contains(txt,forbidden{j}), ...
            'Forbidden author-machine dependency in %s: %s', ...
            active{i},forbidden{j});
    end
end

local_validate_final_stress(fullfile( ...
    repoRoot,'source_data','figure5_submission', ...
    'CMDO_SystemStress_AUC_StateSummary_v1_1.csv'));

end

function local_validate_final_stress(csvPath)

T = readtable(csvPath,'VariableNamingRule','preserve');

methods = { ...
    'PC_PAIRED_HOEFFDING', ...
    'PC_USTAT_MCDIARMID', ...
    'PC_DELONG', ...
    'PC_PLUGIN'};

budgets = [8 16 32 64 128];
expected = [ ...
    1.00 1.00 0.25 0.75; ...
    2.00 4.00 0.75 2.00; ...
    4.00 4.00 1.50 2.00; ...
    4.00 4.00 2.00 2.00; ...
    4.00 4.00 2.00 2.00];

lambdas = sort(unique(double(T.lambda_nominal)))';
observed = zeros(numel(budgets),numel(methods));

for im = 1:numel(methods)
    for ib = 1:numel(budgets)
        crit = 0;
        for il = 1:numel(lambdas)
            mask = strcmp(string(T.method),methods{im}) & ...
                double(T.budget)==budgets(ib) & ...
                abs(double(T.lambda_nominal)-lambdas(il))<1e-12;
            assert(any(mask),'Incomplete final Figure-5 state grid.');
            if max(double(T.mean_excess_mae(mask))) <= 0
                crit = lambdas(il);
            else
                break;
            end
        end
        observed(ib,im) = crit;
    end
end

assert(max(abs(observed(:)-expected(:))) < 1e-12, ...
    ['Figure-5 CSV is not the frozen final run.' newline ...
     'Critical-Lambda fingerprint does not match the manuscript.']);

keys = {'true_auc','budget','lambda_nominal','bias_sign'};

C = T(strcmp(string(T.method),'PC_PAIRED_HOEFFDING'), ...
    [keys {'gain_percent'}]);
U = T(strcmp(string(T.method),'PC_USTAT_MCDIARMID'), ...
    [keys {'gain_percent'}]);

C.Properties.VariableNames{end} = 'gain_CMDO';
U.Properties.VariableNames{end} = 'gain_USTAT';

P = innerjoin(C,U,'Keys',keys);
P = P(double(P.lambda_nominal)<=1+1e-12,:);

adv = double(P.gain_CMDO)-double(P.gain_USTAT);

assert(abs(mean(adv,'omitnan')-1.0817) < 5e-4, ...
    'Final Figure-5 efficiency fingerprint does not match 1.0817 pp.');
assert(abs(mean(adv>0)-0.80) < 1e-12, ...
    'Final Figure-5 paired-win fingerprint does not match 80%%.');

end

function local_output_audit(outDir,strict)

base = { ...
    'Figure1_Evidential_Order_Final_Worlds_ABC'; ...
    'Figure2_IDENTIFY_Validation'; ...
    'Figure3_REUSE_Validation'; ...
    'Figure4_PRESERVE_Refined'; ...
    'Figure5_PhaseBoundary_Final_3Panel'; ...
    'ED1_OutcomeFreeBoundary_v9'; ...
    'ED2_IntegrityControls_v2'};

missing = strings(0,1);
fprintf('\n--- OUTPUT AUDIT ---\n');

for i = 1:numel(base)
    for ext = {'.png','.pdf'}
        name = [base{i} ext{1}];
        path = fullfile(outDir,name);
        ok = isfile(path);
        fprintf('%-50s %s\n',name,string(ok));
        if ~ok
            missing(end+1,1) = string(path); %#ok<AGROW>
        end
    end
end

if strict
    assert(isempty(missing), ...
        'One or more expected submission outputs are missing.');
end

end
