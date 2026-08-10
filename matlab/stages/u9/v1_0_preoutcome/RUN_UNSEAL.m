%% CMDO U9 — Step 3: one-time reserve evaluation
% Run only after an independent reviewer has issued a hash-matched
% StageU9_EXECUTION_AUTHORIZATION_v1_0.json in 01_PreOutcome_Seal.
% A permanent one-shot marker is written before any reserve outcome is read.

u9PackageRoot = fileparts(mfilename('fullpath'));
u9ProjectRoot = fullfile(u9PackageRoot, 'CMDO_U9_eICU_Workdir_v1_0');
u9Authorization = fullfile(u9ProjectRoot, '01_PreOutcome_Seal', ...
    'StageU9_EXECUTION_AUTHORIZATION_v1_0.json');

if ~isfile(u9Authorization)
    error(['Authorization is missing. Return the pre-outcome seal for review; ' ...
        'do not create or edit the authorization yourself.']);
end

fprintf('\nWARNING: U9 UNSEAL IS A ONE-TIME OPERATION.\n');
fprintf('A marker will be committed before reserve outcomes are opened.\n');
u9Confirmation = input('Type exactly UNSEAL U9 ONCE to continue: ', 's');
if ~strcmp(u9Confirmation, 'UNSEAL U9 ONCE')
    error('UNSEAL cancelled; no reserve outcome was read.');
end

addpath(u9PackageRoot);
CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0( ...
    'UNSEAL', '', u9ProjectRoot);

fprintf('\nReturn the canonical ZIP and its companion commit JSON for interpretation.\n');

