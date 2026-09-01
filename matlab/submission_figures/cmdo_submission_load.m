function D = cmdo_submission_load(repoRoot)
%CMDO_SUBMISSION_LOAD Load only tracked reviewer-facing frozen tables.

if nargin < 1 || isempty(repoRoot)
    thisFile = mfilename('fullpath');
    scriptDir = fileparts(thisFile);
    repoRoot = fileparts(fileparts(scriptDir));
end

dataDir = fullfile(repoRoot,'source_data','submission_frozen');

assert(isfolder(dataDir), ...
    ['Missing reviewer-facing frozen source-data folder:' newline dataDir]);

D = struct();

D.u6_state = local_read(dataDir,'StageU6_Audit_State_Results_v1.0.csv');
D.u6_target = local_read(dataDir,'StageU6_Target_Summary_v1.0.csv');

D.u7_state = local_read(dataDir,'StageU7_State_Results_v1.0.csv');
D.u7_target = local_read(dataDir,'StageU7_Target_Metric_Summary_v1.0.csv');
D.u7_metric = local_read(dataDir,'StageU7_Metric_Summary_v1.0.csv');

end

function T = local_read(dataDir,name)
path = fullfile(dataDir,name);
assert(isfile(path), ...
    ['Missing tracked submission record:' newline path]);
T = readtable(path,'VariableNamingRule','preserve');
end
