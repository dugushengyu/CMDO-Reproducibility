%% CMDO U9 — Step 1: build the outcome-separated eICU analytical record
% Prerequisite: credentialed eICU-CRD v2.0 files obtained under the
% PhysioNet data-use agreement. Do not send raw eICU files to anyone.

u9PackageRoot = fileparts(mfilename('fullpath'));
u9ProjectRoot = fullfile(u9PackageRoot, 'CMDO_U9_eICU_Workdir_v1_0');

% Preferred: define the environment variable CMDO_EICU_ROOT.
u9RawDataRoot = getenv('CMDO_EICU_ROOT');

% Or replace the next value with the folder containing patient.csv,
% apachePatientResult.csv and hospital.csv (or their .csv.gz versions).
if strlength(string(u9RawDataRoot)) == 0
    u9RawDataRoot = 'EDIT_THIS_PATH_TO_EICU_CRD_2_0';
end

if ~isfolder(u9RawDataRoot)
    error(['eICU folder not found. Set CMDO_EICU_ROOT or edit u9RawDataRoot ' ...
        'inside RUN_DATA_ADAPTER.m. Current value: ' char(u9RawDataRoot)]);
end

addpath(u9PackageRoot);
CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0( ...
    'ADAPT', u9RawDataRoot, u9ProjectRoot);

fprintf('\nAdapter complete. Do not open files in 00_RESTRICTED_DO_NOT_SHARE.\n');
fprintf('Next: run RUN_PREPARE.m.\n');

