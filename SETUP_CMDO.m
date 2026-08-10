function cfg = SETUP_CMDO()
%SETUP_CMDO Add the repository's stable MATLAB entry points to the path.
%
% Run this once after opening the repository. Stage-specific directories are
% deliberately not added recursively because U8 and U9 contain identically
% named RUN_PREPARE/RUN_UNSEAL scripts.

repoRoot = fileparts(mfilename('fullpath'));
stablePaths = {
    repoRoot
    fullfile(repoRoot, 'matlab')
    fullfile(repoRoot, 'matlab', 'runners')
    fullfile(repoRoot, 'matlab', 'figures', 'helpers')
    fullfile(repoRoot, 'matlab', 'figures', 'main')
    fullfile(repoRoot, 'matlab', 'figures', 'extended')
    };
for i = 1:numel(stablePaths)
    % Empty directories are not retained by ZIP archives or Git.  Skipping
    % them avoids a harmless but confusing addpath warning on first use.
    if isfolder(stablePaths{i})
        addpath(stablePaths{i});
    end
end

cfg = cmdo.load_config();
fprintf('CMDO repository: %s\n', cfg.repoRoot);
fprintf('Local configuration: %s\n', cfg.localConfigPath);
end
