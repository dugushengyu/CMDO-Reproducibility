function result = RUN_REVIEWER_E2E(varargin)
% Cross-machine reviewer audit. Exact manuscript route remains frozen-records -> figures.
p = inputParser;
addParameter(p,'Offline',false,@(x)islogical(x)||isnumeric(x));
addParameter(p,'FreshVenv',true,@(x)islogical(x)||isnumeric(x));
addParameter(p,'OutDir','',@(x)ischar(x)||isstring(x));
addParameter(p,'RunHistoricalPlan',true,@(x)islogical(x)||isnumeric(x));
parse(p,varargin{:}); opt=p.Results;

thisFile=mfilename('fullpath'); assert(~isempty(thisFile),'Run the tracked RUN_REVIEWER_E2E.m file.');
repoRoot=fileparts(thisFile);
assert(isfile(fullfile(repoRoot,'RUN_SUBMISSION_FIGURES.m')),'Repository root not resolved.');
if strlength(string(opt.OutDir))==0
    runRoot=fullfile(tempdir,['CMDO_reviewer_e2e_' datestr(now,'yyyymmdd_HHMMSS')]); %#ok<DATST>
else
    runRoot=char(opt.OutDir);
end
if isfolder(runRoot), rmdir(runRoot,'s'); end; mkdir(runRoot);

fprintf('\n============================================================\n');
fprintf(' CMDO REVIEWER END-TO-END PORTABILITY AUDIT\n');
fprintf('============================================================\n');
fprintf('Repository : %s\nRun root   : %s\nOS         : %s\nMATLAB     : %s\n',repoRoot,runRoot,computer,version);

fprintf('\n[1/7] Repository-relative submission preflight\n');
local_static_audit(repoRoot); fprintf('PASS\n');

smokeRan=false; stressRan=false; venvPython='';
if logical(opt.Offline)
    fprintf('\n[2/7] Python environment: SKIP (offline)\n');
    fprintf('[3/7] Repository engineering acceptance: SKIP (offline)\n');
    fprintf('[4/7] Public raw-data smoke: SKIP (offline)\n');
    fprintf('[5/7] Stress replay diagnostic: SKIP (offline)\n');
else
    fprintf('\n[2/7] Isolated reviewer Python environment\n');
    basePython=local_find_python();
    venvRoot=fullfile(tempdir,'CMDO_reviewer_e2e_venv_v1');
    if logical(opt.FreshVenv)&&isfolder(venvRoot), rmdir(venvRoot,'s'); end
    venvPython=local_venv_python(venvRoot);
    if ~isfile(venvPython)
        local_run(sprintf('%s -m venv %s',basePython,local_q(venvRoot)),repoRoot,'Create reviewer venv');
    end
    req=fullfile(repoRoot,'environment','requirements-reviewer.txt'); assert(isfile(req),'Missing reviewer requirements.');
    local_run(sprintf('%s -m pip install -r %s',local_q(venvPython),local_q(req)),repoRoot,'Install pinned reviewer requirements');

    fprintf('\n[3/7] Repository engineering acceptance\n');
    local_run(sprintf('%s %s check',local_q(venvPython),local_q(fullfile(repoRoot,'RUN_REVIEWER.py'))),repoRoot,'RUN_REVIEWER.py check');

    fprintf('\n[4/7] Public raw-data -> model -> metric -> figure smoke\n');
    smokeOut=fullfile(runRoot,'public_smoke');
    local_run(sprintf('%s %s smoke --allow-network --run-prefix CMDO-E2E --output-root %s', ...
        local_q(venvPython),local_q(fullfile(repoRoot,'RUN_REVIEWER.py')),local_q(smokeOut)),repoRoot,'Public UCI-296 smoke');
    local_assert_output(smokeOut,'smoke_result.json'); local_assert_output(smokeOut,'smoke_roc.png'); smokeRan=true;

    fprintf('\n[5/7] Reconstructed dense-Lambda stress diagnostic\n');
    stressScript=fullfile(repoRoot,'scripts','stress_replay','CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py');
    assert(isfile(stressScript),'Missing reconstructed stress script.'); stressOut=fullfile(runRoot,'stress_replay');
    local_run(sprintf('%s %s --outdir %s',local_q(venvPython),local_q(stressScript),local_q(stressOut)),repoRoot,'Dense-Lambda reconstructed replay');
    local_assert_output(stressOut,'CMDO_SystemStress_AUC_StateSummary_v1_1.csv'); stressRan=true;
    fprintf('Diagnostic only: manuscript Figure 5 remains bound to the tracked frozen CSV.\n');
