function [results, compatibilityReport] = RUN_ALL_FIGURES(varargin)
%RUN_ALL_FIGURES Render current main and extended figures from local records.

p = inputParser;
addParameter(p, 'IncludeMain', true, @(x) islogical(x) && isscalar(x));
addParameter(p, 'IncludeExtended', true, @(x) islogical(x) && isscalar(x));
addParameter(p, 'IncludePreU8Figure5', false, @(x) islogical(x) && isscalar(x));
addParameter(p, 'Batch', true, @(x) islogical(x) && isscalar(x));
addParameter(p, 'Strict', true, @(x) islogical(x) && isscalar(x));
parse(p, varargin{:});
opt = p.Results;

cfg = SETUP_CMDO();
cmdo.check_canonical_archives(cfg, true);
sourceWorkbook = fullfile(cfg.repoRoot, 'source_data', ...
    'SourceData_Figure5_U7_U8_and_ED7_U8.xlsx');
if ~isfile(sourceWorkbook)
    error('CMDO:MissingSourceWorkbook', 'Missing source workbook: %s', sourceWorkbook);
end

previousBatch = getenv('CMDO_BATCH_MODE');
cleanup = onCleanup(@() setenv('CMDO_BATCH_MODE', previousBatch)); %#ok<NASGU>
if opt.Batch
    setenv('CMDO_BATCH_MODE', '1');
else
    setenv('CMDO_BATCH_MODE', '0');
end

names = strings(0,1);
actions = cell(0,1);
if opt.IncludeMain
    names(end+1,1) = "Figure1"; actions{end+1,1} = @() Figure1();
    names(end+1,1) = "Figure2"; actions{end+1,1} = @() Figure2();
    names(end+1,1) = "Figure3"; actions{end+1,1} = @() Figure3();
    names(end+1,1) = "Figure4"; actions{end+1,1} = @() Figure4();
    names(end+1,1) = "Figure5_OperationalBoundary"; actions{end+1,1} = @() Figure5();
    names(end+1,1) = "Figure6_AdmissibilityComposability"; actions{end+1,1} = @() Figure6();
    if opt.IncludePreU8Figure5
        names(end+1,1) = "Figure5_PreU8"; actions{end+1,1} = @() Figure5_PreU8();
    end
end
if opt.IncludeExtended
    names(end+1,1) = "ED1"; actions{end+1,1} = @() ED1();
    names(end+1,1) = "ED2"; actions{end+1,1} = @() ED2();
    names(end+1,1) = "ED3"; actions{end+1,1} = @() ED3();
    names(end+1,1) = "ED4"; actions{end+1,1} = @() ED4();
    names(end+1,1) = "ED5"; actions{end+1,1} = @() ED5();
    names(end+1,1) = "ED6"; actions{end+1,1} = @() ED6();
    % ED7 remains the detailed U8 source-workbook view. The final main
    % Figure 5 carries the U8/U9 operational boundary, while Figure 6
    % carries the admissibility/composability synthesis and mechanism test.
    names(end+1,1) = "ED7_U8"; actions{end+1,1} = @() ...
        CMDO_ExtendedDataFigure7_U8(sourceWorkbook, fullfile(cfg.outputRoot,'figures','extended'));
end

status = strings(size(names));
seconds = NaN(size(names));
message = strings(size(names));
for i = 1:numel(names)
    fprintf('[%d/%d] %s\n', i, numel(names), names(i));
    started = tic;
    try
        actions{i}();
        status(i) = "PASS";
    catch ME
        status(i) = "FAIL";
        message(i) = string(getReport(ME, 'extended', 'hyperlinks', 'off'));
    end
    seconds(i) = toc(started);
end

close all;
compatibilityReportPath = fullfile(cfg.outputRoot, 'reports', ...
    'pdf_compatibility_report.csv');
compatibilityReport = cmdo_build_compatibility_pdfs( ...
    fullfile(cfg.outputRoot, 'figures'), compatibilityReportPath);
fprintf('Compatibility PDF report: %s\n', compatibilityReportPath);

visualReview = repmat("PENDING_EXTERNAL_QA", size(names));
results = table(names, status, seconds, message, visualReview, ...
    'VariableNames', {'figure','status','seconds','message','visualReview'});
reportPath = fullfile(cfg.outputRoot, 'reports', 'figure_run_report.csv');
writetable(results, reportPath);
fprintf('Figure report: %s\n', reportPath);

if opt.Strict && any(status == "FAIL")
    failed = strjoin(names(status == "FAIL"), ', ');
    error('CMDO:FigureRunFailed', 'Figure generation failed for: %s. See %s', failed, reportPath);
end
if opt.Strict && any(compatibilityReport.status == "FAIL")
    error('CMDO:CompatibilityPdfFailed', ...
        'One or more compatibility PDFs failed. See %s', compatibilityReportPath);
end
if opt.Strict && height(compatibilityReport) < nnz(status == "PASS")
    error('CMDO:CompatibilityPdfMissing', ...
        ['Only %d compatibility PDFs were produced for %d successful figure ' ...
         'actions. See %s'], height(compatibilityReport), ...
        nnz(status == "PASS"), compatibilityReportPath);
end
end
