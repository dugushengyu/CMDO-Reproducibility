% CMDO U8 phase 2. DO NOT RUN until a hash-matched authorization file has
% been issued after independent inspection of the PREPARE seal.

packageDir = fileparts(mfilename('fullpath'));
addpath(packageDir);
projectRoot = fullfile(packageDir, 'CMDO_U8_NHANES_Workdir_v1_0');
CMDO_U8_NHANES_Certifiable_Natural_Prevalence_v1_0("UNSEAL", projectRoot);
