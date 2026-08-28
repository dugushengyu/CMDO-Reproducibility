function results = RUN_SUBMISSION_FIGURES(varargin)
%RUN_SUBMISSION_FIGURES Render the final manuscript figure architecture.
%
% Final architecture:
%   Figure 1 : conceptual overview
%   Figure 2 : ordered theory
%   Figure 3 : IDENTIFY
%   Figure 4 : REUSE
%   Figure 5 : PRESERVE
%   ED1      : developmental falsification
%   ED2      : coupling-pathway diagnostics
%
% This runner is submission-specific and does not delete or reinterpret
% historical figure renderers retained elsewhere in the repository.

p = inputParser;
addParameter(p,'OutputDir','',@(x)ischar(x) || isstring(x));
addParameter(p,'Strict',true,@(x)islogical(x) && isscalar(x));
parse(p,varargin{:});
opt = p.Results;

cfg = SETUP_CMDO();
repoRoot = cfg.repoRoot;

if strlength(string(opt.OutputDir)) == 0
    outputDir = fullfile(repoRoot,'outputs','submission_figures');
else
    outputDir = char(opt.OutputDir);
end

if ~isfolder(outputDir)
    mkdir(outputDir);
end

fprintf('\n============================================================\n');
fprintf(' CMDO FINAL SUBMISSION FIGURE RUNNER\n');
fprintf(' Figure 1-5 + Extended Data Figure 1-2\n');
fprintf(' IDENTIFY -> REUSE -> PRESERVE\n');
fprintf('============================================================\n');
fprintf('Repository : %s\n',repoRoot);
fprintf('Output     : %s\n',outputDir);

names = [ ...
    "Figure1"; ...
    "Figure2"; ...
    "Figure3_IDENTIFY"; ...
    "Figure4_REUSE"; ...
    "Figure5_PRESERVE"; ...
    "ExtendedData1"; ...
    "ExtendedData2" ...
    ];

actions = { ...
    @() Figure1_IDA_RealData_Final(outputDir); ...
    @() Figure2_IDA_v4(outputDir); ...
    @() Figure3_FrozenReuse_v8(outputDir,repoRoot); ...
    @() Figure4_OperationalBoundary_v3(outputDir,repoRoot); ...
    @() Figure5_InformationClosure_Composability_v8(outputDir,repoRoot); ...
    @() ED1_OutcomeFreeBoundary_v9(outputDir,repoRoot); ...
    @() ED2_IntegrityControls_v2(outputDir,repoRoot) ...
    };

status = strings(size(names));
seconds = nan(size(names));
message = strings(size(names));

for i = 1:numel(names)

    fprintf('\n[%d/%d] %s\n',i,numel(names),names(i));

    t0 = tic;

    try
        actions{i}();
        status(i) = "PASS";
    catch ME
        status(i) = "FAIL";
        message(i) = string(getReport(ME,'extended','hyperlinks','off'));
    end

    seconds(i) = toc(t0);

end

close all;

expected = { ...
    'Figure1_Evidential_Order_Final_Worlds.png'; ...
    'Figure1_Evidential_Order_Final_Worlds.pdf'; ...
    'Figure2_IDA_EvidentialOrder.fig'; ...
    'Figure2_IDA_EvidentialOrder.png'; ...
    'Figure2_IDA_EvidentialOrder.pdf'; ...
    'Figure3_FrozenReuse_v8.fig'; ...
    'Figure3_FrozenReuse_v8.png'; ...
    'Figure3_FrozenReuse_v8.pdf'; ...
    'Figure4_OperationalBoundary_v3.fig'; ...
    'Figure4_OperationalBoundary_v3.png'; ...
    'Figure4_OperationalBoundary_v3.pdf'; ...
    'Figure5_InformationClosure_Composability_v8.fig'; ...
    'Figure5_InformationClosure_Composability_v8.png'; ...
    'Figure5_InformationClosure_Composability_v8.pdf'; ...
    'ED1_OutcomeFreeBoundary_v9.fig'; ...
    'ED1_OutcomeFreeBoundary_v9.png'; ...
    'ED1_OutcomeFreeBoundary_v9.pdf'; ...
    'ED2_IntegrityControls_v2.fig'; ...
    'ED2_IntegrityControls_v2.png'; ...
    'ED2_IntegrityControls_v2.pdf' ...
    };

missing = strings(0,1);

for i = 1:numel(expected)

    pth = fullfile(outputDir,expected{i});

    if ~isfile(pth)
        missing(end+1,1) = string(expected{i}); %#ok<AGROW>
        continue
    end

    d = dir(pth);

    if isempty(d) || d.bytes <= 0
        missing(end+1,1) = string(expected{i}); %#ok<AGROW>
    end

end

results = table( ...
    names,status,seconds,message, ...
    'VariableNames',{'figure','status','seconds','message'});

reportPath = fullfile(outputDir,'FINAL_SUBMISSION_FIGURE_RUN_REPORT.csv');
writetable(results,reportPath);

fprintf('\n============================================================\n');
fprintf(' FINAL SUBMISSION FIGURE SUMMARY\n');
fprintf('============================================================\n');
disp(results(:,{'figure','status','seconds'}));

fprintf('Report: %s\n',reportPath);

if ~isempty(missing)

    fprintf('\nMissing or empty required outputs:\n');

    for i = 1:numel(missing)
        fprintf('  %s\n',missing(i));
    end

end

if opt.Strict && any(status ~= "PASS")
    failed = strjoin(names(status ~= "PASS"),', ');
    error('CMDO:SubmissionFigureFailure', ...
        'Final submission figure generation failed: %s',failed);
end

if opt.Strict && ~isempty(missing)
    error('CMDO:SubmissionFigureOutputMissing', ...
        'One or more final submission figure files are missing or empty.');
end

fprintf('\n============================================================\n');
fprintf(' CMDO FINAL SUBMISSION FIGURES: PASS\n');
fprintf('============================================================\n');

end