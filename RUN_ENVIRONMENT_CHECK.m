function report = RUN_ENVIRONMENT_CHECK()
%RUN_ENVIRONMENT_CHECK Audit local paths, toolboxes, GPU and source hashes.

cfg = SETUP_CMDO();
cmdo.ensure_runtime_dirs(cfg);

report = struct();
report.checkedAt = char(datetime('now', 'TimeZone', 'Asia/Singapore', ...
    'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
report.matlabVersion = version;
report.matlabRelease = version('-release');
report.computer = computer;
report.repoRoot = cfg.repoRoot;
report.localConfigPath = cfg.localConfigPath;
report.localConfigLoaded = cfg.localConfigLoaded;
if cfg.localConfigLoaded
    report.configurationMode = 'local_paths.json';
else
    report.configurationMode = 'portable repository defaults';
end
report.paths = struct( ...
    'projectRoot', cfg.projectRoot, ...
    'dataRoot', cfg.dataRoot, ...
    'canonicalRecordDir', cfg.canonicalRecordDir, ...
    'outputRoot', cfg.outputRoot, ...
    'cacheRoot', cfg.cacheRoot);

requiredFunctions = {'readtable','jsondecode','exportgraphics','xptread', ...
    'fitclinear','betainv','tiedrank','perfcurve'};
present = false(size(requiredFunctions));
for i = 1:numel(requiredFunctions)
    present(i) = ~isempty(which(requiredFunctions{i})) || ...
        exist(requiredFunctions{i}, 'file') == 2 || ...
        exist(requiredFunctions{i}, 'builtin') == 5;
end
report.requiredFunctions = cell2struct(num2cell(present), ...
    matlab.lang.makeValidName(requiredFunctions), 2);

[gpuAvailable, gpuInfo] = cmdo.has_gpu(cfg.enableGPU);
report.gpuAvailable = gpuAvailable;
report.gpu = gpuInfo;

canonical = cmdo.check_canonical_archives(cfg, false);
report.canonicalArchives = table2struct(canonical);

try
    imported = cmdo.verify_import_manifest(false);
    report.importedSourcesChecked = height(imported);
    report.importedSourcesPassing = nnz(imported.matches);
    report.importedSourcesAllPass = all(imported.matches);
catch ME
    report.importedSourcesChecked = 0;
    report.importedSourcesPassing = 0;
    report.importedSourcesAllPass = false;
    report.importManifestMessage = ME.message;
end

report.sourceWorkbookPresent = isfile(fullfile(cfg.repoRoot, 'source_data', ...
    'SourceData_Figure5_U7_U8_and_ED7_U8.xlsx'));
report.readyForFigures = all(canonical.verified) && report.importedSourcesAllPass ...
    && report.sourceWorkbookPresent;
report.readyForU8U9 = all(present);

reportPath = fullfile(cfg.outputRoot, 'reports', 'environment_report.json');
cmdo.write_json(reportPath, report);

fprintf('\nCMDO environment check\n');
fprintf('  MATLAB: %s (%s)\n', report.matlabVersion, report.matlabRelease);
fprintf('  Configuration: %s\n', report.configurationMode);
fprintf('  Canonical archives verified: %d/%d\n', ...
    nnz(canonical.verified), height(canonical));
fprintf('  Imported-source hashes: %d/%d\n', ...
    report.importedSourcesPassing, report.importedSourcesChecked);
fprintf('  GPU available: %d', report.gpuAvailable);
if strlength(string(report.gpu.name)) > 0
    fprintf(' (%s)', report.gpu.name);
end
fprintf('\n  Ready for all figures: %d\n', report.readyForFigures);
fprintf('  Report: %s\n\n', reportPath);
if ~all(canonical.verified)
    fprintf('  Put the missing canonical ZIP files in:\n    %s\n', ...
        cfg.canonicalRecordDir);
    fprintf('  Missing or invalid: %s\n\n', ...
        strjoin(canonical.archive(~canonical.verified), ', '));
elseif report.readyForFigures
    fprintf('  Environment ready. Safe full command: RUN_ALL_CMDO\n\n');
end
end
