% CMDO U8 phase 1. Safe to run before reserve outcome authorization.
% This phase refuses to download or accept reserve HbA1c files.

packageDir = fileparts(mfilename('fullpath'));
addpath(packageDir);
projectRoot = fullfile(packageDir, 'CMDO_U8_NHANES_Workdir_v1_0');
CMDO_U8_NHANES_Certifiable_Natural_Prevalence_v1_0("PREPARE", projectRoot);
