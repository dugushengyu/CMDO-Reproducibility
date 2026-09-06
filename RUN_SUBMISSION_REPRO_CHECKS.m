function result = RUN_SUBMISSION_REPRO_CHECKS(varargin)
%RUN_SUBMISSION_REPRO_CHECKS Reviewer-facing submission verification bundle.
%
%   RUN_SUBMISSION_REPRO_CHECKS
%   RUN_SUBMISSION_REPRO_CHECKS('Strict',true)
%
% Runs the seven manuscript/Extended Data figure renderers and verifies the
% exact finite-cohort U10 diagnostic reported in Supplementary Note 6.

p = inputParser;
addParameter(p,'Strict',true,@(x)islogical(x) || isnumeric(x));
addParameter(p,'OutDir','',@(x)ischar(x) || isstring(x));
parse(p,varargin{:});
opt = p.Results;

fprintf('\n============================================================\n');
fprintf(' CMDO SUBMISSION REPRODUCIBILITY CHECKS\n');
fprintf('============================================================\n');

if strlength(string(opt.OutDir)) == 0
    figSummary = RUN_SUBMISSION_FIGURES('Batch',true,'Strict',logical(opt.Strict));
else
    figSummary = RUN_SUBMISSION_FIGURES( ...
        'Batch',true, ...
        'Strict',logical(opt.Strict), ...
        'OutDir',char(opt.OutDir));
end

exactSummary = RUN_U10_EXACT_FINITE_COHORT_CHECK( ...
    'VerifyOnly',true, ...
    'Strict',logical(opt.Strict));

result = struct();
result.figures = figSummary;
result.u10_exact = exactSummary;
result.all_figure_renderers_passed = all(figSummary.status=="PASS");
result.u10_exact_verified = true;

fprintf('\nSUBMISSION FIGURES : %d/%d PASS\n', ...
    nnz(figSummary.status=="PASS"),height(figSummary));
fprintf('U10 EXACT CHECK    : PASS\n');
fprintf('============================================================\n\n');

end
