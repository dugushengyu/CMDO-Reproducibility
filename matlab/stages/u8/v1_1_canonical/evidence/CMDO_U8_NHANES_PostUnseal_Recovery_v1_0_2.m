function CMDO_U8_NHANES_PostUnseal_Recovery_v1_0_2(projectRoot)
% CMDO U8 post-unseal deterministic recovery v1.0.2.
%
% This recovery is authorized only for the reviewed U8 run whose original
% v1.0.1 UNSEAL execution stopped at original line 577 after all 2,400
% frozen witness replicates had been computed in memory. The failure was a
% MATLAB container-type mismatch in a cycle-identifier comparison:
%
%   repTable.cycle == targetTable.cycle(i)
%
% where both operands were cell arrays. This recovery makes exactly the
% prespecified mechanical normalization:
%
%   repTable.cycle    = string(repTable.cycle);
%   targetTable.cycle = string(targetTable.cycle);
%   stateTable.cycle  = string(stateTable.cycle);
%
% No model, threshold, cohort, target score, audit budget, seed, replicate,
% formula, gate or decision rule is changed. The recovery refuses to run
% unless the original seal, authorization, code, protocol, frozen assets,
% analysis-start marker, outcome-access record, local outcome files and
% pre-failure reserve-truth table all validate.
%
% The recovery writes an explicit implementation-deviation record and a
% recovery code hash into the final canonical evidence. It is not presented
% as an outcome-blind rerun.

    if nargin < 1 || strlength(string(projectRoot)) == 0
        projectRoot = fullfile(pwd, 'CMDO_U8_NHANES_Workdir_v1_0');
    end

    projectRoot = char(projectRoot);
    C = cmdo_u8_config(projectRoot);
    cmdo_requirements();
    cmdo_make_dirs(C);
    cmdo_recover(C);
end

function C = cmdo_u8_config(projectRoot)
    C.stage = 'U8';
    C.version = 'v1.0';
    C.protocol_name = 'CERTIFIABLE_NATURAL_PREVALENCE_TEMPORAL_RESERVE';
    C.project_root = projectRoot;
    C.raw_dir = fullfile(projectRoot, '00_Raw_Official_NHANES');
    C.seal_dir = fullfile(projectRoot, '01_PreOutcome_Seal');
    C.derived_dir = fullfile(projectRoot, '02_Derived');
    C.results_dir = fullfile(projectRoot, '03_Results');
    C.logs_dir = fullfile(projectRoot, '04_Logs');
    C.canonical_dir = fullfile(projectRoot, '05_Canonical');

    C.recovery_code_path = [mfilename('fullpath') '.m'];
    if ~isfile(C.recovery_code_path)
        C.recovery_code_path = mfilename('fullpath');
    end
    C.package_dir = fileparts(C.recovery_code_path);
    C.original_code_path = fullfile(C.package_dir, ...
        'CMDO_U8_NHANES_Certifiable_Natural_Prevalence_v1_0.m');
    C.code_path = C.original_code_path;
    C.protocol_path = fullfile(C.package_dir, 'StageU8_Protocol_v1_0.md');
    C.recovery_protocol_path = fullfile(C.package_dir, ...
        'StageU8_PostUnseal_Recovery_Protocol_v1_0_2.md');
    C.recovery_authorization_path = fullfile(C.package_dir, ...
        'StageU8_POST_UNSEAL_RECOVERY_AUTHORIZATION_v1_0_2.json');
    C.recovery_diff_path = fullfile(C.package_dir, ...
        'StageU8_Recovery_Analytical_Core_Diff_v1_0_2.patch');

    C.feature_components = {'DEMO', 'BMX', 'BPQ', 'SMQ'};
    C.outcome_component = 'GHB';
    C.outcome_variable = 'LBXGH';
    C.hba1c_threshold = 5.7;
    C.minimum_age = 20;
    C.source_validation_fraction = 0.25;
    C.source_split_seed = 2026080901;
    C.master_seed = 2026080902;
    C.lambda = 1e-3;
    C.folds = 4;
    C.opposite_fold = [3 4 1 2];
    C.delta_family = 0.05;
    C.delta_block = C.delta_family / C.folds;
    C.max_transport_weight = 0.35;
    C.budgets = [128 256 512 1024];
    C.replicates = 200;

    C.cycles = struct( ...
        'id',       {'NHANES_2011_2012','NHANES_2013_2014','NHANES_2015_2016','NHANES_2017_2018','NHANES_2021_2023'}, ...
        'label',    {'2011-2012','2013-2014','2015-2016','2017-2018','2021-2023'}, ...
        'year',     {'2011','2013','2015','2017','2021'}, ...
        'suffix',   {'G','H','I','J','L'}, ...
        'role',     {'SOURCE','DEVELOPMENT','RESERVE','RESERVE','RESERVE'});

    C.reserve_ids = {C.cycles(strcmp({C.cycles.role}, 'RESERVE')).id};
    C.config_path = fullfile(C.seal_dir, 'StageU8_Frozen_Config_v1_0.json');
    C.model_path = fullfile(C.derived_dir, 'StageU8_Frozen_Source_Model_v1_0.mat');
    C.history_path = fullfile(C.derived_dir, 'StageU8_Historical_Performance_Evidence_v1_0.csv');
    C.target_scores_path = fullfile(C.seal_dir, 'StageU8_PreOutcome_Target_Scores_v1_0.csv');
    C.seal_path = fullfile(C.seal_dir, 'StageU8_PreOutcome_Seal_v1_0.json');
    C.authorization_path = fullfile(C.seal_dir, 'StageU8_EXECUTION_AUTHORIZATION_v1_0.json');
    C.analysis_started_path = fullfile(C.results_dir, 'StageU8_ONE_SHOT_ANALYSIS_STARTED_v1_0.json');
    C.outcome_access_path = fullfile(C.results_dir, 'StageU8_Reserve_Outcome_Access_Record_v1_0.json');
    C.truth_path = fullfile(C.results_dir, 'StageU8_Reserve_Truth_v1_0.csv');
    C.recovery_started_path = fullfile(C.results_dir, ...
        'StageU8_POST_UNSEAL_RECOVERY_STARTED_v1_0_2.json');
    C.recovery_deviation_path = fullfile(C.results_dir, ...
        'StageU8_PostUnseal_Implementation_Deviation_v1_0_2.json');
    C.complete_path = fullfile(C.canonical_dir, 'StageU8_Complete_v1_0.json');
end

function cmdo_requirements()
    % `predict` is intentionally not checked here. In this pipeline it is a
    % method of the fitted ClassificationLinear object, not a standalone
    % function that MATLAB must expose on the ordinary function path.
    required = {'xptread', 'fitclinear', 'betainv', 'tiedrank', 'perfcurve'};
    missing = {};
    for i = 1:numel(required)
        if exist(required{i}, 'file') == 0
            missing{end+1} = required{i}; %#ok<AGROW>
        end
    end
    if ~isempty(missing)
        error('CMDO:U8:Toolbox', ['Missing required MATLAB functions: ' strjoin(missing, ', ') '. ' ...
            'Install/enable Statistics and Machine Learning Toolbox before running U8.']);
    end
end

function cmdo_make_dirs(C)
    dirs = {C.project_root, C.raw_dir, C.seal_dir, C.derived_dir, C.results_dir, C.logs_dir, C.canonical_dir};
    for i = 1:numel(dirs)
        if ~isfolder(dirs{i})
            mkdir(dirs{i});
        end
    end
end

