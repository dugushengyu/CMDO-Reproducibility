function result = RUN_REVIEWER_E2E(varargin)
%RUN_REVIEWER_E2E Cross-machine reviewer end-to-end acceptance.
%
%   RUN_REVIEWER_E2E
%   RUN_REVIEWER_E2E('Offline',true)
%   RUN_REVIEWER_E2E('FreshVenv',true)
%
% Exact manuscript claim:
%   tracked frozen derived records -> Figure 1-5 + ED1-2.
%
% Additional engineering checks:
%   public UCI raw data -> preprocess -> train -> AUC -> ROC figure;
%   reconstructed dense-Lambda stress replay (diagnostic only).
%
% The reconstructed stress replay NEVER replaces the frozen Figure-5 CSV.

p = inputParser;
addParameter(p,'Offline',false,@(x)islogical(x)||isnumeric(x));
addParameter(p,'FreshVenv',true,@(x)islogical(x)||isnumeric(x));
addParameter(p,'OutDir','',@(x)ischar(x)||isstring(x));
addParameter(p,'RunHistoricalPlan',true,@(x)islogical(x)||isnumeric(x));
parse(p,varargin{:});
opt = p.Results;

thisFile = mfilename('fullpath');
assert(~isempty(thisFile),'RUN_REVIEWER_E2E must be run from its tracked file.');
repoRoot = fileparts(thisFile);
assert(isfile(fullfile(repoRoot,'RUN_SUBMISSION_FIGURES.m')), ...
    'Repository root could not be resolved.');

if strlength(string(opt.OutDir))==0
    runRoot = fullfile(tempdir,['CMDO_reviewer_e2e_' datestr(now,'yyyymmdd_HHMMSS')]); %#ok<DATST>
else
    runRoot = char(opt.OutDir);
end
if isfolder(runRoot), rmdir(runRoot,'s'); end
mkdir(runRoot);

fprintf('\n============================================================\n');
fprintf(' CMDO REVIEWER END-TO-END PORTABILITY AUDIT\n');
fprintf('============================================================\n');
fprintf('Repository : %s\n',repoRoot);
fprintf('Run root   : %s\n',runRoot);
fprintf('OS         : %s\n',computer);
fprintf('MATLAB     : %s\n',version);

% -------------------------------------------------------------------------
% 1) Checkout portability / author-path isolation
% -------------------------------------------------------------------------
fprintf('\n[1/7] Repository-relative submission preflight\n');
local_static_portability_audit(repoRoot);
fprintf('Repository-relative submission preflight: PASS\n');

% -------------------------------------------------------------------------
% 2-5) Python-side engineering loop (online mode)
% -------------------------------------------------------------------------
smokeRan = false;
stressRan = false;
venvPython = '';

if logical(opt.Offline)
    fprintf('\n[2/7] Isolated reviewer Python environment\n');
    fprintf('SKIP: Offline=true.\n');
    fprintf('\n[3/7] Repository engineering acceptance\n');
    fprintf('SKIP: Offline=true.\n');
    fprintf('\n[4/7] Public raw-data -> model -> metric -> figure smoke\n');
    fprintf('SKIP: Offline=true.\n');
    fprintf('\n[5/7] Reconstructed dense-Lambda stress diagnostic\n');
    fprintf('SKIP: Offline=true.\n');
