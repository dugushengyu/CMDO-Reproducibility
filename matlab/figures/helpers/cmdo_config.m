function cfg = cmdo_config(figureName)
%CMDO_CONFIG Build portable paths for figure generation.

if nargin < 1
    figureName = 'CMDO';
end
base = cmdo.load_config();
cmdo.ensure_runtime_dirs(base);

cfg = base;
cfg.figureName = char(string(figureName));
cfg.outputDir = fullfile(base.outputRoot, 'figures', 'main');
cfg.extendedOutputDir = fullfile(base.outputRoot, 'figures', 'extended');
cfg.canonicalDataDir = base.canonicalRecordDir;
cfg.figureCacheDir = fullfile(base.cacheRoot, 'figures');
dirs = {cfg.outputDir, cfg.extendedOutputDir, cfg.figureCacheDir};
for i = 1:numel(dirs)
    if ~isfolder(dirs{i})
        mkdir(dirs{i});
    end
end
end
