% CMDO U8 complete disclosed post-unseal reconstruction v1.1.0.
% Run this script from the extracted package. No manual file merging is needed.

scriptDir = fileparts(mfilename('fullpath'));
addpath(scriptDir);
projectRoot = fullfile(scriptDir, 'CMDO_U8_NHANES_PostUnseal_Workdir_v1_1_0');
CMDO_U8_NHANES_PostUnseal_Complete_Rerun_v1_1_0(projectRoot);