end

fprintf('\n[6/7] Exact manuscript figures from tracked frozen records\n');
figOut=fullfile(runRoot,'submission_figures');
summary=RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true,'OutDir',figOut);
assert(height(summary)==7&&all(summary.status=="PASS"),'Exact submission route did not pass 7/7.');

fprintf('\n[7/7] Historical-plan disclosure + Git-clean audit\n');
if logical(opt.RunHistoricalPlan)&&~logical(opt.Offline)
    planOut=fullfile(runRoot,'historical_plan');
    local_run(sprintf('%s %s full-claim --plan --run-id CMDO-E2E-FULL-PLAN --output-root %s', ...
        local_q(venvPython),local_q(fullfile(repoRoot,'RUN_REPRODUCTION.py')),local_q(planOut)),repoRoot,'Historical raw-to-science plan');
end
assert(local_git_clean(repoRoot),'Reviewer audit dirtied the Git checkout.');

result=struct('classification','CMDO_REVIEWER_END_TO_END_PORTABILITY_AUDIT','repository',repoRoot, ...
    'runRoot',runRoot,'publicRawDataSmoke',smokeRan,'stressReplayDiagnostic',stressRan, ...
    'exactSubmissionFigures',true,'figureCount',7,'externalAuthorPaths',0,'gitClean',true, ...
    'historicalFullClaimExecuted',false,'status','PASS');
reportPath=fullfile(runRoot,'CMDO_REVIEWER_E2E_REPORT.json');
fid=fopen(reportPath,'w'); assert(fid>0,'Could not write E2E report.'); c=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s',jsonencode(result,'PrettyPrint',true));

fprintf('\n============================================================\n');
fprintf(' CMDO REVIEWER END-TO-END PORTABILITY AUDIT: PASS\n');
fprintf('============================================================\n');
fprintf('Public raw data -> smoke figure : %s\n',string(smokeRan));
fprintf('Stress replay diagnostic        : %s\n',string(stressRan));
fprintf('Exact submission figures        : 7/7 PASS\n');
fprintf('External author-machine paths   : 0\nGit checkout clean              : true\n');
fprintf('Report                          : %s\n',reportPath);
fprintf(['Claim boundary: exact manuscript reproduction is frozen derived records -> figures.\n' ...
    'The public smoke is an engineering test; reconstructed stress is diagnostic only.\n' ...
    'The historical full-claim replay is separately governed and may reach the disclosed scientific-divergence boundary.\n']);
fprintf('============================================================\n');
end

function local_static_audit(repoRoot)
required={ ...
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
for i=1:numel(required), assert(isfile(fullfile(repoRoot,required{i})),'Missing reviewer input: %s',required{i}); end
activeDir=fullfile(repoRoot,'matlab','submission_figures'); files=dir(fullfile(activeDir,'*.m'));
for i=1:numel(files)
 txt=fileread(fullfile(files(i).folder,files(i).name));
 forbidden={'C:\Users\zyx\','F:\manuscript manual\','CMDO-U6-WSL-REPLAY','uigetfile('};
 for j=1:numel(forbidden), assert(~contains(txt,forbidden{j}),'Author-machine dependency in %s: %s',files(i).name,forbidden{j}); end
end
end

function base=local_find_python()
if ispc, candidates={'py -3','python'}; else, candidates={'python3','python'}; end
for i=1:numel(candidates), [st,~]=system([candidates{i} ' --version']); if st==0, base=candidates{i}; return; end; end
error('Python 3.10+ not found on PATH.');
end
function p=local_venv_python(root), if ispc, p=fullfile(root,'Scripts','python.exe'); else, p=fullfile(root,'bin','python'); end; end
function q=local_q(s), s=char(s); q=['"' strrep(s,'"','\"') '"']; end
function local_run(cmd,cwd,label), fprintf('%s\n$ %s\n',label,cmd); old=pwd; c=onCleanup(@()cd(old)); cd(cwd); st=system(cmd,'-echo'); assert(st==0,'%s failed (exit=%d).',label,st); end %#ok<NASGU>
function local_assert_output(root,name), assert(isfolder(root),'Missing output directory: %s',root); h=dir(fullfile(root,'**',name)); assert(~isempty(h)&&any([h.bytes]>0),'Missing/empty generated output: %s',name); end
function tf=local_git_clean(repoRoot), if ~isfolder(fullfile(repoRoot,'.git')), tf=true; return; end; [st,out]=system(sprintf('git -C %s status --porcelain',local_q(repoRoot))); assert(st==0,'git status failed.'); tf=isempty(strtrim(out)); end
