function cfg = load_config(configPath)
%LOAD_CONFIG Read machine-local paths without committing them to Git.

repoRoot = cmdo.repo_root();
if nargin < 1 || strlength(string(configPath)) == 0
    configPath = fullfile(repoRoot, 'config', 'local_paths.json');
end
configPath = char(configPath);

cfg = struct();
cfg.repoRoot = repoRoot;
cfg.projectRoot = repoRoot;
cfg.dataRoot = fullfile(repoRoot, 'data');
cfg.canonicalRecordDir = fullfile(repoRoot, 'data', 'canonical_records');
cfg.outputRoot = fullfile(repoRoot, 'outputs');
cfg.cacheRoot = fullfile(repoRoot, 'outputs', 'cache');
cfg.pythonExecutable = 'python';
cfg.enableGPU = true;
cfg.allowSealedReexecution = false;
cfg.localConfigPath = configPath;
cfg.localConfigLoaded = false;

if isfile(configPath)
    userCfg = jsondecode(fileread(configPath));
    names = fieldnames(userCfg);
    for i = 1:numel(names)
        cfg.(names{i}) = userCfg.(names{i});
    end
    cfg.localConfigLoaded = true;
end

cfg = apply_environment(cfg, 'CMDO_PROJECT_ROOT', 'projectRoot');
cfg = apply_environment(cfg, 'CMDO_DATA_ROOT', 'dataRoot');
cfg = apply_environment(cfg, 'CMDO_CANONICAL_RECORD_DIR', 'canonicalRecordDir');
cfg = apply_environment(cfg, 'CMDO_OUTPUT_ROOT', 'outputRoot');
cfg = apply_environment(cfg, 'CMDO_CACHE_ROOT', 'cacheRoot');
cfg = apply_environment(cfg, 'CMDO_PYTHON', 'pythonExecutable');

pathFields = {'repoRoot','projectRoot','dataRoot','canonicalRecordDir', ...
    'outputRoot','cacheRoot','localConfigPath'};
for i = 1:numel(pathFields)
    name = pathFields{i};
    cfg.(name) = char(string(cfg.(name)));
end
cfg.pythonExecutable = char(string(cfg.pythonExecutable));
cfg.enableGPU = logical(cfg.enableGPU);
cfg.allowSealedReexecution = logical(cfg.allowSealedReexecution);
end

function cfg = apply_environment(cfg, environmentName, fieldName)
value = getenv(environmentName);
if ~isempty(value)
    cfg.(fieldName) = value;
end
end