function cmdo_prepare(C)
    fprintf('\n================ CMDO U8 PREPARE ================\n');
    fprintf('Project root: %s\n', C.project_root);

    if isfile(C.complete_path)
        error('CMDO:U8:Completed', 'A completed U8 record already exists. Successful rerun is prohibited.');
    end
    if isfile(C.seal_path)
        fprintf('An existing pre-outcome seal was found. It will not be overwritten.\n');
        fprintf('Seal: %s\n', C.seal_path);
        fprintf('Seal SHA-256: %s\n', cmdo_sha256_file(C.seal_path));
        fprintf('Next action: send the seal and this hash for independent review.\n');
        return;
    end

    cmdo_assert_reserve_outcomes_absent(C);
    cmdo_selftest(C, false);

    fprintf('Downloading/validating official feature files for all cycles...\n');
    for i = 1:numel(C.cycles)
        cy = C.cycles(i);
        for j = 1:numel(C.feature_components)
            comp = C.feature_components{j};
            cmdo_download_official(C, cy, comp);
        end
        if any(strcmp(cy.role, {'SOURCE','DEVELOPMENT'}))
            cmdo_download_official(C, cy, C.outcome_component);
        end
    end
    cmdo_assert_reserve_outcomes_absent(C);

    fprintf('Loading source cycle and fitting the frozen source model...\n');
    sourceCycle = C.cycles(strcmp({C.cycles.role}, 'SOURCE'));
    devCycle = C.cycles(strcmp({C.cycles.role}, 'DEVELOPMENT'));
    sourceFeatures = cmdo_load_feature_cycle(C, sourceCycle);
    sourceLabel = cmdo_load_outcome_cycle(C, sourceCycle);
    source = innerjoin(sourceFeatures, sourceLabel, 'Keys', 'SEQN');
    source = source(source.RIDAGEYR >= C.minimum_age & ~isnan(source.LBXGH), :);
    source.Y = double(source.LBXGH >= C.hba1c_threshold);

    [trainMask, valMask] = cmdo_stratified_split(source.Y, C.source_validation_fraction, C.source_split_seed);
    encoder = cmdo_fit_encoder(source(trainMask, :));
    Xtrain = cmdo_encode(source(trainMask, :), encoder);
    Xval = cmdo_encode(source(valMask, :), encoder);
    ytrain = source.Y(trainMask);
    yval = source.Y(valMask);

    rng(C.source_split_seed, 'twister');
    mdl = fitclinear(Xtrain, ytrain, ...
        'Learner', 'logistic', ...
        'Regularization', 'ridge', ...
        'Lambda', C.lambda, ...
        'Solver', 'lbfgs', ...
        'ClassNames', [0; 1]);
    scoreVal = cmdo_positive_score(mdl, Xval);
    threshold = cmdo_youden_threshold(yval, scoreVal);
    sourceValPred = double(scoreVal >= threshold);
    sourceValAccuracy = mean(sourceValPred == yval);
    sourceValAUC = cmdo_auc(scoreVal, yval);

    save(C.model_path, 'mdl', 'encoder', 'threshold', 'sourceValAccuracy', 'sourceValAUC', '-v7.3');

    fprintf('Computing transparent historical performance evidence in 2013-2014...\n');
    devFeatures = cmdo_load_feature_cycle(C, devCycle);
    devLabel = cmdo_load_outcome_cycle(C, devCycle);
    dev = innerjoin(devFeatures, devLabel, 'Keys', 'SEQN');
    dev = dev(dev.RIDAGEYR >= C.minimum_age & ~isnan(dev.LBXGH), :);
    dev.Y = double(dev.LBXGH >= C.hba1c_threshold);
    devScore = cmdo_positive_score(mdl, cmdo_encode(dev, encoder));
    devPred = double(devScore >= threshold);
    historicalAccuracy = mean(devPred == dev.Y);
    historicalAUC = cmdo_auc(devScore, dev.Y);

    history = table( ...
        string(sourceCycle.id), string(devCycle.id), height(source), height(dev), ...
        mean(source.Y), mean(dev.Y), sourceValAccuracy, sourceValAUC, ...
        historicalAccuracy, historicalAUC, threshold, ...
        'VariableNames', {'SOURCE_CYCLE','HISTORICAL_CYCLE','SOURCE_N','HISTORICAL_N', ...
        'SOURCE_PREVALENCE','HISTORICAL_PREVALENCE','SOURCE_VALIDATION_ACCURACY', ...
        'SOURCE_VALIDATION_AUC','HISTORICAL_ACCURACY','HISTORICAL_AUC','FROZEN_THRESHOLD'});
    writetable(history, C.history_path);

    fprintf('Generating reserve scores without accessing reserve outcomes...\n');
    targetParts = cell(numel(C.reserve_ids), 1);
    reserveCycles = C.cycles(strcmp({C.cycles.role}, 'RESERVE'));
    for i = 1:numel(reserveCycles)
        cy = reserveCycles(i);
        T = cmdo_load_feature_cycle(C, cy);
        T = T(T.RIDAGEYR >= C.minimum_age, :);
        X = cmdo_encode(T, encoder);
        score = cmdo_positive_score(mdl, X);
        pred = double(score >= threshold);
        targetParts{i} = table( ...
            repmat(string(cy.id), height(T), 1), T.SEQN, score, pred, ...
            'VariableNames', {'CYCLE','SEQN','SCORE','PREDICTED_CLASS'});
    end
    targetScores = vertcat(targetParts{:});
    targetScores = sortrows(targetScores, {'CYCLE','SEQN'});
    writetable(targetScores, C.target_scores_path);

    frozenConfig = cmdo_config_for_json(C);
    cmdo_write_json(C.config_path, frozenConfig);

    seal = struct();
    seal.stage = C.stage;
    seal.version = C.version;
    seal.protocol_name = C.protocol_name;
    seal.created_at_singapore = cmdo_timestamp();
    seal.decision = 'SEAL_FEATURES_MODEL_SCORES_AND_GATES_KEEP_RESERVE_OUTCOMES_PROHIBITED';
    seal.source_cycle = sourceCycle.id;
    seal.transparent_historical_cycle = devCycle.id;
    seal.reserve_cycles = C.reserve_ids;
    seal.reserve_outcome_status = 'NOT_ACCESSED_OR_DOWNLOADED_BY_THIS_PIPELINE';
    seal.code_sha256 = cmdo_sha256_file(C.code_path);
    seal.protocol_sha256 = cmdo_optional_hash(C.protocol_path);
    seal.config_sha256 = cmdo_sha256_file(C.config_path);
    seal.model_sha256 = cmdo_sha256_file(C.model_path);
    seal.history_sha256 = cmdo_sha256_file(C.history_path);
    seal.target_scores_sha256 = cmdo_sha256_file(C.target_scores_path);
    seal.target_score_rows = height(targetScores);
    seal.historical_accuracy = historicalAccuracy;
    seal.historical_auc = historicalAUC;
    seal.frozen_threshold = threshold;
    seal.budgets = C.budgets;
    seal.replicates = C.replicates;
    seal.delta_block = C.delta_block;
    seal.max_transport_weight = C.max_transport_weight;
    seal.successful_rerun = 'PROHIBITED';
    seal.legacy_stage12_and_locked_assets = 'UNCHANGED_AND_PROHIBITED';
    seal.official_input_manifest = cmdo_official_input_manifest(C, false);
    cmdo_write_json(C.seal_path, seal);

    sealHash = cmdo_sha256_file(C.seal_path);
    note = sprintf(['CMDO U8 PREPARE COMPLETE\n' ...
        'Reserve outcomes remain unopened.\n' ...
        'Pre-outcome seal: %s\n' ...
        'Pre-outcome seal SHA-256: %s\n' ...
        'Code SHA-256: %s\n' ...
        'Target-score SHA-256: %s\n' ...
        'DO NOT RUN UNSEAL before a matching authorization file is issued.\n'], ...
        C.seal_path, sealHash, seal.code_sha256, seal.target_scores_sha256);
    cmdo_write_text(fullfile(C.logs_dir, 'StageU8_PREPARE_COMPLETE_v1_0.txt'), note);

    fprintf('\n%s\n', note);
end

