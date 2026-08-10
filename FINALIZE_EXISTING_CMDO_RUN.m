function output = FINALIZE_EXISTING_CMDO_RUN()
%FINALIZE_EXISTING_CMDO_RUN Finalize an already-rendered safe acceptance run.
%
% Use this after figures and compatibility PDFs were written but the former
% R4 top-level runner failed while rereading pdf_compatibility_report.csv.
% The function does not rerender figures, re-execute U8 or access U9 outcomes.

cfg = SETUP_CMDO();
environment = RUN_ENVIRONMENT_CHECK();
if ~environment.readyForFigures
    error('CMDO:NotReadyForFinalize', ...
        'Environment or canonical-record verification is not ready.');
end

reportRoot = fullfile(cfg.outputRoot, 'reports');
testPath = fullfile(reportRoot, 'test_run_report.csv');
figurePath = fullfile(reportRoot, 'figure_run_report.csv');
pdfPath = fullfile(reportRoot, 'pdf_compatibility_report.csv');

tests = read_report(testPath, 5, 'test');
figures = read_report(figurePath, 5, 'figure');
pdfCompatibility = read_report(pdfPath, 4, 'PDF compatibility');

testPassed = as_logical(tests{:,2}, testPath, 'passed');
testFailed = as_logical(tests{:,3}, testPath, 'failed');
testIncomplete = as_logical(tests{:,4}, testPath, 'incomplete');
figureStatus = upper(strtrim(string(figures{:,2})));
pdfStatus = upper(strtrim(string(pdfCompatibility{:,3})));

if isempty(testPassed) || any(~testPassed | testFailed | testIncomplete)
    error('CMDO:ExistingTestsFailed', ...
        'The existing test report is missing passing results or contains a failure.');
end
if isempty(figureStatus) || any(figureStatus ~= "PASS")
    error('CMDO:ExistingFiguresFailed', ...
        'The existing figure report contains a missing or failed figure.');
end
if isempty(pdfStatus) || any(pdfStatus ~= "PASS")
    error('CMDO:ExistingCompatibilityPdfFailed', ...
        'The existing compatibility-PDF report contains a missing or failed PDF.');
end
if height(pdfCompatibility) < height(figures)
    error('CMDO:ExistingCompatibilityPdfMissing', ...
        'Only %d compatibility PDFs are reported for %d figures.', ...
        height(pdfCompatibility), height(figures));
end

acceptance = struct( ...
    'checkedAt', environment.checkedAt, ...
    'environmentReady', environment.readyForFigures, ...
    'testCount', height(tests), ...
    'testFailures', nnz(~testPassed | testFailed | testIncomplete), ...
    'figureCount', height(figures), ...
    'figureGenerationFailures', nnz(figureStatus == "FAIL"), ...
    'compatibilityPdfCount', height(pdfCompatibility), ...
    'compatibilityPdfFailures', nnz(pdfStatus == "FAIL"), ...
    'visualReview', 'PENDING_EXTERNAL_QA', ...
    'u8Reexecuted', false, ...
    'u9Unsealed', false, ...
    'finalizedFromExistingOutputs', true);

acceptancePath = fullfile(reportRoot, 'local_acceptance_summary.json');
cmdo.write_json(acceptancePath, acceptance);
fprintf('\nExisting CMDO run finalized without rerendering.\n');
fprintf('  Tests: %d passed, 0 failed\n', height(tests));
fprintf('  Figures: %d passed, 0 failed\n', height(figures));
fprintf('  Compatibility PDFs: %d passed, 0 failed\n', ...
    height(pdfCompatibility));
fprintf('  Acceptance summary: %s\n\n', acceptancePath);

output = struct('mode','FINALIZE_EXISTING', ...
    'environment',environment, ...
    'tests',tests, ...
    'figures',figures, ...
    'pdfCompatibility',pdfCompatibility, ...
    'acceptance',acceptance);
end

function report = read_report(path, minimumWidth, label)
if ~isfile(path)
    error('CMDO:MissingExistingReport', 'Missing %s report: %s', label, path);
end

% Variable names are deliberately not referenced.  Some MATLAB releases
% truncate imported CSV headings even with VariableNamingRule='preserve'.
% Report schemas are stable and status fields are therefore read by column.
report = readtable(path, 'FileType', 'text', 'Delimiter', ',', ...
    'ReadVariableNames', true, 'TextType', 'string', ...
    'VariableNamingRule', 'modify');
if height(report) == 0 || width(report) < minimumWidth
    error('CMDO:InvalidExistingReport', ...
        'The %s report is empty or has an invalid schema: %s', label, path);
end
end

function tf = as_logical(values, path, label)
if islogical(values)
    tf = values;
elseif isnumeric(values)
    tf = values ~= 0;
else
    text = lower(strtrim(string(values)));
    valid = ismember(text, ["true","false","1","0"]);
    if any(~valid)
        error('CMDO:InvalidLogicalReportValue', ...
            'Invalid %s value in report: %s', label, path);
    end
    tf = ismember(text, ["true","1"]);
end
tf = logical(tf(:));
end
