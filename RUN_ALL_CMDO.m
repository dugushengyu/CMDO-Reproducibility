function output = RUN_ALL_CMDO(varargin)
%RUN_ALL_CMDO Stable top-level MATLAB entry point for the CMDO repository.
%
% RUN_ALL_CMDO                         safe local acceptance run:
%                                      check, tests and all current figures
% RUN_ALL_CMDO('Mode','check')         environment and integrity check only
% RUN_ALL_CMDO('Mode','figures')       render all current figures
% RUN_ALL_CMDO('Mode','tests')         run repository unit tests
% RUN_ALL_CMDO('Mode','finalize')      validate and summarize an existing
%                                      completed safe run without rerendering
% RUN_ALL_CMDO('Mode','u9-selftest')   safe outcome-free U9 self-test
% RUN_ALL_CMDO('Mode','u8-rerun', ...
%   'ConfirmAuthorizedU8Rerun',true)   explicit disclosed U8 v1.1 rerun
%
% The default safe run never re-executes U8 and never accesses U9 outcomes.
% U9 ADAPT/PREPARE/UNSEAL remain stage-local, ordered, review-gated actions.

p = inputParser;
addParameter(p, 'Mode', 'safe-all');
addParameter(p, 'ConfirmAuthorizedU8Rerun', false, @(x) islogical(x) && isscalar(x));
addParameter(p, 'RawDataRoot', '');
addParameter(p, 'ProjectRoot', '');
parse(p, varargin{:});
opt = p.Results;

cfg = SETUP_CMDO();
mode = lower(string(opt.Mode));

switch mode
    case {"safe-all","safe","all"}
        environment = RUN_ENVIRONMENT_CHECK();
        archiveReady = [environment.canonicalArchives.verified];
        if ~environment.readyForFigures
            missing = string({environment.canonicalArchives(~archiveReady).archive});
            if isempty(missing)
                missingText = "none (inspect the environment report)";
            else
                missingText = strjoin(missing, ', ');
            end
            error('CMDO:NotReadyForSafeAll', [ ...
                'The safe local run cannot continue. Missing or invalid canonical archives: %s. ' ...
                'Expected folder: %s'], missingText, ...
                environment.paths.canonicalRecordDir);
        end
        tests = RUN_CMDO_TESTS();
        [figures, pdfCompatibility] = RUN_ALL_FIGURES();
        acceptance = struct( ...
            'checkedAt', environment.checkedAt, ...
            'environmentReady', environment.readyForFigures, ...
            'testCount', numel(tests), ...
            'testFailures', nnz([tests.Failed]), ...
            'figureCount', height(figures), ...
            'figureGenerationFailures', nnz(figures.status == "FAIL"), ...
            'compatibilityPdfCount', height(pdfCompatibility), ...
            'compatibilityPdfFailures', nnz(pdfCompatibility.status == "FAIL"), ...
            'visualReview', 'PENDING_EXTERNAL_QA', ...
            'u8Reexecuted', false, ...
            'u9Unsealed', false);
        acceptancePath = fullfile(cfg.outputRoot, 'reports', ...
            'local_acceptance_summary.json');
        cmdo.write_json(acceptancePath, acceptance);
        fprintf('Acceptance summary: %s\n', acceptancePath);
        output = struct('mode','SAFE_ALL','environment',environment, ...
            'tests',tests,'figures',figures, ...
            'pdfCompatibility',pdfCompatibility,'acceptance',acceptance);

    case {"check","environment"}
        output = RUN_ENVIRONMENT_CHECK();

    case "figures"
        output = RUN_ALL_FIGURES();

    case "tests"
        output = RUN_CMDO_TESTS();

    case {"finalize-existing","finalize"}
        output = FINALIZE_EXISTING_CMDO_RUN();

    case "u9-selftest"
        stageDir = cmdo.stage_path('U9_V1_0');
        addpath(stageDir);
        cleanup = onCleanup(@() rmpath(stageDir));
        workRoot = fullfile(cfg.outputRoot, 'u9', 'CMDO_U9_eICU_Workdir_v1_0');
        CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0( ...
            'SELFTEST', '', workRoot);
        output = struct('stage','U9','mode','SELFTEST','workRoot',workRoot);

    case "u8-rerun"
        if ~opt.ConfirmAuthorizedU8Rerun
            error('CMDO:ConfirmationRequired', [ ...
                'U8 v1.1 writes reconstruction markers and must be an explicitly ' ...
                'authorized rerun. Reissue with ConfirmAuthorizedU8Rerun=true.']);
        end
        stageDir = cmdo.stage_path('U8_V1_1');
        addpath(stageDir);
        cleanup = onCleanup(@() rmpath(stageDir));
        if strlength(string(opt.ProjectRoot)) > 0
            workRoot = char(string(opt.ProjectRoot));
        else
            workRoot = fullfile(cfg.outputRoot, 'u8', ...
                'CMDO_U8_NHANES_PostUnseal_Workdir_v1_1_0');
        end
        CMDO_U8_NHANES_PostUnseal_Complete_Rerun_v1_1_0(workRoot);
        output = struct('stage','U8','mode','AUTHORIZED_V1_1_RERUN', ...
            'projectRoot',workRoot);

    otherwise
        error('CMDO:UnknownMode', 'Unknown RUN_ALL_CMDO mode: %s', mode);
end
end