function cmdo_recover(C)
    fprintf('\n========== CMDO U8 POST-UNSEAL RECOVERY v1.0.2 ==========\n');
    fprintf('Project root: %s\n', C.project_root);
    if isfile(C.complete_path)
        error('CMDO:U8:Completed', 'A completed U8 record exists. Successful rerun is prohibited.');
    end
    if isfile(C.recovery_started_path)
        error('CMDO:U8:RecoveryConsumed', ['The recovery-start marker already exists: ' ...
            C.recovery_started_path '. Preserve the full record; a second recovery is prohibited.']);
    end
    forbiddenExistingOutputs = { ...
        fullfile(C.results_dir, 'StageU8_Witness_Replicates_v1_0.csv'), ...
        fullfile(C.results_dir, 'StageU8_Witness_Replicates_v1_0.csv.gz'), ...
        fullfile(C.results_dir, 'StageU8_State_Results_v1_0.csv'), ...
        fullfile(C.results_dir, 'StageU8_Target_Summary_v1_0.csv'), ...
        fullfile(C.results_dir, 'StageU8_Gate_Table_v1_0.csv'), ...
        fullfile(C.results_dir, 'StageU8_Report_v1_0.md'), ...
        fullfile(C.results_dir, 'Figure_U8_Certifiable_Natural_Prevalence_v1_0.png'), ...
        fullfile(C.results_dir, 'Figure_U8_Certifiable_Natural_Prevalence_v1_0.pdf')};
    for i = 1:numel(forbiddenExistingOutputs)
        if isfile(forbiddenExistingOutputs{i})
            error('CMDO:U8:RecoveryWouldOverwrite', ...
                'Recovery refuses to overwrite an existing final-analysis output: %s', ...
                forbiddenExistingOutputs{i});
        end
    end
    requiredPaths = {C.seal_path, C.authorization_path, C.original_code_path, ...
        C.protocol_path, C.recovery_code_path, C.recovery_protocol_path, ...
        C.recovery_authorization_path, C.recovery_diff_path, C.config_path, C.model_path, ...
        C.history_path, C.target_scores_path, C.analysis_started_path, ...
        C.outcome_access_path, C.truth_path};
    for i = 1:numel(requiredPaths)
        if ~isfile(requiredPaths{i})
            error('CMDO:U8:RecoveryMissingFile', ...
                'Required original or recovery file is missing: %s', requiredPaths{i});
        end
    end

    seal = jsondecode(fileread(C.seal_path));
    auth = jsondecode(fileread(C.authorization_path));
    recoveryAuth = jsondecode(fileread(C.recovery_authorization_path));
    analysisStart = jsondecode(fileread(C.analysis_started_path));
    currentSealHash = cmdo_sha256_file(C.seal_path);
    originalCodeHash = cmdo_sha256_file(C.original_code_path);
    recoveryCodeHash = cmdo_sha256_file(C.recovery_code_path);
    recoveryProtocolHash = cmdo_sha256_file(C.recovery_protocol_path);

    cmdo_assert_text_equal(currentSealHash, ...
        '5b6cab9bddd614b610a3acf5e69af0e1c304f14c4f38c55b62808be3835579cf', ...
        'reviewed pre-outcome seal hash');
    cmdo_assert_text_equal(originalCodeHash, ...
        'f963ff0b3d1ec692cc18c1954cee6b748c2b527a83a30b17aa20b9aef49898b2', ...
        'reviewed original v1.0.1 code hash');
    cmdo_assert_text_equal(cmdo_sha256_file(C.protocol_path), ...
        'c1fffe15415b3fcde2e7976e82013f1ec4952c5ecc87c4694808f8758faaeb7b', ...
        'reviewed original protocol hash');
    cmdo_assert_text_equal(cmdo_sha256_file(C.authorization_path), ...
        'ffd8bcb9263d66a5b4edb08e33100a565554a2d7e80c18021c13d49201da90ac', ...
        'reviewed original execution authorization hash');

    cmdo_assert_text_equal(auth.stage, C.stage, 'authorization stage');
    cmdo_assert_text_equal(auth.protocol_version, C.version, 'authorization version');
    cmdo_assert_text_equal(auth.decision, 'AUTHORIZE_ONE_TIME_RESERVE_OUTCOME_ACCESS', 'authorization decision');
    cmdo_assert_text_equal(auth.preoutcome_seal_sha256, currentSealHash, 'authorization seal hash');
    cmdo_assert_text_equal(auth.code_sha256, originalCodeHash, 'authorization code hash');
    cmdo_assert_text_equal(seal.code_sha256, originalCodeHash, 'sealed code hash');
    cmdo_assert_text_equal(seal.protocol_sha256, cmdo_sha256_file(C.protocol_path), 'sealed protocol hash');
    cmdo_assert_text_equal(seal.config_sha256, cmdo_sha256_file(C.config_path), 'frozen config hash');
    cmdo_assert_text_equal(seal.model_sha256, cmdo_sha256_file(C.model_path), 'frozen model hash');
    cmdo_assert_text_equal(seal.history_sha256, cmdo_sha256_file(C.history_path), 'historical evidence hash');
    cmdo_assert_text_equal(seal.target_scores_sha256, cmdo_sha256_file(C.target_scores_path), 'target score hash');
    cmdo_assert_text_equal(seal.target_scores_sha256, ...
        '7a67146ee0b8cc48c925636cad162d7835c293e7ce1bab0b0a8ed868287dce12', ...
        'reviewed target-score hash');

    cmdo_assert_text_equal(recoveryAuth.stage, C.stage, 'recovery authorization stage');
    cmdo_assert_text_equal(recoveryAuth.protocol_version, C.version, 'recovery authorization protocol version');
    cmdo_assert_text_equal(recoveryAuth.recovery_version, 'v1.0.2', 'recovery version');
    cmdo_assert_text_equal(recoveryAuth.decision, ...
        'AUTHORIZE_POST_UNSEAL_DETERMINISTIC_RECOVERY_AFTER_CELL_STRING_TYPE_ERROR', ...
        'recovery authorization decision');
    cmdo_assert_text_equal(recoveryAuth.preoutcome_seal_sha256, currentSealHash, ...
        'recovery authorization seal hash');
    cmdo_assert_text_equal(recoveryAuth.original_code_sha256, originalCodeHash, ...
        'recovery authorization original-code hash');
    cmdo_assert_text_equal(recoveryAuth.original_protocol_sha256, ...
        cmdo_sha256_file(C.protocol_path), 'recovery authorization original-protocol hash');
    cmdo_assert_text_equal(recoveryAuth.original_execution_authorization_sha256, ...
        cmdo_sha256_file(C.authorization_path), ...
        'recovery authorization original-execution-authorization hash');
    cmdo_assert_text_equal(recoveryAuth.recovery_code_sha256, recoveryCodeHash, ...
        'recovery authorization recovery-code hash');
    cmdo_assert_text_equal(recoveryAuth.recovery_protocol_sha256, recoveryProtocolHash, ...
        'recovery authorization recovery-protocol hash');
    cmdo_assert_text_equal(recoveryAuth.analytical_core_diff_sha256, ...
        cmdo_sha256_file(C.recovery_diff_path), ...
        'recovery authorization analytical-core-diff hash');
    cmdo_assert_text_equal(recoveryAuth.permitted_change, ...
        'CYCLE_IDENTIFIER_CONTAINER_NORMALIZATION_CELL_TO_STRING_ONLY', ...
        'permitted recovery change');

    cmdo_assert_text_equal(analysisStart.stage, C.stage, 'analysis-start stage');
    cmdo_assert_text_equal(analysisStart.version, C.version, 'analysis-start version');
    cmdo_assert_text_equal(analysisStart.decision, ...
        'ONE_SHOT_ANALYSIS_BEGINS_RERUN_PROHIBITED', 'analysis-start decision');
    cmdo_assert_text_equal(analysisStart.preoutcome_seal_sha256, currentSealHash, ...
        'analysis-start seal hash');
    cmdo_assert_text_equal(analysisStart.authorization_sha256, ...
        cmdo_sha256_file(C.authorization_path), 'analysis-start authorization hash');
    cmdo_assert_text_equal(analysisStart.code_sha256, originalCodeHash, ...
        'analysis-start original-code hash');
    cmdo_assert_text_equal(analysisStart.reserve_outcome_access_record_sha256, ...
        cmdo_sha256_file(C.outcome_access_path), 'analysis-start outcome-access-record hash');

    fprintf('Original seal, authorization, frozen assets and failed-run marker match.\n');
    reserveCycles = C.cycles(strcmp({C.cycles.role}, 'RESERVE'));
    outcomeAccess = jsondecode(fileread(C.outcome_access_path));
    if numel(outcomeAccess) ~= numel(reserveCycles)
        error('CMDO:U8:RecoveryOutcomeRecord', ...
            'Outcome-access record has %d rows; expected %d.', numel(outcomeAccess), numel(reserveCycles));
    end
    for i = 1:numel(reserveCycles)
        cy = reserveCycles(i);
        rec = outcomeAccess(i);
        localPath = cmdo_local_file(C, cy, C.outcome_component);
        cmdo_assert_text_equal(rec.cycle, cy.id, sprintf('outcome record cycle %d', i));
        cmdo_assert_text_equal(rec.url, cmdo_official_url(cy, C.outcome_component), ...
            sprintf('outcome record URL %d', i));
        cmdo_assert_text_equal(rec.path, localPath, sprintf('outcome record local path %d', i));
        if ~isfile(localPath)
            error('CMDO:U8:RecoveryOutcomeMissing', 'Original accessed outcome is missing: %s', localPath);
        end
        cmdo_assert_text_equal(rec.sha256, cmdo_sha256_file(localPath), ...
            sprintf('outcome file hash %d', i));
    end

    fprintf('All three already-accessed outcome files match their first-access hashes.\n');
    history = readtable(C.history_path, 'TextType', 'string');
    historicalAccuracy = history.HISTORICAL_ACCURACY(1);
    historicalAUC = history.HISTORICAL_AUC(1);
    targetScores = readtable(C.target_scores_path, 'TextType', 'string');
    if height(targetScores) ~= double(seal.target_score_rows)
        error('CMDO:U8:RecoveryTargetRows', ...
            'Target-score row count is %d; sealed count is %d.', ...
            height(targetScores), double(seal.target_score_rows));
    end

    truthParts = cell(numel(reserveCycles), 1);
    for i = 1:numel(reserveCycles)
        cy = reserveCycles(i);
        label = cmdo_load_outcome_cycle(C, cy);
        scored = targetScores(targetScores.CYCLE == string(cy.id), :);
        joined = innerjoin(scored, label, 'Keys', 'SEQN');
        joined = joined(~isnan(joined.LBXGH), :);
        joined.Y = double(joined.LBXGH >= C.hba1c_threshold);
        joined.CORRECT = double(joined.PREDICTED_CLASS == joined.Y);
        truthParts{i} = joined;
    end
    truth = vertcat(truthParts{:});
    truth = sortrows(truth, {'CYCLE','SEQN'});
    preFailureTruth = readtable(C.truth_path, 'TextType', 'string');
    cmdo_assert_truth_equivalent(preFailureTruth, truth);

    deviation = struct();
    deviation.stage = C.stage;
    deviation.protocol_version = C.version;
    deviation.recovery_version = 'v1.0.2';
    deviation.recorded_at_singapore = cmdo_timestamp();
    deviation.classification = 'POST_UNSEAL_IMPLEMENTATION_TYPE_ERROR';
    deviation.original_failure = ['Original v1.0.1 stopped at line 577 after the frozen witness loops, ' ...
        'because repTable.cycle and targetTable.cycle were cell arrays and MATLAB does not support cell == cell.'];
    deviation.permitted_change = 'CYCLE_IDENTIFIER_CONTAINER_NORMALIZATION_CELL_TO_STRING_ONLY';
    deviation.changed_lines = { ...
        'repTable.cycle = string(repTable.cycle);', ...
        'targetTable.cycle = string(targetTable.cycle);', ...
        'stateTable.cycle = string(stateTable.cycle);'};
    deviation.unchanged = ['MODEL_THRESHOLD_COHORT_SCORES_OUTCOMES_BUDGETS_SEEDS_REPLICATES_' ...
        'ESTIMATORS_GATES_DECISION_RULES'];
    deviation.original_witness_count = numel(C.reserve_ids) * numel(C.budgets) * C.replicates;
    deviation.pre_failure_truth_sha256 = cmdo_sha256_file(C.truth_path);
    deviation.original_analysis_started_sha256 = cmdo_sha256_file(C.analysis_started_path);
    deviation.original_outcome_access_record_sha256 = cmdo_sha256_file(C.outcome_access_path);
    deviation.post_failure_default_prepare_invocation = ...
        'CONSOLE_OBSERVED_EXISTING_SEAL_BRANCH_RETURNED_BEFORE_PIPELINE_WRITES';
    deviation.claim = ['Deterministic reconstruction of the frozen analysis after an implementation failure; ' ...
        'not represented as an outcome-blind first execution.'];
    cmdo_write_json(C.recovery_deviation_path, deviation);

    recoveryStart = struct();
    recoveryStart.stage = C.stage;
    recoveryStart.protocol_version = C.version;
    recoveryStart.recovery_version = 'v1.0.2';
    recoveryStart.decision = 'POST_UNSEAL_DETERMINISTIC_RECOVERY_BEGINS_SECOND_RECOVERY_PROHIBITED';
    recoveryStart.started_at_singapore = cmdo_timestamp();
    recoveryStart.preoutcome_seal_sha256 = currentSealHash;
    recoveryStart.original_code_sha256 = originalCodeHash;
    recoveryStart.recovery_code_sha256 = recoveryCodeHash;
    recoveryStart.recovery_protocol_sha256 = recoveryProtocolHash;
    recoveryStart.analytical_core_diff_sha256 = cmdo_sha256_file(C.recovery_diff_path);
    recoveryStart.recovery_authorization_sha256 = cmdo_sha256_file(C.recovery_authorization_path);
    recoveryStart.original_analysis_started_sha256 = cmdo_sha256_file(C.analysis_started_path);
    recoveryStart.outcome_access_record_sha256 = cmdo_sha256_file(C.outcome_access_path);
    recoveryStart.pre_failure_truth_sha256 = cmdo_sha256_file(C.truth_path);
    recoveryStart.implementation_deviation_sha256 = cmdo_sha256_file(C.recovery_deviation_path);
    recoveryStart.frozen_witness_count = numel(C.reserve_ids) * numel(C.budgets) * C.replicates;
    cmdo_write_json(C.recovery_started_path, recoveryStart);

    fprintf('Pre-failure reserve truth matches reconstruction from the accessed official files.\n');
    fprintf('Recovery marker committed; rebuilding the 2,400 frozen witnesses.\n');

    [replicates, states, targets, summary, gates] = cmdo_execute_frozen_evaluation(C, truth, historicalAccuracy, historicalAUC);
    expectedWitnesses = numel(C.reserve_ids) * numel(C.budgets) * C.replicates;
    if height(replicates) ~= expectedWitnesses
        error('CMDO:U8:RecoveryWitnessCount', ...
            'Recovered witness count is %d; frozen count is %d.', ...
            height(replicates), expectedWitnesses);
    end

    replicateCsv = fullfile(C.results_dir, 'StageU8_Witness_Replicates_v1_0.csv');
    statePath = fullfile(C.results_dir, 'StageU8_State_Results_v1_0.csv');
    targetPath = fullfile(C.results_dir, 'StageU8_Target_Summary_v1_0.csv');
    gatePath = fullfile(C.results_dir, 'StageU8_Gate_Table_v1_0.csv');
    writetable(replicates, replicateCsv);
    writetable(states, statePath);
    writetable(targets, targetPath);
    writetable(gates, gatePath);
    gzip(replicateCsv);

    reportPath = fullfile(C.results_dir, 'StageU8_Report_v1_0.md');
    cmdo_write_report(C, reportPath, summary, targets, gates, outcomeAccess);
    cmdo_write_figures(C, states, targets, summary);

    complete = struct();
    complete.stage = C.stage;
    complete.version = C.version;
    complete.completed_at_singapore = cmdo_timestamp();
    complete.preoutcome_seal_sha256 = currentSealHash;
    complete.authorization_sha256 = cmdo_sha256_file(C.authorization_path);
    complete.code_sha256 = originalCodeHash;
    complete.execution_status = 'COMPLETED_BY_AUTHORIZED_POST_UNSEAL_DETERMINISTIC_RECOVERY';
    complete.recovery_version = 'v1.0.2';
    complete.recovery_code_sha256 = recoveryCodeHash;
    complete.recovery_protocol_sha256 = recoveryProtocolHash;
    complete.analytical_core_diff_sha256 = cmdo_sha256_file(C.recovery_diff_path);
    complete.recovery_authorization_sha256 = cmdo_sha256_file(C.recovery_authorization_path);
    complete.original_analysis_started_sha256 = cmdo_sha256_file(C.analysis_started_path);
    complete.recovery_started_sha256 = cmdo_sha256_file(C.recovery_started_path);
    complete.implementation_deviation_sha256 = cmdo_sha256_file(C.recovery_deviation_path);
    complete.decision = summary.decision;
    complete.primary_metric = 'NATURAL_PREVALENCE_FIXED_THRESHOLD_ACCURACY';
    complete.reserve_cycles = C.reserve_ids;
    complete.historical_accuracy = historicalAccuracy;
    complete.historical_auc = historicalAUC;
    complete.summary = summary;
    complete.outcome_access = outcomeAccess;
    complete.claim_boundary = ['Theorem S6 is implemented blockwise. Exact full-direct fallback is algebraic. ' ...
        'Aggregate cross-fitted performance is empirical and is not an unrestricted aggregate no-harm theorem.'];
    complete.recovery_claim_boundary = ['The reserve was opened once by the original v1.0.1 execution. ' ...
        'This record was completed by a disclosed, pre-result recovery that changes only the MATLAB ' ...
        'container type of cycle identifiers from cell to string.'];
    complete.successful_rerun = 'PROHIBITED';
    cmdo_write_json(C.complete_path, complete);

    cmdo_copy_authority_files(C);
    finalCommit = struct();
    finalCommit.stage = C.stage;
    finalCommit.version = C.version;
    finalCommit.completion_record = C.complete_path;
    finalCommit.completion_record_sha256 = cmdo_sha256_file(C.complete_path);
    finalCommit.preoutcome_seal_sha256 = currentSealHash;
    finalCommit.authorization_sha256 = cmdo_sha256_file(C.authorization_path);
    finalCommit.original_code_sha256 = originalCodeHash;
    finalCommit.recovery_code_sha256 = recoveryCodeHash;
    finalCommit.recovery_authorization_sha256 = cmdo_sha256_file(C.recovery_authorization_path);
    finalCommit.implementation_deviation_sha256 = cmdo_sha256_file(C.recovery_deviation_path);
    finalCommit.committed_at_singapore = cmdo_timestamp();
    finalCommitPath = fullfile(C.canonical_dir, 'StageU8_Final_Record_Commit_v1_0.json');
    cmdo_write_json(finalCommitPath, finalCommit);

    manifestPath = fullfile(C.canonical_dir, 'StageU8_Durable_Manifest_v1_0.csv');
    cmdo_write_manifest(C, manifestPath);
    zipPath = cmdo_make_canonical_zip(C);
    zipCommit = struct();
    zipCommit.stage = C.stage;
    zipCommit.version = C.version;
    zipCommit.canonical_zip = zipPath;
    zipCommit.canonical_zip_sha256 = cmdo_sha256_file(zipPath);
    zipCommit.manifest_sha256 = cmdo_sha256_file(manifestPath);
    zipCommit.recovery_version = 'v1.0.2';
    zipCommit.recovery_code_sha256 = recoveryCodeHash;
    zipCommit.committed_at_singapore = cmdo_timestamp();
    cmdo_write_json(fullfile(C.canonical_dir, 'StageU8_Canonical_Zip_Commit_v1_0.json'), zipCommit);

    fprintf('\n================ CMDO U8 COMPLETE ================\n');
    fprintf('Execution status: AUTHORIZED POST-UNSEAL RECOVERY v1.0.2\n');
    fprintf('Decision: %s\n', summary.decision);
    fprintf('Pooled observer/direct MAE: %.9f / %.9f\n', summary.observer_mae, summary.direct_mae);
    fprintf('Relative MAE change: %.4f%%\n', 100 * summary.relative_gain);
    fprintf('Worst state regret: %.9f\n', summary.worst_state_regret);
    fprintf('Improved reserve cycles: %d/%d\n', summary.improved_cycles, summary.reserve_cycle_count);
    fprintf('Mean transport weight: %.6f\n', summary.mean_weight);
    fprintf('Minimum/mean simultaneous coverage: %.4f / %.4f\n', summary.minimum_simultaneous_coverage, summary.mean_simultaneous_coverage);
    fprintf('Covered-event certificate violations: %d\n', summary.covered_event_certificate_violations);
    fprintf('Maximum fallback residual: %.3g\n', summary.maximum_fallback_residual);
    fprintf('Final record SHA-256: %s\n', cmdo_sha256_file(C.complete_path));
