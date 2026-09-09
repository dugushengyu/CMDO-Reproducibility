function ED3_RobustnessEfficiency_v1(varargin)
% ED3_ROBUSTNESSEFFICIENCY_V1
% Submission-v2 alias for the frozen controlled AUC robustness-efficiency
% renderer previously carried as Figure5_PhaseBoundary.m in the older
% three-layer submission architecture.
%
% This wrapper does not recompute or retune the stress study. It calls the
% tracked frozen renderer and renames only the exported display files so the
% manuscript-facing role is Extended Data Figure 3.

p=inputParser;
addParameter(p,'CSVPath','',@(x)ischar(x)||isstring(x));
addParameter(p,'OutDir','',@(x)ischar(x)||isstring(x));
parse(p,varargin{:}); opt=p.Results;

args={};
if strlength(string(opt.CSVPath))>0
    args=[args {'CSVPath',char(opt.CSVPath)}]; %#ok<AGROW>
end
if strlength(string(opt.OutDir))>0
    args=[args {'OutDir',char(opt.OutDir)}]; %#ok<AGROW>
end

Figure5_PhaseBoundary(args{:});

thisFile=mfilename('fullpath');
if isempty(thisFile), scriptDir=pwd; else, scriptDir=fileparts(thisFile); end
if strlength(string(opt.OutDir))==0
    outDir=fullfile(scriptDir,'output');
else
    outDir=char(opt.OutDir);
end

srcPng=fullfile(outDir,'Figure5_PhaseBoundary_Final_3Panel.png');
srcPdf=fullfile(outDir,'Figure5_PhaseBoundary_Final_3Panel.pdf');
dstPng=fullfile(outDir,'ED3_RobustnessEfficiency_v1.png');
dstPdf=fullfile(outDir,'ED3_RobustnessEfficiency_v1.pdf');

assert(isfile(srcPng),'Missing frozen robustness-efficiency PNG: %s',srcPng);
assert(isfile(srcPdf),'Missing frozen robustness-efficiency PDF: %s',srcPdf);
copyfile(srcPng,dstPng,'f');
copyfile(srcPdf,dstPdf,'f');

fprintf('Extended Data Figure 3 alias written:\n%s\n%s\n',dstPng,dstPdf);
end
