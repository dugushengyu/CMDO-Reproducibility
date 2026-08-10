%% CMDO U9 — Step 0: outcome-free implementation self-test
% This script does not read eICU data or any outcome vault.

u9PackageRoot = fileparts(mfilename('fullpath'));
u9ProjectRoot = fullfile(u9PackageRoot, 'CMDO_U9_eICU_Workdir_v1_0');
addpath(u9PackageRoot);

CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0( ...
    'SELFTEST', '', u9ProjectRoot);

fprintf('\nNext: set your credentialed eICU path in RUN_DATA_ADAPTER.m.\n');