end

function [repTable, stateTable, targetTable, summary, gateTable] = cmdo_execute_frozen_evaluation(C, truth, historicalAccuracy, historicalAUC)
    reserveCycles = C.cycles(strcmp({C.cycles.role}, 'RESERVE'));
    repRecords = repmat(cmdo_empty_rep_record(), 0, 1);
    targetRecords = repmat(cmdo_empty_target_record(), 0, 1);

    for ci = 1:numel(reserveCycles)
        cy = reserveCycles(ci);
        T = truth(truth.CYCLE == string(cy.id), :);
        theta = mean(T.CORRECT);
        trueAUC = cmdo_auc(T.SCORE, T.Y);
        targetRec = cmdo_empty_target_record();
        targetRec.cycle = cy.id;
        targetRec.n = height(T);
        targetRec.positive_n = sum(T.Y == 1);
        targetRec.negative_n = sum(T.Y == 0);
        targetRec.prevalence = mean(T.Y);
        targetRec.true_accuracy = theta;
        targetRec.true_auc = trueAUC;
        targetRec.historical_accuracy_bias = historicalAccuracy - theta;
        targetRec.historical_auc_bias = historicalAUC - trueAUC;
        targetRecords(end+1) = targetRec; %#ok<AGROW>

        for bi = 1:numel(C.budgets)
            b = C.budgets(bi);
            if b > height(T)
                error('CMDO:U8:Budget', 'Budget %d exceeds evaluable target N=%d for %s.', b, height(T), cy.id);
            end
            if mod(b, C.folds) ~= 0
                error('CMDO:U8:FoldBudget', 'Every budget must be divisible by %d.', C.folds);
            end

            for ri = 1:C.replicates
                seed = cmdo_derived_seed(C.master_seed, ci, b, ri);
                rng(seed, 'twister');
                idx = randperm(height(T), b);
                W = T(idx, :);
                foldSize = b / C.folds;
                fold = reshape(1:b, foldSize, C.folds);
                blockEstimate = zeros(C.folds, 1);
                blockDirect = zeros(C.folds, 1);
                weights = zeros(C.folds, 1);
                cover = false(C.folds, 1);
                certViolation = false(C.folds, 1);

                for q = 1:C.folds
                    directRows = fold(:, q);
                    auxRows = fold(:, C.opposite_fold(q));
                    zDirect = W.CORRECT(directRows);
                    zAux = W.CORRECT(auxRows);
                    Dq = mean(zDirect);
                    [lo, hi] = cmdo_clopper_pearson(sum(zAux), numel(zAux), C.delta_block);
                    Lq = min(lo * (1 - lo), hi * (1 - hi)) / numel(zDirect);
                    Uq = max((historicalAccuracy - lo)^2, (historicalAccuracy - hi)^2);
                    if Lq <= 0
                        wq = 0;
                    else
                        wq = min(C.max_transport_weight, 2 * Lq / (Lq + Uq + eps));
                    end
                    blockDirect(q) = Dq;
                    weights(q) = wq;
                    blockEstimate(q) = (1 - wq) * Dq + wq * historicalAccuracy;
                    cover(q) = (lo <= theta) && (theta <= hi);

                    Vtrue = theta * (1 - theta) / numel(zDirect);
                    Btrue2 = (historicalAccuracy - theta)^2;
                    oracleCap = 2 * Vtrue / (Vtrue + Btrue2 + eps);
                    certViolation(q) = cover(q) && (wq > oracleCap + 1e-12);
                end

                directAccuracy = mean(W.CORRECT);
                observerAccuracy = mean(blockEstimate);
                fallbackAccuracy = mean(blockDirect);
                directAUC = cmdo_auc(W.SCORE, W.Y);

                rec = cmdo_empty_rep_record();
                rec.cycle = cy.id;
                rec.budget = b;
                rec.replicate = ri;
                rec.seed = seed;
                rec.target_n = height(T);
                rec.audit_positive_n = sum(W.Y == 1);
                rec.audit_negative_n = sum(W.Y == 0);
                rec.true_accuracy = theta;
                rec.direct_accuracy = directAccuracy;
                rec.observer_accuracy = observerAccuracy;
                rec.direct_abs_error = abs(directAccuracy - theta);
                rec.observer_abs_error = abs(observerAccuracy - theta);
                rec.regret = rec.observer_abs_error - rec.direct_abs_error;
                rec.mean_weight = mean(weights);
                rec.max_weight = max(weights);
                rec.fallback_residual = abs(fallbackAccuracy - directAccuracy);
                rec.simultaneous_coverage = all(cover);
                rec.covered_event_certificate_violations = sum(certViolation);
                rec.true_auc = trueAUC;
                rec.direct_auc = directAUC;
                rec.direct_auc_abs_error = abs(directAUC - trueAUC);
                repRecords(end+1) = rec; %#ok<AGROW>
            end
        end
    end

    repTable = struct2table(repRecords);
    targetTable = struct2table(targetRecords);
    % Authorized post-unseal implementation correction v1.0.2.
    % Container normalization only; no analytical value is changed.
    repTable.cycle = string(repTable.cycle);
    targetTable.cycle = string(targetTable.cycle);
    stateRecords = repmat(cmdo_empty_state_record(), 0, 1);
    for ci = 1:numel(reserveCycles)
        cy = reserveCycles(ci);
        for bi = 1:numel(C.budgets)
            b = C.budgets(bi);
            R = repTable(repTable.cycle == string(cy.id) & repTable.budget == b, :);
            s = cmdo_empty_state_record();
            s.cycle = cy.id;
            s.budget = b;
            s.target_n = R.target_n(1);
            s.true_accuracy = R.true_accuracy(1);
            s.direct_mae = mean(R.direct_abs_error);
            s.observer_mae = mean(R.observer_abs_error);
            s.relative_gain = (s.direct_mae - s.observer_mae) / max(s.direct_mae, eps);
            s.regret = s.observer_mae - s.direct_mae;
            s.mean_weight = mean(R.mean_weight);
            s.simultaneous_coverage = mean(R.simultaneous_coverage);
            s.covered_event_certificate_violations = sum(R.covered_event_certificate_violations);
            s.maximum_fallback_residual = max(R.fallback_residual);
            s.mean_audit_positive_n = mean(R.audit_positive_n);
            s.direct_auc_mae = mean(R.direct_auc_abs_error, 'omitnan');
            stateRecords(end+1) = s; %#ok<AGROW>
        end
    end
    stateTable = struct2table(stateRecords);
    stateTable.cycle = string(stateTable.cycle);

    targetTable.direct_mae = zeros(height(targetTable), 1);
    targetTable.observer_mae = zeros(height(targetTable), 1);
    targetTable.relative_gain = zeros(height(targetTable), 1);
    targetTable.mean_weight = zeros(height(targetTable), 1);
    targetTable.improved = false(height(targetTable), 1);
    for i = 1:height(targetTable)
        R = repTable(repTable.cycle == targetTable.cycle(i), :);
        targetTable.direct_mae(i) = mean(R.direct_abs_error);
        targetTable.observer_mae(i) = mean(R.observer_abs_error);
        targetTable.relative_gain(i) = (targetTable.direct_mae(i) - targetTable.observer_mae(i)) / max(targetTable.direct_mae(i), eps);
        targetTable.mean_weight(i) = mean(R.mean_weight);
        targetTable.improved(i) = targetTable.observer_mae(i) <= targetTable.direct_mae(i);
    end

    summary = struct();
    summary.reserve_cycle_count = height(targetTable);
    summary.direct_mae = mean(repTable.direct_abs_error);
    summary.observer_mae = mean(repTable.observer_abs_error);
    summary.relative_gain = (summary.direct_mae - summary.observer_mae) / max(summary.direct_mae, eps);
    summary.worst_state_regret = max(stateTable.regret);
    summary.improved_cycles = sum(targetTable.improved);
    summary.mean_weight = mean(repTable.mean_weight);
    summary.mean_simultaneous_coverage = mean(stateTable.simultaneous_coverage);
    summary.minimum_simultaneous_coverage = min(stateTable.simultaneous_coverage);
    summary.covered_event_certificate_violations = sum(repTable.covered_event_certificate_violations);
    summary.maximum_fallback_residual = max(repTable.fallback_residual);
    budgetMae = zeros(numel(C.budgets), 1);
    for bi = 1:numel(C.budgets)
        budgetMae(bi) = mean(repTable.direct_abs_error(repTable.budget == C.budgets(bi)));
    end
    coeff = polyfit(log(C.budgets(:)), log(max(budgetMae, eps)), 1);
    summary.direct_root_budget_slope = coeff(1);

    gateRecords = repmat(struct('gate',"",'threshold',"",'observed',"",'passed',false), 0, 1);
    gateRecords(end+1) = cmdo_gate('three_temporal_reserve_cycles', '>=3', summary.reserve_cycle_count, summary.reserve_cycle_count >= 3);
    gateRecords(end+1) = cmdo_gate('exact_full_direct_fallback', '<1e-12', summary.maximum_fallback_residual, summary.maximum_fallback_residual < 1e-12);
    gateRecords(end+1) = cmdo_gate('covered_event_certificate_violations', '=0', summary.covered_event_certificate_violations, summary.covered_event_certificate_violations == 0);
    gateRecords(end+1) = cmdo_gate('mean_simultaneous_coverage', '>=0.90', summary.mean_simultaneous_coverage, summary.mean_simultaneous_coverage >= 0.90);
    gateRecords(end+1) = cmdo_gate('minimum_state_simultaneous_coverage', '>=0.85', summary.minimum_simultaneous_coverage, summary.minimum_simultaneous_coverage >= 0.85);
    gateRecords(end+1) = cmdo_gate('pooled_observer_noninferiority', 'observer MAE <= direct MAE', summary.observer_mae - summary.direct_mae, summary.observer_mae <= summary.direct_mae);
    gateRecords(end+1) = cmdo_gate('worst_state_regret', '<=0.005', summary.worst_state_regret, summary.worst_state_regret <= 0.005);
    gateRecords(end+1) = cmdo_gate('improved_reserve_cycles', '>=2/3', summary.improved_cycles, summary.improved_cycles >= 2);
    gateRecords(end+1) = cmdo_gate('nontrivial_borrowing', 'mean weight >0', summary.mean_weight, summary.mean_weight > 0);
    slopePass = summary.direct_root_budget_slope >= -0.70 && summary.direct_root_budget_slope <= -0.30;
    gateRecords(end+1) = cmdo_gate('direct_root_budget_slope', '[-0.70,-0.30]', summary.direct_root_budget_slope, slopePass);
    gateTable = struct2table(gateRecords);

    integrityNames = ["three_temporal_reserve_cycles","exact_full_direct_fallback", ...
        "covered_event_certificate_violations","mean_simultaneous_coverage", ...
        "minimum_state_simultaneous_coverage","direct_root_budget_slope"];
    empiricalNames = ["pooled_observer_noninferiority","worst_state_regret", ...
        "improved_reserve_cycles","nontrivial_borrowing"];
    integrityPass = all(gateTable.passed(ismember(gateTable.gate, integrityNames)));
    empiricalPass = all(gateTable.passed(ismember(gateTable.gate, empiricalNames)));
    if integrityPass && empiricalPass
        summary.decision = 'SUPPORT_CERTIFIABLE_NATURAL_PREVALENCE_OBSERVER';
    elseif integrityPass
        summary.decision = 'PARTIAL_CERTIFICATION_SUPPORTED_EMPIRICAL_EFFICIENCY_NOT_CONFIRMED';
    else
        summary.decision = 'FAIL_U8_INTEGRITY_OR_CERTIFICATION_GATE';
    end
