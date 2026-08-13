%% CMDO U9 Amendment A1 — public-demo engineering regression
% Engineering validation only. No scientific claim. No PREPARE. No UNSEAL.

packageRoot = fileparts(mfilename('fullpath'));
addpath(packageRoot);

demoRoot = getenv('CMDO_EICU_DEMO_ROOT');
testRoot = getenv('CMDO_U9_A1_REGRESSION_ROOT');

if strlength(string(demoRoot)) == 0 || ~isfolder(demoRoot)
    error('CMDO:U9:A1:DemoRoot', 'Set CMDO_EICU_DEMO_ROOT to the official public eICU demo v2.0 folder.');
end
if strlength(string(testRoot)) == 0
    testRoot = fullfile(tempdir, 'CMDO_U9_A1_REGRESSION');
end
if isfolder(testRoot)
    rmdir(testRoot, 's');
end
mkdir(testRoot);

fprintf('\n================ CMDO U9 A1 REGRESSION ================\n');
fprintf('Demo root: %s\n', demoRoot);
fprintf('Test root: %s\n', testRoot);

% Static frozen-constant checks on the amended authoritative implementation.
codePath = fullfile(packageRoot, 'CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0.m');
codeText = fileread(codePath);

mustContain = {
    'C.apache_version = 4;'
    'C.minimum_age = 18;'
    'C.minimum_hospital_roster = 512;'
    'C.source_hospitals = 6;'
    'C.history_hospitals = 6;'
    'C.calibration_hospitals = 6;'
    'C.reserve_hospitals = 20;'
    'C.budgets = [64 128 256];'
    'C.replicates = 200;'
    'C.folds = 4;'
    'C.max_transport_weight = 0.35;'
    'C.decision_guard_band = 0.01;'
    'C.role_seed = 2026081001;'
    'C.master_seed = 2026081002;'
    'C.calibration_seed = 2026081003;'
    'C.telemetry_pair_count = 10;'
    'apachePatientResultsID'
    'apachepatientresultsid'
    '[~, caseUnique] = unique(lower(paths), ''stable'');'
    'paths = paths(caseUnique);'
};
for i = 1:numel(mustContain)
    assert(contains(codeText, mustContain{i}), ...
        'CMDO:U9:A1:FrozenConstant', 'Missing frozen token: %s', mustContain{i});
end
assert(~contains(codeText, 'apachePatientsResultsID'), ...
    'CMDO:U9:A1:OldSchemaToken', 'Old APACHE schema token remains.');
assert(~contains(codeText, 'apachepatientsresultsid'), ...
    'CMDO:U9:A1:OldCanonicalToken', 'Old canonical APACHE token remains.');

% Verify exactly the three official demo tables are available.
requiredFiles = {
    'patient.csv.gz'
    'apachePatientResult.csv.gz'
    'hospital.csv.gz'
};
for i = 1:numel(requiredFiles)
    assert(isfile(fullfile(demoRoot, requiredFiles{i})), ...
        'CMDO:U9:A1:DemoFile', 'Missing demo file: %s', requiredFiles{i});
end

% Native mathematical/implementation self-test on amended code.
selfRoot = fullfile(testRoot, 'selftest');
CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0('SELFTEST', demoRoot, selfRoot);

% Official adapter regression. The public demo is intentionally too small;
% the expected terminal boundary is the immutable 38-hospital gate.
adaptRoot = fullfile(testRoot, 'adapter');
caught = "";
caughtMessage = "";
try
    CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0('ADAPT', demoRoot, adaptRoot);
    error('CMDO:U9:A1:UnexpectedPass', ...
        'Public demo unexpectedly passed the frozen 38-hospital gate.');
catch ME
    caught = string(ME.identifier);
    caughtMessage = string(ME.message);
    if caught ~= "CMDO:U9:HospitalCount"
        rethrow(ME);
    end
end

% No scientific/sealed outputs are permitted in the engineering dry run.
forbidden = {
    fullfile(adaptRoot, '01_PreOutcome_Seal', 'StageU9_PreOutcome_Seal_v1_0.json')
    fullfile(adaptRoot, '03_Results', 'StageU9_ONE_SHOT_ANALYSIS_STARTED_v1_0.json')
    fullfile(adaptRoot, '05_Canonical', 'StageU9_Complete_v1_0.json')
};
for i = 1:numel(forbidden)
    assert(~isfile(forbidden{i}), ...
        'CMDO:U9:A1:ForbiddenArtifact', 'Forbidden formal U9 artefact exists: %s', forbidden{i});
end

record = struct();
record.classification = 'CMDO_U9_PREOUTCOME_ENGINEERING_AMENDMENT_A1_REGRESSION_PASS';
record.purpose = 'PUBLIC_DEMO_ENGINEERING_SCHEMA_REGRESSION_ONLY';
record.native_selftest_passed = true;
record.adapter_expected_boundary = char(caught);
record.adapter_expected_boundary_message = char(caughtMessage);
record.full_eicu_outcomes_accessed = false;
record.prepare_executed = false;
record.unseal_executed = false;
record.scientific_claim_created = false;
record.minimum_hospital_roster = 512;
record.required_hospitals = 38;
record.source_hospitals = 6;
record.history_hospitals = 6;
record.calibration_hospitals = 6;
record.reserve_hospitals = 20;
record.budgets = [64 128 256];
record.replicates = 200;
record.role_seed = 2026081001;
record.master_seed = 2026081002;
record.calibration_seed = 2026081003;

jsonPath = fullfile(testRoot, 'U9_AMENDMENT_A1_REGRESSION_PASS.json');
fid = fopen(jsonPath, 'w');
assert(fid > 0, 'Could not open regression JSON for writing.');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', jsonencode(record, PrettyPrint=true));
clear cleanup;

fprintf('\nCMDO_U9_PREOUTCOME_ENGINEERING_AMENDMENT_A1_REGRESSION_PASS\n');
fprintf('Expected terminal boundary: %s\n', caught);
fprintf('PREPARE executed: FALSE\n');
fprintf('UNSEAL executed: FALSE\n');
fprintf('Scientific claim created: FALSE\n');
fprintf('Regression record: %s\n', jsonPath);