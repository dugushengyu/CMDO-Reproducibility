function Figure6
%FIGURE6 Final U8 natural-prevalence confirmation + U9 external boundary.
here = fileparts(mfilename('fullpath'));
repo = fileparts(fileparts(fileparts(here)));
sourceDir = fullfile(repo,'source_data','figure6_u8_u9');
outDir = fullfile(repo,'outputs','figures','main');
CMDO_Figure6_U8_U9_OperationalBoundary(sourceDir,outDir);
end