end

function rec = cmdo_empty_rep_record()
    rec = struct('cycle',"",'budget',0,'replicate',0,'seed',0,'target_n',0, ...
        'audit_positive_n',0,'audit_negative_n',0,'true_accuracy',NaN, ...
        'direct_accuracy',NaN,'observer_accuracy',NaN,'direct_abs_error',NaN, ...
        'observer_abs_error',NaN,'regret',NaN,'mean_weight',NaN,'max_weight',NaN, ...
        'fallback_residual',NaN,'simultaneous_coverage',false, ...
        'covered_event_certificate_violations',0,'true_auc',NaN,'direct_auc',NaN, ...
        'direct_auc_abs_error',NaN);
end

function rec = cmdo_empty_state_record()
    rec = struct('cycle',"",'budget',0,'target_n',0,'true_accuracy',NaN, ...
        'direct_mae',NaN,'observer_mae',NaN,'relative_gain',NaN,'regret',NaN, ...
        'mean_weight',NaN,'simultaneous_coverage',NaN, ...
        'covered_event_certificate_violations',0,'maximum_fallback_residual',NaN, ...
        'mean_audit_positive_n',NaN,'direct_auc_mae',NaN);
end

function rec = cmdo_empty_target_record()
    rec = struct('cycle',"",'n',0,'positive_n',0,'negative_n',0,'prevalence',NaN, ...
        'true_accuracy',NaN,'true_auc',NaN,'historical_accuracy_bias',NaN, ...
        'historical_auc_bias',NaN);
