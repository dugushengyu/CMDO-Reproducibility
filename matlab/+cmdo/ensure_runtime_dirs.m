function ensure_runtime_dirs(cfg)
%ENSURE_RUNTIME_DIRS Create only disposable/generated output directories.

targets = {cfg.outputRoot, cfg.cacheRoot, ...
    fullfile(cfg.outputRoot, 'figures'), ...
    fullfile(cfg.outputRoot, 'reports')};
for i = 1:numel(targets)
    if ~isfolder(targets{i})
        mkdir(targets{i});
    end
end
end
