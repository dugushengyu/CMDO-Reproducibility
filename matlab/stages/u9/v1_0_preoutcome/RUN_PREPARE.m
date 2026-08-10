%% CMDO U9 — Step 2: freeze the pre-outcome design and seal
% PREPARE reads development outcomes only. It hashes, but does not read,
% the reserve-outcome vault.

u9PackageRoot = fileparts(mfilename('fullpath'));
u9ProjectRoot = fullfile(u9PackageRoot, 'CMDO_U9_eICU_Workdir_v1_0');
addpath(u9PackageRoot);

CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0( ...
    'PREPARE', '', u9ProjectRoot);

fprintf('\nSTOP HERE. Do not run RUN_UNSEAL.m yet.\n');
fprintf(['Return only the files listed in U9_Results_Return_Checklist_v1_0.md ' ...
    'for independent seal review.\n']);