end

function rec = cmdo_gate(name, threshold, observed, passed)
    rec = struct('gate',string(name),'threshold',string(threshold), ...
        'observed',string(sprintf('%.12g', observed)),'passed',logical(passed));
end

function cmdo_selftest(C, verbose)
    rng(2026080999, 'twister');
    theta = 0.72;
    T = 0.70;
    b = 512;
    z = double(rand(b, 1) < theta);
    fold = reshape(1:b, b / C.folds, C.folds);
    D = zeros(C.folds, 1);
    E = zeros(C.folds, 1);
    for q = 1:C.folds
        directRows = fold(:, q);
        auxRows = fold(:, C.opposite_fold(q));
        D(q) = mean(z(directRows));
        [lo, hi] = cmdo_clopper_pearson(sum(z(auxRows)), numel(auxRows), C.delta_block);
        L = min(lo * (1 - lo), hi * (1 - hi)) / numel(directRows);
        U = max((T - lo)^2, (T - hi)^2);
        w = min(C.max_transport_weight, 2 * L / (L + U + eps));
        assert(w >= 0 && w <= C.max_transport_weight + eps, 'Weight bounds failed.');
        E(q) = (1 - w) * D(q) + w * T;
    end
    residual = abs(mean(D) - mean(z));
    assert(residual < 1e-12, 'Exact fallback identity failed.');
    assert(all(isfinite(E)), 'Synthetic observer produced non-finite values.');
    if verbose
        fprintf('CMDO U8 SELFTEST PASSED\n');
        fprintf('Exact fallback residual: %.3g\n', residual);
    end
end

function cmdo_assert_reserve_outcomes_absent(C)
    reserveCycles = C.cycles(strcmp({C.cycles.role}, 'RESERVE'));
    found = {};
    for i = 1:numel(reserveCycles)
        p = cmdo_local_file(C, reserveCycles(i), C.outcome_component);
        if isfile(p)
            found{end+1} = p; %#ok<AGROW>
        end
    end
    if ~isempty(found)
        error('CMDO:U8:OutcomeLeak', ['Reserve outcome file(s) exist before authorization: ' strjoin(found, '; ') '. ' ...
            'Do not continue or silently delete them. Start a new clean project root and document the incident.']);
    end
end

function path = cmdo_download_official(C, cy, component)
    path = cmdo_local_file(C, cy, component);
    if isfile(path)
        fprintf('  present: %s\n', path);
        return;
    end
    url = cmdo_official_url(cy, component);
    fprintf('  download: %s\n', url);
    tempPath = [path '.part'];
    try
        opts = weboptions('Timeout', 180);
        websave(tempPath, url, opts);
        if ~isfile(tempPath) || dir(tempPath).bytes == 0
            error('Downloaded file is empty.');
        end
        movefile(tempPath, path, 'f');
    catch ME
        manual = sprintf(['Automatic download failed.\n\nOfficial URL:\n%s\n\nPlace the unchanged file at:\n%s\n\nMATLAB error:\n%s\n'], ...
            url, path, ME.message);
        cmdo_write_text(fullfile(C.logs_dir, ['MANUAL_DOWNLOAD_REQUIRED_' component '_' cy.suffix '.txt']), manual);
        error('CMDO:U8:Download', '%s', manual);
    end
end

function url = cmdo_official_url(cy, component)
    url = sprintf('https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/%s/DataFiles/%s_%s.XPT', ...
        cy.year, upper(component), upper(cy.suffix));
end

function path = cmdo_local_file(C, cy, component)
    cycleDir = fullfile(C.raw_dir, cy.id);
    if ~isfolder(cycleDir)
        mkdir(cycleDir);
    end
    path = fullfile(cycleDir, sprintf('%s_%s.XPT', upper(component), upper(cy.suffix)));
end

function T = cmdo_load_feature_cycle(C, cy)
    demo = cmdo_read_xpt(cmdo_local_file(C, cy, 'DEMO'));
    bmx = cmdo_read_xpt(cmdo_local_file(C, cy, 'BMX'));
    bpq = cmdo_read_xpt(cmdo_local_file(C, cy, 'BPQ'));
    smq = cmdo_read_xpt(cmdo_local_file(C, cy, 'SMQ'));

    demo = cmdo_select(demo, {'SEQN','RIDAGEYR','RIAGENDR','RIDRETH3','DMDEDUC2','INDFMPIR'});
    bmx = cmdo_select(bmx, {'SEQN','BMXBMI','BMXWAIST'});
    bpq = cmdo_select(bpq, {'SEQN','BPQ020','BPQ080'});
    smq = cmdo_select(smq, {'SEQN','SMQ020'});

    T = outerjoin(demo, bmx, 'Keys', 'SEQN', 'MergeKeys', true, 'Type', 'left');
    T = outerjoin(T, bpq, 'Keys', 'SEQN', 'MergeKeys', true, 'Type', 'left');
    T = outerjoin(T, smq, 'Keys', 'SEQN', 'MergeKeys', true, 'Type', 'left');
    T = sortrows(T, 'SEQN');
    T = cmdo_clean_features(T);
end

function T = cmdo_load_outcome_cycle(C, cy)
    T = cmdo_read_xpt(cmdo_local_file(C, cy, C.outcome_component));
    T = cmdo_select(T, {'SEQN', C.outcome_variable});
end

function T = cmdo_read_xpt(path)
    if ~isfile(path)
        error('CMDO:U8:MissingFile', 'Missing required file: %s', path);
    end
    T = xptread(path);
    if ~istable(T)
        T = dataset2table(T); %#ok<DS2T>
    end
    T.Properties.VariableNames = cellstr(upper(string(T.Properties.VariableNames)));
end

function T = cmdo_select(T, names)
    names = cellstr(upper(string(names)));
    missing = setdiff(names, T.Properties.VariableNames);
    if ~isempty(missing)
        error('CMDO:U8:Schema', 'Missing variable(s): %s', strjoin(missing, ', '));
    end
    T = T(:, names);
end

function T = cmdo_clean_features(T)
    T.RIDAGEYR(T.RIDAGEYR < 0) = NaN;
    T.INDFMPIR(T.INDFMPIR < 0) = NaN;
    T.BMXBMI(T.BMXBMI <= 0) = NaN;
    T.BMXWAIST(T.BMXWAIST <= 0) = NaN;
    T.RIAGENDR(~ismember(T.RIAGENDR, [1 2])) = NaN;
    T.RIDRETH3(~ismember(T.RIDRETH3, 1:7)) = NaN;
    T.DMDEDUC2(~ismember(T.DMDEDUC2, 1:5)) = NaN;
    T.BPQ020(~ismember(T.BPQ020, [1 2])) = NaN;
    T.BPQ080(~ismember(T.BPQ080, [1 2])) = NaN;
    T.SMQ020(~ismember(T.SMQ020, [1 2])) = NaN;
end

function encoder = cmdo_fit_encoder(T)
    continuous = {'RIDAGEYR','INDFMPIR','BMXBMI','BMXWAIST'};
    encoder.continuous = continuous;
    encoder.median = zeros(1, numel(continuous));
    encoder.mean = zeros(1, numel(continuous));
    encoder.std = ones(1, numel(continuous));
    for i = 1:numel(continuous)
        x = T.(continuous{i});
        med = median(x, 'omitnan');
        if isnan(med), med = 0; end
        x2 = x;
        x2(isnan(x2)) = med;
        mu = mean(x2);
        sd = std(x2);
        if ~isfinite(sd) || sd < 1e-12, sd = 1; end
        encoder.median(i) = med;
        encoder.mean(i) = mu;
        encoder.std(i) = sd;
    end
    encoder.categorical = {'RIAGENDR','RIDRETH3','DMDEDUC2','BPQ020','BPQ080','SMQ020'};
    encoder.levels = {[1 2], 1:7, 1:5, [1 2], [1 2], [1 2]};
end

