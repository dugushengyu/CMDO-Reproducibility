function files = cmdo_safe_save_figure(fig, cfg, stem)
%CMDO_SAFE_SAVE_FIGURE Export editable, vector and raster versions locally.

if ~isfolder(cfg.outputDir)
    mkdir(cfg.outputDir);
end
stem = char(string(stem));
files = struct();
files.fig = fullfile(cfg.outputDir, [stem '.fig']);
files.pdf = fullfile(cfg.outputDir, [stem '.pdf']);
files.png = fullfile(cfg.outputDir, [stem '.png']);
files.tiff = fullfile(cfg.outputDir, [stem '.tiff']);

drawnow;
savefig(fig, files.fig);
try
    exportgraphics(fig, files.pdf, 'ContentType', 'vector');
    exportgraphics(fig, files.png, 'Resolution', 600);
    exportgraphics(fig, files.tiff, 'Resolution', 600);
catch
    print(fig, files.pdf, '-dpdf', '-painters');
    print(fig, files.png, '-dpng', '-r600');
    print(fig, files.tiff, '-dtiff', '-r600');
end
fprintf('Wrote figure files to %s\n', cfg.outputDir);
end
