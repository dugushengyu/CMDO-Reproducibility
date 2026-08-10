function results = RUN_CMDO_TESTS()
%RUN_CMDO_TESTS Run non-data unit tests for the portable MATLAB layer.

cfg = SETUP_CMDO();
suite = testsuite(fullfile(cfg.repoRoot, 'matlab', 'tests'), ...
    'IncludeSubfolders', true);
results = run(suite);
disp(results);
names = string({results.Name})';
passed = logical([results.Passed])';
failed = logical([results.Failed])';
incomplete = logical([results.Incomplete])';
durationValues = [results.Duration]';
if isduration(durationValues)
    durationSeconds = seconds(durationValues);
else
    durationSeconds = double(durationValues);
end
testReport = table(names, passed, failed, incomplete, durationSeconds, ...
    'VariableNames', {'test','passed','failed','incomplete','seconds'});
reportPath = fullfile(cfg.outputRoot, 'reports', 'test_run_report.csv');
writetable(testReport, reportPath);
fprintf('Test report: %s\n', reportPath);
if any([results.Failed])
    error('CMDO:TestsFailed', '%d CMDO unit tests failed.', nnz([results.Failed]));
end
end