function X = cmdo_encode(T, encoder)
    n = height(T);
    blocks = {};
    for i = 1:numel(encoder.continuous)
        x = T.(encoder.continuous{i});
        miss = isnan(x);
        x(miss) = encoder.median(i);
        x = (x - encoder.mean(i)) / encoder.std(i);
        blocks{end+1} = x; %#ok<AGROW>
        blocks{end+1} = double(miss); %#ok<AGROW>
    end
    for i = 1:numel(encoder.categorical)
        x = T.(encoder.categorical{i});
        levels = encoder.levels{i};
        onehot = zeros(n, numel(levels) + 1);
        for j = 1:numel(levels)
            onehot(:, j) = double(x == levels(j));
        end
        onehot(:, end) = double(isnan(x) | ~ismember(x, levels));
        blocks{end+1} = onehot; %#ok<AGROW>
    end
    X = horzcat(blocks{:});
    if any(~isfinite(X), 'all')
        error('CMDO:U8:Encoding', 'Non-finite value remained after frozen encoding.');
    end
end

function [trainMask, valMask] = cmdo_stratified_split(y, valFraction, seed)
    rng(seed, 'twister');
    trainMask = false(size(y));
    valMask = false(size(y));
    classes = unique(y(:))';
    for c = classes
        idx = find(y == c);
        idx = idx(randperm(numel(idx)));
        nVal = max(1, round(valFraction * numel(idx)));
        valMask(idx(1:nVal)) = true;
        trainMask(idx(nVal+1:end)) = true;
    end
    if ~all(trainMask | valMask) || any(trainMask & valMask)
        error('CMDO:U8:Split', 'Stratified split integrity failure.');
    end
end

function score = cmdo_positive_score(mdl, X)
    [~, allScores] = predict(mdl, X);
    classNames = mdl.ClassNames;
    posCol = find(classNames == 1, 1);
    if isempty(posCol)
        error('CMDO:U8:ClassNames', 'Positive class 1 was not found in the frozen model.');
    end
    score = allScores(:, posCol);
end

function threshold = cmdo_youden_threshold(y, score)
    [fpr, tpr, thresholds] = perfcurve(y, score, 1);
    J = tpr - fpr;
    best = find(J == max(J), 1, 'first');
    threshold = thresholds(best);
    if ~isfinite(threshold)
        finiteScores = score(isfinite(score));
        threshold = median(finiteScores);
    end
end

function auc = cmdo_auc(score, y)
    good = isfinite(score) & isfinite(y);
    score = score(good);
    y = y(good);
    nPos = sum(y == 1);
    nNeg = sum(y == 0);
    if nPos == 0 || nNeg == 0
        auc = NaN;
        return;
    end
    r = tiedrank(score);
    auc = (sum(r(y == 1)) - nPos * (nPos + 1) / 2) / (nPos * nNeg);
end

function [lo, hi] = cmdo_clopper_pearson(x, n, delta)
    alpha = delta;
    if x == 0
        lo = 0;
    else
        lo = betainv(alpha / 2, x, n - x + 1);
    end
    if x == n
        hi = 1;
    else
        hi = betainv(1 - alpha / 2, x + 1, n - x);
    end
end

function seed = cmdo_derived_seed(masterSeed, cycleIndex, budget, replicate)
    modulus = 2147483647;
    seed = mod(double(masterSeed) + 10000019 * cycleIndex + 1009 * budget + 37 * replicate, modulus - 1) + 1;
end

function J = cmdo_config_for_json(C)
    J = struct();
    J.stage = C.stage;
    J.version = C.version;
    J.protocol_name = C.protocol_name;
    J.created_at_singapore = cmdo_timestamp();
    J.primary_metric = 'NATURAL_PREVALENCE_FIXED_THRESHOLD_ACCURACY';
    J.supportive_metric = 'NATURAL_PREVALENCE_DIRECT_AUC';
    J.outcome = sprintf('LBXGH >= %.1f percent', C.hba1c_threshold);
    J.minimum_age = C.minimum_age;
    J.cycles = C.cycles;
    J.feature_components = C.feature_components;
    J.outcome_component = C.outcome_component;
    J.budgets = C.budgets;
    J.replicates = C.replicates;
    J.folds = C.folds;
    J.opposite_fold = C.opposite_fold;
    J.delta_family = C.delta_family;
    J.delta_block = C.delta_block;
    J.max_transport_weight = C.max_transport_weight;
    J.master_seed = C.master_seed;
    J.source_split_seed = C.source_split_seed;
    J.source_validation_fraction = C.source_validation_fraction;
    J.ridge_lambda = C.lambda;
    J.aggregate_claim = 'EMPIRICAL_ONLY_BLOCKWISE_THEOREM_DOES_NOT_IMPLY_UNRESTRICTED_AGGREGATE_NO_HARM';
    J.legacy_stage12 = 'PROHIBITED_UNCHANGED';
end

function M = cmdo_official_input_manifest(C, includeReserveOutcomes)
    records = repmat(struct('cycle','','role','','component','','url','','local_path','','sha256','','size_bytes',0), 0, 1);
    for i = 1:numel(C.cycles)
        cy = C.cycles(i);
        comps = C.feature_components;
        if any(strcmp(cy.role, {'SOURCE','DEVELOPMENT'})) || (includeReserveOutcomes && strcmp(cy.role, 'RESERVE'))
            comps{end+1} = C.outcome_component;
        end
        for j = 1:numel(comps)
            comp = comps{j};
            p = cmdo_local_file(C, cy, comp);
            rec = struct();
            rec.cycle = cy.id;
            rec.role = cy.role;
            rec.component = comp;
            rec.url = cmdo_official_url(cy, comp);
            rec.local_path = p;
            if isfile(p)
                rec.sha256 = cmdo_sha256_file(p);
                d = dir(p);
                rec.size_bytes = d.bytes;
            else
                rec.sha256 = 'ABSENT';
                rec.size_bytes = 0;
            end
            records(end+1) = rec; %#ok<AGROW>
        end
    end
    M = records;
end

function cmdo_write_figures(C, states, targets, summary)
    f = figure('Color', 'w', 'Position', [100 100 1250 820]);
    tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    cycles = unique(states.cycle, 'stable');
    colors = lines(numel(cycles));
    hold on;
    for i = 1:numel(cycles)
        S = states(states.cycle == cycles(i), :);
        plot(S.budget, S.direct_mae, '--o', 'Color', colors(i,:), 'LineWidth', 1.3);
        plot(S.budget, S.observer_mae, '-s', 'Color', colors(i,:), 'LineWidth', 1.8);
    end
    set(gca, 'XScale', 'log', 'YScale', 'log'); grid on;
    xlabel('Screened cases'); ylabel('MAE'); title('Natural-prevalence accuracy estimation');

    nexttile;
    hold on;
    for i = 1:numel(cycles)
        S = states(states.cycle == cycles(i), :);
        plot(S.budget, 100*S.relative_gain, '-o', 'Color', colors(i,:), 'LineWidth', 1.8, 'DisplayName', char(cycles(i)));
    end
    yline(0, 'k:'); set(gca, 'XScale', 'log'); grid on;
    xlabel('Screened cases'); ylabel('Relative MAE reduction (%)'); title('Empirical aggregate efficiency');
    legend('Location', 'best', 'Interpreter', 'none');

    nexttile;
    bar(categorical(targets.cycle), [targets.direct_mae targets.observer_mae]);
    ylabel('MAE across budgets'); title('Cycle-level reserve result'); grid on;
    legend({'Direct','Certifiable observer'}, 'Location', 'best');

    nexttile;
    yyaxis left;
    plot(states.budget, states.simultaneous_coverage, 'o', 'MarkerFaceColor', [0.15 0.45 0.75]);
    ylabel('Simultaneous coverage'); ylim([0 1.02]);
    yyaxis right;
    plot(states.budget, states.mean_weight, 's', 'MarkerFaceColor', [0.85 0.35 0.15]);
    ylabel('Mean transport weight');
    set(gca, 'XScale', 'log'); grid on; xlabel('Screened cases');
    title(sprintf('%s; pooled gain %.2f%%', summary.decision, 100*summary.relative_gain), 'Interpreter', 'none');

    pngPath = fullfile(C.results_dir, 'Figure_U8_Certifiable_Natural_Prevalence_v1_0.png');
    pdfPath = fullfile(C.results_dir, 'Figure_U8_Certifiable_Natural_Prevalence_v1_0.pdf');
    exportgraphics(f, pngPath, 'Resolution', 300);
    exportgraphics(f, pdfPath, 'ContentType', 'vector');
    close(f);
end