else
    fprintf('\n[2/7] Isolated reviewer Python environment\n');
    basePython = local_find_python();
    venvRoot = fullfile(tempdir,'CMDO_reviewer_e2e_venv_v1');
    if logical(opt.FreshVenv) && isfolder(venvRoot), rmdir(venvRoot,'s'); end
    venvPython = local_venv_python(venvRoot);
    if ~isfile(venvPython)
        local_run(sprintf('%s -m venv %s',basePython,local_q(venvRoot)),repoRoot, ...
            'Create reviewer virtual environment');
    end
    assert(isfile(venvPython),'Reviewer virtual environment did not create Python.');

    req = fullfile(repoRoot,'environment','requirements-reviewer.txt');
    assert(isfile(req),'Missing environment/requirements-reviewer.txt');
    local_run(sprintf('%s -m pip install -r %s',local_q(venvPython),local_q(req)), ...
        repoRoot,'Install pinned reviewer requirements');
    local_run(sprintf('%s --version',local_q(venvPython)),repoRoot,'Reviewer Python');

    fprintf('\n[3/7] Repository engineering acceptance\n');
    local_run(sprintf('%s %s check',local_q(venvPython), ...
        local_q(fullfile(repoRoot,'RUN_REVIEWER.py'))),repoRoot,'RUN_REVIEWER.py check');

    fprintf('\n[4/7] Public raw-data -> model -> metric -> figure smoke\n');
    smokeOut = fullfile(runRoot,'public_smoke');
    cmd = sprintf('%s %s smoke --allow-network --run-prefix CMDO-E2E --output-root %s', ...
        local_q(venvPython),local_q(fullfile(repoRoot,'RUN_REVIEWER.py')),local_q(smokeOut));
    local_run(cmd,repoRoot,'Public UCI-296 raw-data smoke');
    local_assert_nonempty_recursive(smokeOut,'smoke_result.json');
    local_assert_nonempty_recursive(smokeOut,'smoke_roc.png');
    smokeRan = true;

    fprintf('\n[5/7] Reconstructed dense-Lambda stress diagnostic\n');
    stressScript = fullfile(repoRoot,'scripts','stress_replay', ...
        'CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py');
    assert(isfile(stressScript),'Missing reconstructed stress diagnostic.');
    stressOut = fullfile(runRoot,'stress_replay');
    local_run(sprintf('%s %s --outdir %s',local_q(venvPython),local_q(stressScript),local_q(stressOut)), ...
        repoRoot,'Dense-Lambda reconstructed stress replay');
    local_assert_nonempty_recursive(stressOut,'CMDO_SystemStress_AUC_StateSummary_v1_1.csv');
    stressRan = true;
    fprintf(['Role boundary: this replay is diagnostic only.\n' ...
             'The manuscript Figure 5 remains bound to the tracked frozen CSV.\n']);
end

% -------------------------------------------------------------------------
% 6) EXACT submission figures from tracked frozen records
% -------------------------------------------------------------------------
fprintf('\n[6/7] Exact manuscript figures from tracked frozen records\n');
figOut = fullfile(runRoot,'submission_figures');
summary = RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true,'OutDir',figOut);
assert(height(summary)==7 && all(summary.status=="PASS"), ...
    'Exact submission figure route did not pass 7/7.');

% -------------------------------------------------------------------------
% 7) Historical full-claim plan + Git-clean acceptance
% -------------------------------------------------------------------------
fprintf('\n[7/7] Historical-plan disclosure + Git-clean audit\n');
if logical(opt.RunHistoricalPlan) && ~logical(opt.Offline)
    planOut = fullfile(runRoot,'historical_plan');
    cmd = sprintf('%s %s full-claim --plan --run-id CMDO-E2E-FULL-PLAN --output-root %s', ...
        local_q(venvPython),local_q(fullfile(repoRoot,'RUN_REPRODUCTION.py')),local_q(planOut));
    local_run(cmd,repoRoot,'Historical raw-to-science plan');
end

gitClean = local_git_clean(repoRoot);
assert(gitClean,'Reviewer audit dirtied the Git checkout.');

result = struct();
result.classification = 'CMDO_REVIEWER_END_TO_END_PORTABILITY_AUDIT';
result.repository = repoRoot;
result.runRoot = runRoot;
result.publicRawDataSmoke = smokeRan;
result.stressReplayDiagnostic = stressRan;
result.exactSubmissionFigures = true;
result.figureCount = 7;
result.externalAuthorPaths = 0;
result.gitClean = true;
result.historicalFullClaimExecuted = false;
result.status = 'PASS';

reportPath = fullfile(runRoot,'CMDO_REVIEWER_E2E_REPORT.json');
fid = fopen(reportPath,'w');
assert(fid>0,'Could not write reviewer E2E report.');
c = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s',jsonencode(result,'PrettyPrint',true));

