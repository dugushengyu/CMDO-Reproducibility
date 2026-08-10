function report = REBUILD_COMPATIBILITY_PDFS()
%REBUILD_COMPATIBILITY_PDFS Rebuild renderer-safe PDFs from existing PNGs.
%
% This recovery entry point does not redraw figures, run tests, re-execute
% U8 or access U9 outcomes.  It only replaces *_compat.pdf companions and
% refreshes outputs/reports/pdf_compatibility_report.csv.

cfg = SETUP_CMDO();
figureRoot = fullfile(cfg.outputRoot, 'figures');
reportPath = fullfile(cfg.outputRoot, 'reports', ...
    'pdf_compatibility_report.csv');
report = cmdo_build_compatibility_pdfs(figureRoot, reportPath);

passed = report.status == "PASS";
fprintf('\nCompatibility PDFs rebuilt from existing PNGs.\n');
fprintf('  Passed: %d\n', nnz(passed));
fprintf('  Failed: %d\n', nnz(~passed));
fprintf('  Report: %s\n\n', reportPath);

if height(report) < 13
    error('CMDO:CompatibilityPdfMissing', ...
        'Only %d compatibility PDFs were produced; expected at least 13.', ...
        height(report));
end
if any(~passed)
    error('CMDO:CompatibilityPdfFailed', ...
        'One or more compatibility PDFs failed. See %s', reportPath);
end
end