function cmdo_write_report(C, path, summary, targets, gates, outcomeAccess)
    lines = strings(0,1);
    lines(end+1) = "# Stage U8 — Certifiable natural-prevalence temporal reserve";
    lines(end+1) = "";
    lines(end+1) = "## Decision";
    lines(end+1) = "";
    lines(end+1) = "`" + string(summary.decision) + "`";
    lines(end+1) = "";
    lines(end+1) = "Execution status: **authorized post-unseal deterministic recovery v1.0.2**.";
    lines(end+1) = "The original v1.0.1 run opened the reserve once and then stopped on a MATLAB cell/string comparison error. The recovery changes only cycle-identifier container types; it does not change any analytical value or frozen decision rule.";
    lines(end+1) = "";
    lines(end+1) = sprintf('- Reserve cycles: %d', summary.reserve_cycle_count);
    lines(end+1) = sprintf('- Observer MAE: %.9f', summary.observer_mae);
    lines(end+1) = sprintf('- Same-screened-budget direct MAE: %.9f', summary.direct_mae);
    lines(end+1) = sprintf('- Relative MAE reduction: %.4f%%', 100*summary.relative_gain);
    lines(end+1) = sprintf('- Worst cycle-budget regret: %.9f', summary.worst_state_regret);
    lines(end+1) = sprintf('- Improved cycles: %d/%d', summary.improved_cycles, summary.reserve_cycle_count);
    lines(end+1) = sprintf('- Mean transport weight: %.6f', summary.mean_weight);
    lines(end+1) = sprintf('- Mean/minimum simultaneous coverage: %.4f / %.4f', summary.mean_simultaneous_coverage, summary.minimum_simultaneous_coverage);
    lines(end+1) = sprintf('- Covered-event certificate violations: %d', summary.covered_event_certificate_violations);
    lines(end+1) = sprintf('- Maximum fallback residual: %.3g', summary.maximum_fallback_residual);
    lines(end+1) = sprintf('- Direct root-budget slope: %.4f', summary.direct_root_budget_slope);
    lines(end+1) = "";
    lines(end+1) = "## Reserve targets";
    lines(end+1) = "";
    lines(end+1) = "| Cycle | N | Positive | Prevalence | True accuracy | True AUC | Direct MAE | Observer MAE | Gain | Mean weight |";
    lines(end+1) = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|";
    for i = 1:height(targets)
        lines(end+1) = sprintf('| %s | %d | %d | %.4f | %.6f | %.6f | %.6f | %.6f | %.2f%% | %.4f |', ...
            targets.cycle(i), targets.n(i), targets.positive_n(i), targets.prevalence(i), ...
            targets.true_accuracy(i), targets.true_auc(i), targets.direct_mae(i), ...
            targets.observer_mae(i), 100*targets.relative_gain(i), targets.mean_weight(i));
    end
    lines(end+1) = "";
    lines(end+1) = "## Frozen gates";
    lines(end+1) = "";
    lines(end+1) = "| Gate | Threshold | Observed | Passed |";
    lines(end+1) = "|---|---|---:|:---:|";
    for i = 1:height(gates)
        lines(end+1) = sprintf('| %s | %s | %s | %s |', gates.gate(i), gates.threshold(i), gates.observed(i), string(gates.passed(i)));
    end
    lines(end+1) = "";
    lines(end+1) = "## Outcome access";
    lines(end+1) = "";
    for i = 1:numel(outcomeAccess)
        lines(end+1) = sprintf('- %s: %s; SHA-256 `%s`', outcomeAccess(i).cycle, outcomeAccess(i).accessed_at_singapore, outcomeAccess(i).sha256);
    end
    lines(end+1) = "";
    lines(end+1) = "## Claim boundary";
    lines(end+1) = "";
    lines(end+1) = "The variance-disjoint confidence event and Eq. (S115) apply to each protected direct fold. The four-fold aggregate has exact full-direct fallback when all weights are zero, but its realised same-budget performance is an empirical reserve result rather than an unrestricted aggregate-risk theorem. The audit samples cases without class conditioning; every budget is therefore a screened-case and verified-outcome budget under the retrospective emulation.";
    lines(end+1) = "";
    lines(end+1) = "Legacy DDO-2 Stage 12 and its locked assets were not accessed, repurposed or modified by U8.";
    cmdo_write_text(path, strjoin(lines, newline));
end

function cmdo_write_manifest(C, path)
    roots = {C.seal_dir, C.derived_dir, C.results_dir, C.canonical_dir};
    records = repmat(struct('relative_path',"",'size_bytes',0,'sha256',""), 0, 1);
    for r = 1:numel(roots)
        files = dir(fullfile(roots{r}, '**', '*'));
        files = files(~[files.isdir]);
        for i = 1:numel(files)
            p = fullfile(files(i).folder, files(i).name);
            if strcmp(p, path) || endsWith(p, 'StageU8_Canonical_Records_v1_0.zip') || ...
                    endsWith(p, 'StageU8_Canonical_Zip_Commit_v1_0.json')
                continue;
            end
            rel = erase(p, [C.project_root filesep]);
            rec = struct('relative_path',string(rel),'size_bytes',files(i).bytes,'sha256',string(cmdo_sha256_file(p)));
            records(end+1) = rec; %#ok<AGROW>
        end
    end
    writetable(struct2table(records), path);
end

function cmdo_copy_authority_files(C)
    codeCopy = fullfile(C.canonical_dir, 'CMDO_U8_NHANES_Certifiable_Natural_Prevalence_v1_0.m');
    copyfile(C.code_path, codeCopy, 'f');
    if isfile(C.protocol_path)
        copyfile(C.protocol_path, fullfile(C.canonical_dir, 'StageU8_Protocol_v1_0.md'), 'f');
    end
    copyfile(C.recovery_code_path, fullfile(C.canonical_dir, ...
        'CMDO_U8_NHANES_PostUnseal_Recovery_v1_0_2.m'), 'f');
    copyfile(C.recovery_protocol_path, fullfile(C.canonical_dir, ...
        'StageU8_PostUnseal_Recovery_Protocol_v1_0_2.md'), 'f');
    copyfile(C.recovery_authorization_path, fullfile(C.canonical_dir, ...
        'StageU8_POST_UNSEAL_RECOVERY_AUTHORIZATION_v1_0_2.json'), 'f');
    copyfile(C.recovery_diff_path, fullfile(C.canonical_dir, ...
        'StageU8_Recovery_Analytical_Core_Diff_v1_0_2.patch'), 'f');
end

function zipPath = cmdo_make_canonical_zip(C)
    zipPath = fullfile(C.canonical_dir, 'StageU8_Canonical_Records_v1_0.zip');
    roots = {C.seal_dir, C.derived_dir, C.results_dir, C.canonical_dir};
    relativeFiles = {};
    for r = 1:numel(roots)
        entries = dir(fullfile(roots{r}, '**', '*'));
        entries = entries(~[entries.isdir]);
        for i = 1:numel(entries)
            p = fullfile(entries(i).folder, entries(i).name);
            if strcmp(p, zipPath) || endsWith(p, 'StageU8_Canonical_Zip_Commit_v1_0.json')
                continue;
            end
            relativeFiles{end+1} = erase(p, [C.project_root filesep]); %#ok<AGROW>
        end
    end
    zip(zipPath, relativeFiles, C.project_root);
end

function h = cmdo_optional_hash(path)
    if isfile(path)
        h = cmdo_sha256_file(path);
    else
        h = 'ABSENT';
    end
end

function h = cmdo_sha256_file(path)
    fid = fopen(path, 'rb');
    if fid < 0
        error('CMDO:U8:HashOpen', 'Cannot open file for hashing: %s', path);
    end
    cleaner = onCleanup(@() fclose(fid)); %#ok<NASGU>
    md = java.security.MessageDigest.getInstance('SHA-256');
    while true
        bytes = fread(fid, 1024 * 1024, '*uint8');
        if isempty(bytes), break; end
        md.update(typecast(bytes(:), 'int8'));
    end
    digest = typecast(md.digest(), 'uint8');
    h = lower(reshape(dec2hex(digest, 2).', 1, []));
end

function cmdo_write_json(path, value)
    try
        txt = jsonencode(value, 'PrettyPrint', true);
    catch
        txt = jsonencode(value);
    end
    cmdo_write_text(path, txt);
end

function cmdo_write_text(path, txt)
    fid = fopen(path, 'w', 'n', 'UTF-8');
    if fid < 0
        error('CMDO:U8:Write', 'Cannot open file for writing: %s', path);
    end
    cleaner = onCleanup(@() fclose(fid)); %#ok<NASGU>
    fprintf(fid, '%s', char(txt));
end

function stamp = cmdo_timestamp()
    stamp = char(datetime('now', 'TimeZone', 'Asia/Singapore', 'Format', 'yyyy-MM-dd HH:mm:ss Z'));
end

function cmdo_assert_truth_equivalent(preFailureTruth, reconstructedTruth)
    if height(preFailureTruth) ~= height(reconstructedTruth)
        error('CMDO:U8:RecoveryTruthRows', ...
            'Pre-failure truth has %d rows; reconstruction has %d.', ...
            height(preFailureTruth), height(reconstructedTruth));
    end
    if ~isequal(preFailureTruth.Properties.VariableNames, ...
            reconstructedTruth.Properties.VariableNames)
        error('CMDO:U8:RecoveryTruthSchema', ...
            'Pre-failure truth variable names or order differ from reconstruction.');
    end
    preFailureTruth = sortrows(preFailureTruth, {'CYCLE','SEQN'});
    reconstructedTruth = sortrows(reconstructedTruth, {'CYCLE','SEQN'});
    names = preFailureTruth.Properties.VariableNames;
    for i = 1:numel(names)
        name = names{i};
        a = preFailureTruth.(name);
        b = reconstructedTruth.(name);
        if (isnumeric(a) || islogical(a)) && (isnumeric(b) || islogical(b))
            a = double(a);
            b = double(b);
            sameNaN = isnan(a) & isnan(b);
            finiteValues = [abs(a(isfinite(a))); abs(b(isfinite(b)))];
            if isempty(finiteValues)
                scale = 1;
            else
                scale = max(1, max(finiteValues));
            end
            equalValue = abs(a - b) <= 1e-12 * scale;
            if any(~(sameNaN | equalValue), 'all')
                error('CMDO:U8:RecoveryTruthValue', ...
                    'Pre-failure truth differs from reconstruction in variable %s.', name);
            end
        else
            if ~isequaln(string(a), string(b))
                error('CMDO:U8:RecoveryTruthValue', ...
                    'Pre-failure truth differs from reconstruction in variable %s.', name);
            end
        end
    end
end

function cmdo_assert_text_equal(actual, expected, label)
    if ~strcmp(char(string(actual)), char(string(expected)))
        error('CMDO:U8:HashMismatch', '%s mismatch. Expected %s, observed %s.', label, string(expected), string(actual));
    end
end
