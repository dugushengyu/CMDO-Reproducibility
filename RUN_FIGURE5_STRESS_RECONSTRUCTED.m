function csvPath = RUN_FIGURE5_STRESS_RECONSTRUCTED(varargin)
% Generate the reconstructed dense-Lambda stress source and return its CSV.
p=inputParser; addParameter(p,'OutDir','',@(x)ischar(x)||isstring(x)); parse(p,varargin{:}); opt=p.Results;
cfg=SETUP_CMDO(); repoRoot=cfg.repoRoot;
if strlength(string(opt.OutDir))==0
    outDir=fullfile(repoRoot,'source_data','figure5_stress_reconstructed');
else
    outDir=char(opt.OutDir);
end
if ~isfolder(outDir), mkdir(outDir); end
py=fullfile(repoRoot,'scripts','CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py');
if ~isfile(py), error('CMDO:StressGeneratorMissing','Missing generator: %s',py); end
[code,~]=system('py -3 --version');
if code==0, pycmd='py -3'; else, [code,~]=system('python --version'); if code~=0, error('CMDO:PythonMissing','Python 3 not found.'); end; pycmd='python'; end
cmd=sprintf('%s "%s" --outdir "%s"',pycmd,py,outDir);
fprintf('\nGenerating reconstructed dense-Lambda stress test...\n');
[code,txt]=system(cmd,'-echo');
if code~=0, error('CMDO:StressGenerationFailed','Stress generator failed (exit %d).\n%s',code,txt); end
csvPath=fullfile(outDir,'CMDO_SystemStress_AUC_StateSummary_v1_1.csv');
if ~isfile(csvPath), error('CMDO:StressOutputMissing','Expected CSV not created: %s',csvPath); end
T=readtable(csvPath); need={'true_auc','budget','lambda_nominal','bias_sign','method','method_label','mae','direct_mae','mean_excess_mae','gain_percent'};
for i=1:numel(need), if ~ismember(need{i},T.Properties.VariableNames), error('CMDO:StressColumnMissing','Missing column: %s',need{i}); end; end
fprintf('Stress source ready:\n  %s\n',csvPath);
end
