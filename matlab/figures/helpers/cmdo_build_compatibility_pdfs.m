function report = cmdo_build_compatibility_pdfs(figureRoot, reportPath)
%CMDO_BUILD_COMPATIBILITY_PDFS Create renderer-safe raster PDF companions.
%
% MATLAB's vector PDF exporter can display expanded character spacing in
% some Poppler-based journal and archive previewers even though Adobe and
% Ghostscript render the same file normally.  Keep the editable vector PDF
% and create a 600-dpi image-only *_compat.pdf companion from each accepted
% PNG.  The companion contains no live fonts, so its appearance is stable
% across PDF engines.  The PNG image stream is embedded directly instead of
% being routed through an invisible MATLAB axes.  Exporting the axes can
% tighten the canvas by a few pixels and clip marks or annotations that sit
% close to the right or lower figure boundary.

if nargin < 1 || strlength(string(figureRoot)) == 0
    error('CMDO:MissingFigureRoot', 'A figure root is required.');
end
if nargin < 2
    reportPath = '';
end

figureRoot = char(string(figureRoot));
folders = {fullfile(figureRoot, 'main'), fullfile(figureRoot, 'extended')};
pngFiles = [];
for k = 1:numel(folders)
    if isfolder(folders{k})
        nextFiles = dir(fullfile(folders{k}, '*.png'));
        if isempty(pngFiles)
            pngFiles = nextFiles;
        else
            pngFiles = [pngFiles; nextFiles]; %#ok<AGROW>
        end
    end
end

sourcePng = strings(numel(pngFiles),1);
compatibilityPdf = strings(numel(pngFiles),1);
status = strings(numel(pngFiles),1);
message = strings(numel(pngFiles),1);

for k = 1:numel(pngFiles)
    sourcePng(k) = string(fullfile(pngFiles(k).folder, pngFiles(k).name));
    [~, stem] = fileparts(pngFiles(k).name);
    compatibilityPdf(k) = string(fullfile( ...
        pngFiles(k).folder, [stem '_compat.pdf']));

    try
        cmdo_png_to_pdf(sourcePng(k), compatibilityPdf(k), 600);
        status(k) = "PASS";
    catch ME
        status(k) = "FAIL";
        message(k) = string(getReport(ME, 'basic', 'hyperlinks', 'off'));
    end
end

report = table(sourcePng, compatibilityPdf, status, message, ...
    'VariableNames', {'sourcePng','compatibilityPdf','status','message'});

if strlength(string(reportPath)) > 0
    reportFolder = fileparts(char(string(reportPath)));
    if ~isfolder(reportFolder)
        mkdir(reportFolder);
    end
    writetable(report, reportPath);
end
end