fprintf('\n============================================================\n');
fprintf(' CMDO REVIEWER END-TO-END PORTABILITY AUDIT: PASS\n');
fprintf('============================================================\n');
fprintf('Public raw data -> model -> smoke figure : %s\n',string(smokeRan));
fprintf('Stress replay diagnostic                 : %s\n',string(stressRan));
fprintf('Exact submission figures                 : 7/7 PASS\n');
fprintf('External author-machine paths            : 0\n');
fprintf('Git checkout clean                       : true\n');
fprintf('Report                                   : %s\n',reportPath);
fprintf('\nIMPORTANT CLAIM BOUNDARY\n');
fprintf(['The exact manuscript route is frozen derived records -> figures.\n' ...
         'The public raw-data smoke validates cross-machine execution, not a manuscript estimate.\n' ...
         'The reconstructed stress replay is diagnostic, not the manuscript Figure-5 source.\n' ...
         'The historical full-claim route is separately governed and may reach the documented\n' ...
         'scientific-divergence boundary; it is not required for submitted-figure reproduction.\n']);
fprintf('============================================================\n');

end

function local_static_portability_audit(repoRoot)
required = { ...
    'RUN_SUBMISSION_FIGURES.m'; ...
    fullfile('source_data','figure1_assets','Figure1_assets_selected_v1.mat'); ...
    fullfile('source_data','figure5_submission','CMDO_SystemStress_AUC_StateSummary_v1_1.csv'); ...
    fullfile('source_data','submission_frozen','StageU4C_Component_Fits_v1.1.csv'); ...
    fullfile('source_data','submission_frozen','StageU5B_Audit_State_Results_v1.0.csv'); ...
    fullfile('source_data','submission_frozen','StageU6_Audit_State_Results_v1.0.csv'); ...
    fullfile('source_data','submission_frozen','StageU7_State_Results_v1.0.csv'); ...
    fullfile('source_data','figure6_admissibility','CMDO_Admissibility_State_MSE_Audit.csv'); ...
    fullfile('U10_Prospective_ECG','01_Prospective_Result','U10_PRIMARY_RESULT.json'); ...
    fullfile('U11_Information_Closure','01_Result','U11_WORLD_PLUS_georgia_v0.1.csv')};
for i=1:numel(required)
    assert(isfile(fullfile(repoRoot,required{i})), ...
        'Missing tracked reviewer input: %s',required{i});
end
activeDir = fullfile(repoRoot,'matlab','submission_figures');
files = [dir(fullfile(activeDir,'*.m')); dir(fullfile(repoRoot,'RUN_SUBMISSION_FIGURES.m'))];
for i=1:numel(files)
    txt = fileread(fullfile(files(i).folder,files(i).name));
    forbidden = {'C:\Users\zyx\','F:\manuscript manual\','CMDO-U6-WSL-REPLAY','uigetfile('};
    for j=1:numel(forbidden)
        assert(~contains(txt,forbidden{j}), ...
            'Author-machine dependency found in %s: %s',files(i).name,forbidden{j});
    end
end
end

function basePython = local_find_python()
if ispc
    candidates = {'py -3','python'};
else
    candidates = {'python3','python'};
end
for i=1:numel(candidates)
    [status,~] = system([candidates{i} ' --version']);
    if status==0
        basePython = candidates{i};
        return;
    end
end
error('Python 3.10+ was not found on PATH.');
end

function path = local_venv_python(root)
if ispc
    path = fullfile(root,'Scripts','python.exe');
else
    path = fullfile(root,'bin','python');
end
end

function q = local_q(s)
s = char(s);
q = ['"' strrep(s,'"','\"') '"'];
end

function local_run(cmd,cwd,label)
fprintf('%s\n$ %s\n',label,cmd);
old = pwd;
c = onCleanup(@() cd(old)); %#ok<NASGU>
cd(cwd);
status = system(cmd,'-echo');
assert(status==0,'%s failed (exit=%d).',label,status);
end

function local_assert_nonempty_recursive(root,name)
assert(isfolder(root),'Expected output directory missing: %s',root);
hits = dir(fullfile(root,'**',name));
assert(~isempty(hits),'Expected generated file missing: %s',name);
assert(any([hits.bytes]>0),'Generated file is empty: %s',name);
end

function tf = local_git_clean(repoRoot)
if ~isfolder(fullfile(repoRoot,'.git'))
    tf = true;
    return;
end
[status,out] = system(sprintf('git -C %s status --porcelain',local_q(repoRoot)));
assert(status==0,'git status failed.');
tf = isempty(strtrim(out));
end
