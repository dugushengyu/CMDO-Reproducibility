function CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0(mode, rawDataRoot, projectRoot)
% CMDO U9: sealed multicentre decision-observability reserve in eICU-CRD.
%
% Modes
% -----
% SELFTEST : outcome-free mathematical and implementation checks.
% ADAPT    : split official eICU tables into an outcome-free analytical
%            roster, development outcomes, and a sealed reserve-outcome
%            vault. This step prints no reserve outcome statistics.
% PREPARE  : fit/freeze all source and historical quantities, target scores,
%            comparators, telemetry pairs, criteria, seeds and gates without
%            reading the reserve-outcome vault.
% UNSEAL   : after independent authorization, verify every frozen hash,
%            commit a one-shot marker, open the reserve-outcome vault once,
%            and write the complete canonical record.
%
% Recommended calls are provided in RUN_SELFTEST.m, RUN_DATA_ADAPTER.m,
% RUN_PREPARE.m and RUN_UNSEAL.m. Do not call UNSEAL before an authorization
% file matching the pre-outcome seal has been issued.

    if nargin < 1 || strlength(string(mode)) == 0
        mode = "SELFTEST";
    end
    if nargin < 2 || strlength(string(rawDataRoot)) == 0
        rawDataRoot = getenv('CMDO_EICU_ROOT');
        if strlength(string(rawDataRoot)) == 0
            rawDataRoot = fullfile(pwd, 'eicu-crd-2.0');
        end
    end
    if nargin < 3 || strlength(string(projectRoot)) == 0
        projectRoot = fullfile(pwd, 'CMDO_U9_eICU_Workdir_v1_0');
    end

    mode = upper(string(mode));
    C = cmdo_u9_config(char(rawDataRoot), char(projectRoot));
    cmdo_u9_requirements(mode);
    cmdo_u9_make_dirs(C);

    switch mode
        case "SELFTEST"
            cmdo_u9_selftest(C, true);
        case "ADAPT"
            cmdo_u9_adapt(C);
        case "PREPARE"
            cmdo_u9_prepare(C);
        case "UNSEAL"
            cmdo_u9_unseal(C);
        otherwise
            error('CMDO:U9:Mode', 'Unknown mode "%s". Use SELFTEST, ADAPT, PREPARE or UNSEAL.', mode);
    end
end

function cmdo_u9_prepare(C)
    fprintf('\n================ CMDO U9 PREPARE ================\n');
    fprintf('Project root: %s\n', C.project_root);

    if isfile(C.complete_path)
        error('CMDO:U9:Completed', 'A completed U9 record already exists. Successful rerun is prohibited.');
    end
    if isfile(C.analysis_started_path)
        error('CMDO:U9:OneShotConsumed', 'The one-shot analysis marker exists. PREPARE cannot run.');
    end
    if isfile(C.seal_path)
        fprintf('An existing pre-outcome seal was found and will not be overwritten.\n');
        fprintf('Seal: %s\n', C.seal_path);
        fprintf('Seal SHA-256: %s\n', cmdo_u9_sha256_file(C.seal_path));
        fprintf('Next action: obtain independent authorization. Do not run UNSEAL yet.\n');
        return;
    end
    cmdo_u9_assert_adapter_ready(C);
    cmdo_u9_selftest(C, false);

    adapterSeal = jsondecode(fileread(C.adapter_seal_path));
    vaultHashBefore = cmdo_u9_sha256_file(C.reserve_vault_path);
    cmdo_u9_assert_text_equal(adapterSeal.reserve_outcome_vault_sha256, vaultHashBefore, 'adapter-sealed reserve vault hash');
    cmdo_u9_assert_text_equal(adapterSeal.outcome_free_roster_sha256, cmdo_u9_sha256_file(C.roster_path), 'adapter roster hash');
    cmdo_u9_assert_text_equal(adapterSeal.development_outcomes_sha256, cmdo_u9_sha256_file(C.development_outcome_path), 'development outcome hash');
    cmdo_u9_assert_text_equal(adapterSeal.hospital_roles_sha256, cmdo_u9_sha256_file(C.roles_path), 'hospital role hash');

    % PREPARE reads only the outcome-free roster and non-reserve outcomes.
    % The reserve vault is hashed as bytes but never passed to readtable.
    roster = readtable(C.roster_path, 'TextType', 'string');
    roles = readtable(C.roles_path, 'TextType', 'string');
    devOutcome = readtable(C.development_outcome_path, 'TextType', 'string');
    dev = innerjoin(roster(roster.ROLE ~= "RESERVE", :), devOutcome, 'Keys', {'CASE_ID','HOSPITAL','ROLE'});
    dev = dev(isfinite(dev.Y), :);
    if isempty(dev)
        error('CMDO:U9:DevelopmentOutcome', 'No finite development outcomes were available after the adapter split.');
    end

    source = dev(dev.ROLE == "SOURCE", :);
    history = dev(dev.ROLE == "HISTORY", :);
    calibration = dev(dev.ROLE == "CALIBRATION", :);
    cmdo_u9_require_nonempty(source, 'SOURCE');
    cmdo_u9_require_nonempty(history, 'HISTORY');
    cmdo_u9_require_nonempty(calibration, 'CALIBRATION');

    threshold = cmdo_u9_youden_threshold(source.Y, source.SCORE);
    roster.PREDICTED_CLASS = double(roster.SCORE >= threshold);
    roster.CONFIDENCE = cmdo_u9_operating_confidence(roster.SCORE, threshold);
    dev.PREDICTED_CLASS = double(dev.SCORE >= threshold);
    dev.CONFIDENCE = cmdo_u9_operating_confidence(dev.SCORE, threshold);
    dev.CORRECT = double(dev.PREDICTED_CLASS == dev.Y);
    % Refresh role tables after derived correctness variables are added;
    % MATLAB table slices are value copies, not live views.
    source = dev(dev.ROLE == "SOURCE", :);
    history = dev(dev.ROLE == "HISTORY", :);
    calibration = dev(dev.ROLE == "CALIBRATION", :);

    sourceMask = dev.ROLE == "SOURCE";
    historyMask = dev.ROLE == "HISTORY";
    sourceAccuracy = mean(dev.CORRECT(sourceMask));
    sourceAUC = cmdo_u9_auc(dev.SCORE(sourceMask), dev.Y(sourceMask));
    historicalAccuracy = mean(dev.CORRECT(historyMask));
    historicalAUC = cmdo_u9_auc(dev.SCORE(historyMask), dev.Y(historyMask));

    historyHospitals = unique(dev.HOSPITAL(historyMask));
    historyRecords = repmat(cmdo_u9_empty_history_record(), 0, 1);
    for i = 1:numel(historyHospitals)
        H = dev(historyMask & dev.HOSPITAL == historyHospitals(i), :);
        rec = cmdo_u9_empty_history_record();
        rec.hospital = historyHospitals(i);
        rec.n = height(H);
        rec.prevalence = mean(H.Y);
        rec.accuracy = mean(H.CORRECT);
        rec.auc = cmdo_u9_auc(H.SCORE, H.Y);
        historyRecords(end+1) = rec; %#ok<AGROW>
    end
    historicalByHospital = struct2table(historyRecords);
    primaryFloor = median(historicalByHospital.accuracy);
    lenientFloor = quantile(historicalByHospital.accuracy, 0.25);
    strictFloor = quantile(historicalByHospital.accuracy, 0.75);

    % Frozen correctness proxy used only by the PPI++-style comparator.
    proxyTrainMask = dev.ROLE == "SOURCE" | dev.ROLE == "HISTORY";
    XproxyTrain = cmdo_u9_proxy_features(dev(proxyTrainMask, :), threshold);
    proxyMean = mean(XproxyTrain, 1);
    proxyStd = std(XproxyTrain, 0, 1);
    proxyStd(proxyStd < 1e-10 | ~isfinite(proxyStd)) = 1;
    XproxyTrain = (XproxyTrain - proxyMean) ./ proxyStd;
    proxyMdl = fitglm(XproxyTrain, dev.CORRECT(proxyTrainMask), 'linear', ...
        'Distribution', 'binomial', 'Link', 'logit');
    XproxyAll = (cmdo_u9_proxy_features(roster, threshold) - proxyMean) ./ proxyStd;
    roster.PROXY_CORRECTNESS = min(1, max(0, predict(proxyMdl, XproxyAll)));

    % ATC-style thresholded confidence is fitted in source hospitals only.
    atcThreshold = cmdo_u9_atc_threshold(dev.CONFIDENCE(sourceMask), sourceAccuracy);
    telemetry = cmdo_u9_hospital_telemetry(roster, roles, threshold, atcThreshold);
    pairs = cmdo_u9_select_telemetry_pairs(telemetry(telemetry.ROLE == "RESERVE", :), C.telemetry_pair_count);

    % Static historical borrowing is tuned only on calibration hospitals.
    [staticWeight, calibrationDiagnostics] = cmdo_u9_tune_static_weight(C, calibration, historicalAccuracy);
    writetable(historicalByHospital, C.history_path);
    writetable(calibrationDiagnostics, C.calibration_path);
    writetable(telemetry, C.telemetry_path);
    writetable(pairs, C.telemetry_pairs_path);

    targetScores = roster(roster.ROLE == "RESERVE", ...
        {'CASE_ID','HOSPITAL','SCORE','PREDICTED_CLASS','CONFIDENCE','PROXY_CORRECTNESS'});
    targetScores = sortrows(targetScores, {'HOSPITAL','CASE_ID'});
    writetable(targetScores, C.target_scores_path);

    save(C.model_path, 'threshold', 'sourceAccuracy', 'sourceAUC', ...
        'historicalAccuracy', 'historicalAUC', 'historicalByHospital', ...
        'primaryFloor', 'lenientFloor', 'strictFloor', 'staticWeight', ...
        'atcThreshold', 'proxyMdl', 'proxyMean', 'proxyStd', '-v7.3');

    frozenConfig = cmdo_u9_config_for_json(C);
    frozenConfig.frozen_operating_threshold = threshold;
    frozenConfig.source_accuracy = sourceAccuracy;
    frozenConfig.source_auc = sourceAUC;
    frozenConfig.historical_accuracy = historicalAccuracy;
    frozenConfig.historical_auc = historicalAUC;
    frozenConfig.primary_historical_median_floor = primaryFloor;
    frozenConfig.lenient_historical_quartile_floor = lenientFloor;
    frozenConfig.strict_historical_quartile_floor = strictFloor;
    frozenConfig.static_weight = staticWeight;
    frozenConfig.atc_confidence_threshold = atcThreshold;
    cmdo_u9_write_json(C.config_path, frozenConfig);

    seal = struct();
    seal.stage = C.stage;
    seal.version = C.version;
    seal.protocol_name = C.protocol_name;
    seal.created_at_singapore = cmdo_u9_timestamp();
    seal.decision = 'SEAL_MULTICENTRE_ROSTER_SCORES_CRITERIA_COMPARATORS_GATES_AND_TELEMETRY_PAIRS';
    seal.data_source = 'eICU Collaborative Research Database v2.0';
    seal.reserve_outcome_status = 'VAULT_HASHED_BUT_NOT_READ_BY_PREPARE';
    seal.adapter_seal_sha256 = cmdo_u9_sha256_file(C.adapter_seal_path);
    seal.reserve_outcome_vault_sha256 = vaultHashBefore;
    seal.code_sha256 = cmdo_u9_sha256_file(C.code_path);
    seal.protocol_sha256 = cmdo_u9_optional_hash(C.protocol_path);
    seal.config_sha256 = cmdo_u9_sha256_file(C.config_path);
    seal.model_sha256 = cmdo_u9_sha256_file(C.model_path);
    seal.roles_sha256 = cmdo_u9_sha256_file(C.roles_path);
    seal.roster_sha256 = cmdo_u9_sha256_file(C.roster_path);
    seal.development_outcomes_sha256 = cmdo_u9_sha256_file(C.development_outcome_path);
    seal.history_sha256 = cmdo_u9_sha256_file(C.history_path);
    seal.calibration_sha256 = cmdo_u9_sha256_file(C.calibration_path);
    seal.telemetry_sha256 = cmdo_u9_sha256_file(C.telemetry_path);
    seal.telemetry_pairs_sha256 = cmdo_u9_sha256_file(C.telemetry_pairs_path);
    seal.target_scores_sha256 = cmdo_u9_sha256_file(C.target_scores_path);
    seal.target_score_rows = height(targetScores);
    seal.reserve_hospitals = cellstr(sort(unique(targetScores.HOSPITAL)));
    seal.reserve_hospital_count = numel(seal.reserve_hospitals);
    seal.frozen_operating_threshold = threshold;
    seal.historical_accuracy = historicalAccuracy;
    seal.primary_floor = primaryFloor;
    seal.static_weight = staticWeight;
    seal.atc_threshold = atcThreshold;
    seal.budgets = C.budgets;
    seal.replicates = C.replicates;
    seal.master_seed = C.master_seed;
    seal.delta_block = C.delta_block;
    seal.max_transport_weight = C.max_transport_weight;
    seal.successful_rerun = 'PROHIBITED';
    seal.restricted_row_level_data = 'EXCLUDED_FROM_CANONICAL_SHAREABLE_ZIP';
    cmdo_u9_write_json(C.seal_path, seal);

    % A filled review record is written for convenience, but its decision
    % remains explicitly non-authorizing until independently changed.
    review = struct();
    review.stage = C.stage;
    review.protocol_version = C.version;
    review.decision = 'DO_NOT_AUTHORIZE_WITHOUT_INDEPENDENT_REVIEW';
    review.preoutcome_seal_sha256 = cmdo_u9_sha256_file(C.seal_path);
    review.code_sha256 = seal.code_sha256;
    review.reserve_outcome_vault_sha256 = vaultHashBefore;
    review.issued_by = 'PENDING';
    review.issued_at_singapore = 'PENDING';
    review.note = 'Send the seal and this review record for authorization. Do not self-authorize by changing only the decision string.';
    cmdo_u9_write_json(fullfile(C.seal_dir, 'StageU9_AUTHORIZATION_REVIEW_RECORD_v1_0.json'), review);

    vaultHashAfter = cmdo_u9_sha256_file(C.reserve_vault_path);
    cmdo_u9_assert_text_equal(vaultHashAfter, vaultHashBefore, 'reserve vault unchanged during PREPARE');
    note = sprintf(['CMDO U9 PREPARE COMPLETE\n' ...
        'Reserve-outcome vault was not read by PREPARE and its hash is unchanged.\n' ...
        'Pre-outcome seal: %s\n' ...
        'Pre-outcome seal SHA-256: %s\n' ...
        'Code SHA-256: %s\n' ...
        'Target-score SHA-256: %s\n' ...
        'DO NOT RUN UNSEAL until a matching authorization file is issued.\n'], ...
        C.seal_path, cmdo_u9_sha256_file(C.seal_path), seal.code_sha256, seal.target_scores_sha256);
    cmdo_u9_write_text(fullfile(C.logs_dir, 'StageU9_PREPARE_COMPLETE_v1_0.txt'), note);
    fprintf('\n%s\n', note);
end

function cmdo_u9_unseal(C)
    fprintf('\n================ CMDO U9 UNSEAL ================\n');
    if isfile(C.complete_path)
        error('CMDO:U9:Completed', 'A completed U9 record exists. Successful rerun is prohibited.');
    end
    if isfile(C.analysis_started_path)
        error('CMDO:U9:OneShotConsumed', ['The one-shot analysis marker already exists: ' ...
            C.analysis_started_path '. Preserve the full record; analysis rerun is prohibited.']);
    end
    if ~isfile(C.seal_path)
        error('CMDO:U9:NoSeal', 'PREPARE must complete before UNSEAL.');
    end
    if ~isfile(C.authorization_path)
        error('CMDO:U9:NoAuthorization', ['Missing ' C.authorization_path '. ' ...
            'Send the pre-outcome seal for independent review; do not self-authorize.']);
    end

    seal = jsondecode(fileread(C.seal_path));
    auth = jsondecode(fileread(C.authorization_path));
    currentSealHash = cmdo_u9_sha256_file(C.seal_path);
    currentCodeHash = cmdo_u9_sha256_file(C.code_path);
    currentVaultHash = cmdo_u9_sha256_file(C.reserve_vault_path);

    cmdo_u9_assert_text_equal(auth.stage, C.stage, 'authorization stage');
    cmdo_u9_assert_text_equal(auth.protocol_version, C.version, 'authorization version');
    cmdo_u9_assert_text_equal(auth.decision, 'AUTHORIZE_ONE_TIME_RESERVE_OUTCOME_ACCESS', 'authorization decision');
    cmdo_u9_assert_text_equal(auth.preoutcome_seal_sha256, currentSealHash, 'authorization seal hash');
    cmdo_u9_assert_text_equal(auth.code_sha256, currentCodeHash, 'authorization code hash');
    cmdo_u9_assert_text_equal(auth.reserve_outcome_vault_sha256, currentVaultHash, 'authorization vault hash');
    cmdo_u9_assert_text_equal(seal.code_sha256, currentCodeHash, 'sealed code hash');
    cmdo_u9_assert_text_equal(seal.protocol_sha256, cmdo_u9_optional_hash(C.protocol_path), 'sealed protocol hash');
    cmdo_u9_assert_text_equal(seal.adapter_seal_sha256, cmdo_u9_sha256_file(C.adapter_seal_path), 'adapter-seal hash');
    cmdo_u9_assert_text_equal(seal.config_sha256, cmdo_u9_sha256_file(C.config_path), 'frozen config hash');
    cmdo_u9_assert_text_equal(seal.model_sha256, cmdo_u9_sha256_file(C.model_path), 'frozen model hash');
    cmdo_u9_assert_text_equal(seal.roles_sha256, cmdo_u9_sha256_file(C.roles_path), 'role hash');
    cmdo_u9_assert_text_equal(seal.roster_sha256, cmdo_u9_sha256_file(C.roster_path), 'roster hash');
    cmdo_u9_assert_text_equal(seal.development_outcomes_sha256, cmdo_u9_sha256_file(C.development_outcome_path), 'development-outcome hash');
    cmdo_u9_assert_text_equal(seal.history_sha256, cmdo_u9_sha256_file(C.history_path), 'history hash');
    cmdo_u9_assert_text_equal(seal.calibration_sha256, cmdo_u9_sha256_file(C.calibration_path), 'calibration hash');
    cmdo_u9_assert_text_equal(seal.telemetry_sha256, cmdo_u9_sha256_file(C.telemetry_path), 'telemetry hash');
    cmdo_u9_assert_text_equal(seal.telemetry_pairs_sha256, cmdo_u9_sha256_file(C.telemetry_pairs_path), 'telemetry-pair hash');
    cmdo_u9_assert_text_equal(seal.target_scores_sha256, cmdo_u9_sha256_file(C.target_scores_path), 'target-score hash');
    cmdo_u9_assert_text_equal(seal.reserve_outcome_vault_sha256, currentVaultHash, 'sealed reserve-vault hash');

    fprintf('Authorization and every frozen hash match. Committing the one-shot marker now.\n');
    analysisStart = struct();
    analysisStart.stage = C.stage;
    analysisStart.version = C.version;
    analysisStart.decision = 'ONE_SHOT_MULTICENTRE_ANALYSIS_BEGINS_RERUN_PROHIBITED';
    analysisStart.started_at_singapore = cmdo_u9_timestamp();
    analysisStart.preoutcome_seal_sha256 = currentSealHash;
    analysisStart.authorization_sha256 = cmdo_u9_sha256_file(C.authorization_path);
    analysisStart.code_sha256 = currentCodeHash;
    analysisStart.reserve_outcome_vault_sha256 = currentVaultHash;
    cmdo_u9_write_json(C.analysis_started_path, analysisStart);

    % The first reserve-outcome read occurs only after the permanent marker.
    scores = readtable(C.target_scores_path, 'TextType', 'string');
    reserveOutcome = readtable(C.reserve_vault_path, 'TextType', 'string');
    truth = innerjoin(scores, reserveOutcome(:, {'CASE_ID','HOSPITAL','Y'}), 'Keys', {'CASE_ID','HOSPITAL'});
    truth = truth(isfinite(truth.Y), :);
    truth.CORRECT = double(truth.PREDICTED_CLASS == truth.Y);
    truth = sortrows(truth, {'HOSPITAL','CASE_ID'});

    S = load(C.model_path);
    telemetry = readtable(C.telemetry_path, 'TextType', 'string');
    telemetryPairs = readtable(C.telemetry_pairs_path, 'TextType', 'string');
    [replicates, states, hospitals, methods, decisions, pairResults, summary, gates] = ...
        cmdo_u9_execute_frozen_evaluation(C, truth, telemetry, telemetryPairs, S);

    replicatePath = fullfile(C.results_dir, 'StageU9_Witness_Replicates_v1_0.csv');
    statePath = fullfile(C.results_dir, 'StageU9_Budget_State_Results_v1_0.csv');
    hospitalPath = fullfile(C.results_dir, 'StageU9_Hospital_Summary_v1_0.csv');
    methodPath = fullfile(C.results_dir, 'StageU9_Method_Summary_v1_0.csv');
    decisionPath = fullfile(C.results_dir, 'StageU9_Decision_Summary_v1_0.csv');
    pairPath = fullfile(C.results_dir, 'StageU9_Telemetry_Pair_Results_v1_0.csv');
    gatePath = fullfile(C.results_dir, 'StageU9_Gate_Table_v1_0.csv');
    writetable(replicates, replicatePath);
    writetable(states, statePath);
    writetable(hospitals, hospitalPath);
    writetable(methods, methodPath);
    writetable(decisions, decisionPath);
    writetable(pairResults, pairPath);
    writetable(gates, gatePath);
    gzip(replicatePath);

    sourceDataPath = fullfile(C.results_dir, 'SourceData_U9_Multicentre_Decision_Observability_v1_0.xlsx');
    cmdo_u9_write_source_data_workbook(C, sourceDataPath, hospitals, states, methods, decisions, pairResults, gates);
    cmdo_u9_write_figures(C, hospitals, states, methods, decisions, pairResults, summary);
    reportPath = fullfile(C.results_dir, 'StageU9_Report_v1_0.md');
    cmdo_u9_write_report(C, reportPath, summary, methods, decisions, pairResults, gates);

    complete = struct();
    complete.stage = C.stage;
    complete.version = C.version;
    complete.completed_at_singapore = cmdo_u9_timestamp();
    complete.preoutcome_seal_sha256 = currentSealHash;
    complete.authorization_sha256 = cmdo_u9_sha256_file(C.authorization_path);
    complete.code_sha256 = currentCodeHash;
    complete.reserve_outcome_vault_sha256 = currentVaultHash;
    complete.decision = summary.decision;
    complete.primary_metric = 'NATURAL_PREVALENCE_FIXED_THRESHOLD_ACCURACY';
    complete.primary_decision = 'ACCEPTABLE_IF_HOSPITAL_ACCURACY_AT_LEAST_HISTORICAL_HOSPITAL_MEDIAN';
    complete.summary = summary;
    complete.claim_boundary = ['Hospitals are independent deidentified deployment units in a retrospective database. ' ...
        'Theorem-S6 geometry is evaluated blockwise under the prespecified patient-independence model; ' ...
        'aggregate MAE and decision efficiency are empirical reserve results, not universal no-harm theorems.'];
    complete.restricted_row_level_data = 'NOT_INCLUDED_IN_SHAREABLE_CANONICAL_ZIP';
    complete.successful_rerun = 'PROHIBITED';
    cmdo_u9_write_json(C.complete_path, complete);

    cmdo_u9_copy_authority_files(C);
    manifestPath = fullfile(C.canonical_dir, 'StageU9_Durable_Manifest_v1_0.csv');
    cmdo_u9_write_manifest(C, manifestPath);
    zipPath = cmdo_u9_make_canonical_zip(C);
    zipCommit = struct();
    zipCommit.stage = C.stage;
    zipCommit.version = C.version;
    [~, zipName, zipExt] = fileparts(zipPath);
    zipCommit.canonical_zip = [zipName zipExt];
    zipCommit.canonical_zip_sha256 = cmdo_u9_sha256_file(zipPath);
    zipCommit.manifest_sha256 = cmdo_u9_sha256_file(manifestPath);
    zipCommit.restricted_row_level_data_included = false;
    zipCommit.committed_at_singapore = cmdo_u9_timestamp();
    cmdo_u9_write_json(C.zip_commit_path, zipCommit);

    fprintf('\n================ CMDO U9 COMPLETE ================\n');
    fprintf('Decision: %s\n', summary.decision);
    fprintf('Reserve hospitals: %d\n', summary.reserve_hospital_count);
    fprintf('Pooled CMDO/direct MAE: %.9f / %.9f\n', summary.cmdo_mae, summary.direct_mae);
    fprintf('Relative MAE change: %.4f%%\n', 100 * summary.relative_mae_gain);
    fprintf('Stable-decision cost reduction: %.4f%%\n', 100 * summary.decision_cost_reduction);
    fprintf('CMDO/direct false-assurance rates: %.6f / %.6f\n', summary.cmdo_false_assurance_rate, summary.direct_false_assurance_rate);
    fprintf('Covered-event certificate violations: %d\n', summary.covered_event_certificate_violations);
    fprintf('Maximum fallback residual: %.3g\n', summary.maximum_fallback_residual);
    fprintf('Canonical ZIP SHA-256: %s\n', cmdo_u9_sha256_file(zipPath));
end

function C = cmdo_u9_config(rawDataRoot, projectRoot)
    C.stage = 'U9';
    C.version = 'v1.0';
    C.protocol_name = 'SEALED_MULTICENTRE_DECISION_OBSERVABILITY_RESERVE';
    C.raw_root = rawDataRoot;
    C.project_root = projectRoot;
    C.adapter_dir = fullfile(projectRoot, '00_Data_Adapter');
    C.restricted_dir = fullfile(projectRoot, '00_RESTRICTED_DO_NOT_SHARE');
    C.seal_dir = fullfile(projectRoot, '01_PreOutcome_Seal');
    C.derived_dir = fullfile(projectRoot, '02_Derived');
    C.results_dir = fullfile(projectRoot, '03_Results');
    C.logs_dir = fullfile(projectRoot, '04_Logs');
    C.canonical_dir = fullfile(projectRoot, '05_Canonical');
    C.cache_dir = fullfile(projectRoot, '00_Adapter_Cache');

    stack = dbstack('-completenames');
    C.code_path = stack(1).file;
    if ~isfile(C.code_path)
        error('CMDO:U9:CodePath', 'Could not resolve the executing U9 MATLAB code path.');
    end
    C.package_dir = fileparts(C.code_path);
    C.protocol_path = fullfile(C.package_dir, 'StageU9_Protocol_v1_0.md');

    % Official eICU v2.0 table and cohort specification.
    C.apache_version = 4;                 % APACHE IVa row.
    C.minimum_age = 18;
    C.minimum_hospital_roster = 512;      % Outcome-free score-eligible roster.
    C.source_hospitals = 6;
    C.history_hospitals = 6;
    C.calibration_hospitals = 6;
    C.reserve_hospitals = 20;
    C.required_hospitals = C.source_hospitals + C.history_hospitals + ...
        C.calibration_hospitals + C.reserve_hospitals;

    % Frozen auditing and observer specification.
    C.budgets = [64 128 256];
    C.replicates = 200;
    C.calibration_replicates = 60;
    C.folds = 4;
    C.opposite_fold = [3 4 1 2];
    C.delta_family = 0.05;
    C.delta_block = C.delta_family / C.folds;
    C.max_transport_weight = 0.35;
    C.static_weight_grid = 0:0.05:0.35;
    C.decision_guard_band = 0.01;
    C.role_seed = 2026081001;
    C.master_seed = 2026081002;
    C.calibration_seed = 2026081003;
    C.proxy_ridge = 1e-4;
    C.telemetry_pair_count = 10;
    C.ppi_lambda_min = 0;
    C.ppi_lambda_max = 1;

    % Outcome-free adapter products.
    C.roster_path = fullfile(C.adapter_dir, 'StageU9_OutcomeFree_Roster_v1_0.csv');
    C.roles_path = fullfile(C.adapter_dir, 'StageU9_OutcomeFree_Hospital_Roles_v1_0.csv');
    C.mapping_path = fullfile(C.restricted_dir, 'StageU9_RESTRICTED_Hospital_And_Case_Mapping_v1_0.csv');
    C.development_outcome_path = fullfile(C.restricted_dir, 'StageU9_Development_Outcomes_v1_0.csv');
    C.reserve_vault_path = fullfile(C.restricted_dir, 'StageU9_RESERVE_OUTCOME_VAULT_v1_0.csv');
    C.adapter_seal_path = fullfile(C.adapter_dir, 'StageU9_Data_Adapter_Seal_v1_0.json');

    % PREPARE products.
    C.config_path = fullfile(C.seal_dir, 'StageU9_Frozen_Config_v1_0.json');
    C.model_path = fullfile(C.derived_dir, 'StageU9_Frozen_Observer_Assets_v1_0.mat');
    C.history_path = fullfile(C.derived_dir, 'StageU9_Historical_Performance_Evidence_v1_0.csv');
    C.calibration_path = fullfile(C.derived_dir, 'StageU9_Calibration_Diagnostics_v1_0.csv');
    C.telemetry_path = fullfile(C.seal_dir, 'StageU9_PreOutcome_Hospital_Telemetry_v1_0.csv');
    C.telemetry_pairs_path = fullfile(C.seal_dir, 'StageU9_PreOutcome_Telemetry_Pairs_v1_0.csv');
    C.target_scores_path = fullfile(C.seal_dir, 'StageU9_PreOutcome_Target_Scores_v1_0.csv');
    C.seal_path = fullfile(C.seal_dir, 'StageU9_PreOutcome_Seal_v1_0.json');
    C.authorization_path = fullfile(C.seal_dir, 'StageU9_EXECUTION_AUTHORIZATION_v1_0.json');
    C.analysis_started_path = fullfile(C.results_dir, 'StageU9_ONE_SHOT_ANALYSIS_STARTED_v1_0.json');
    C.complete_path = fullfile(C.canonical_dir, 'StageU9_Complete_v1_0.json');
    C.canonical_zip_path = fullfile(C.project_root, 'CMDO_U9_Canonical_Shareable_Record_v1_0.zip');
    C.zip_commit_path = fullfile(C.project_root, 'StageU9_Canonical_Zip_Commit_v1_0.json');
end

function cmdo_u9_requirements(mode)
    if verLessThan('matlab', '9.13')
        error('CMDO:U9:MATLABVersion', 'CMDO U9 requires MATLAB R2022b (9.13) or newer.');
    end
    required = {'readtable', 'detectImportOptions', 'betainv', 'tiedrank', 'perfcurve'};
    if any(mode == ["PREPARE", "UNSEAL"])
        required{end+1} = 'fitglm'; %#ok<AGROW>
    end
    missing = {};
    for i = 1:numel(required)
        if exist(required{i}, 'file') == 0
            missing{end+1} = required{i}; %#ok<AGROW>
        end
    end
    if ~isempty(missing)
        error('CMDO:U9:Toolbox', ['Missing required MATLAB functions: ' strjoin(missing, ', ') '. ' ...
            'Install/enable Statistics and Machine Learning Toolbox before running U9.']);
    end
end

function cmdo_u9_make_dirs(C)
    dirs = {C.project_root, C.adapter_dir, C.restricted_dir, C.seal_dir, ...
        C.derived_dir, C.results_dir, C.logs_dir, C.canonical_dir, C.cache_dir};
    for i = 1:numel(dirs)
        if ~isfolder(dirs{i})
            mkdir(dirs{i});
        end
    end
end

function cmdo_u9_adapt(C)
    fprintf('\n================ CMDO U9 DATA ADAPTER ================\n');
    fprintf('Official eICU root: %s\n', C.raw_root);
    fprintf('Project root:       %s\n', C.project_root);

    if isfile(C.adapter_seal_path)
        fprintf('An existing adapter seal was found and will not be overwritten.\n');
        fprintf('Adapter seal: %s\n', C.adapter_seal_path);
        fprintf('SHA-256: %s\n', cmdo_u9_sha256_file(C.adapter_seal_path));
        return;
    end
    if isfile(C.seal_path) || isfile(C.analysis_started_path) || isfile(C.complete_path)
        error('CMDO:U9:AdapterOrder', 'ADAPT cannot run after PREPARE or UNSEAL has begun. Use a new clean project root.');
    end

    patientPath = cmdo_u9_locate_table(C, 'patient');
    apachePath = cmdo_u9_locate_table(C, 'apachePatientResult');
    hospitalPath = cmdo_u9_locate_table(C, 'hospital');

    fprintf('Reading only the three official tables required by the frozen adapter...\n');
    P = cmdo_u9_read_selected(C, patientPath, ...
        {'patientUnitStayID','patientHealthSystemStayID','uniquePID','hospitalID', ...
         'unitVisitNumber','age','gender','ethnicity','unitType','unitAdmitSource'});
    A = cmdo_u9_read_selected(C, apachePath, ...
        {'patientUnitStayID','apachePatientsResultsID','apacheVersion', ...
         'predictedHospitalMortality','actualHospitalMortality'});
    H = cmdo_u9_read_selected(C, hospitalPath, ...
        {'hospitalID','numBedsCategory','teachingStatus','region'});

    % Canonical types. The adapter must copy outcomes into role-separated
    % files, but it deliberately computes and prints no outcome statistics.
    P.patientunitstayid = cmdo_u9_to_double(P.patientunitstayid);
    P.patienthealthsystemstayid = cmdo_u9_to_double(P.patienthealthsystemstayid);
    P.hospitalid = cmdo_u9_to_double(P.hospitalid);
    P.unitvisitnumber = cmdo_u9_to_double(P.unitvisitnumber);
    P.age_num = cmdo_u9_parse_age(P.age);
    P.uniquepid = string(P.uniquepid);
    P.gender = string(P.gender);
    P.ethnicity = string(P.ethnicity);
    P.unittype = string(P.unittype);
    P.unitadmitsource = string(P.unitadmitsource);

    A.patientunitstayid = cmdo_u9_to_double(A.patientunitstayid);
    A.apachepatientsresultsid = cmdo_u9_to_double(A.apachepatientsresultsid);
    A.apacheversion_num = cmdo_u9_parse_apache_version(A.apacheversion);
    A.score = cmdo_u9_to_double(A.predictedhospitalmortality);
    A.outcome = cmdo_u9_parse_mortality(A.actualhospitalmortality);

    A = A(A.apacheversion_num == C.apache_version & isfinite(A.score) & A.score >= 0 & A.score <= 1, :);
    A = sortrows(A, {'patientunitstayid','apachepatientsresultsid'});
    [~, ia] = unique(A.patientunitstayid, 'stable');
    A = A(ia, {'patientunitstayid','apacheversion_num','score','outcome'});

    P = P(P.unitvisitnumber == 1 & P.age_num >= C.minimum_age & ...
        isfinite(P.patientunitstayid) & isfinite(P.hospitalid) & strlength(P.uniquepid) > 0, :);
    P = sortrows(P, {'uniquepid','patientunitstayid'});
    [~, ip] = unique(P.uniquepid, 'stable');
    P = P(ip, :);

    T = innerjoin(P, A, 'Keys', 'patientunitstayid');
    T = T(isfinite(T.score) & T.score >= 0 & T.score <= 1, :);
    if isempty(T)
        error('CMDO:U9:EmptyCohort', 'The official tables joined to an empty APACHE-IVa cohort. Check the eICU version and files.');
    end

    hospitalIDs = unique(T.hospitalid);
    counts = zeros(numel(hospitalIDs), 1);
    for i = 1:numel(hospitalIDs)
        counts(i) = sum(T.hospitalid == hospitalIDs(i));
    end
    eligibleIDs = hospitalIDs(counts >= C.minimum_hospital_roster);
    eligibleCounts = counts(counts >= C.minimum_hospital_roster);
    if numel(eligibleIDs) < C.required_hospitals
        error('CMDO:U9:HospitalCount', ['Only %d hospitals have at least %d outcome-free score-eligible cases; ' ...
            'the frozen U9 design requires %d. Do not relax this threshold after viewing outcomes.'], ...
            numel(eligibleIDs), C.minimum_hospital_roster, C.required_hospitals);
    end

    [eligibleIDs, order] = sort(eligibleIDs);
    eligibleCounts = eligibleCounts(order);
    rng(C.role_seed, 'twister');
    selectedOrder = randperm(numel(eligibleIDs), C.required_hospitals);
    selectedIDs = eligibleIDs(selectedOrder);

    role = strings(C.required_hospitals, 1);
    cut1 = C.source_hospitals;
    cut2 = cut1 + C.history_hospitals;
    cut3 = cut2 + C.calibration_hospitals;
    role(1:cut1) = "SOURCE";
    role(cut1+1:cut2) = "HISTORY";
    role(cut2+1:cut3) = "CALIBRATION";
    role(cut3+1:end) = "RESERVE";

    % Pseudonyms are derived independently of role and outcomes.
    sortedSelected = sort(selectedIDs);
    pseudonymBySorted = compose("H%03d", (1:numel(sortedSelected))');
    selectedPseudo = strings(numel(selectedIDs), 1);
    selectedN = zeros(numel(selectedIDs), 1);
    for i = 1:numel(selectedIDs)
        selectedPseudo(i) = pseudonymBySorted(sortedSelected == selectedIDs(i));
        selectedN(i) = sum(T.hospitalid == selectedIDs(i));
    end

    selectedMask = ismember(T.hospitalid, selectedIDs);
    T = T(selectedMask, :);
    T.HOSPITAL = strings(height(T), 1);
    T.ROLE = strings(height(T), 1);
    for i = 1:numel(selectedIDs)
        mask = T.hospitalid == selectedIDs(i);
        T.HOSPITAL(mask) = selectedPseudo(i);
        T.ROLE(mask) = role(i);
    end
    T = sortrows(T, {'HOSPITAL','patientunitstayid'});
    T.CASE_ID = strings(height(T), 1);
    hospitals = unique(T.HOSPITAL, 'stable');
    for i = 1:numel(hospitals)
        idx = find(T.HOSPITAL == hospitals(i));
        T.CASE_ID(idx) = hospitals(i) + "_C" + compose("%05d", (1:numel(idx))');
    end

    H.hospitalid = cmdo_u9_to_double(H.hospitalid);
    H.numbedscategory = string(H.numbedscategory);
    H.teachingstatus = string(H.teachingstatus);
    H.region = string(H.region);
    [~, hLoc] = ismember(T.hospitalid, H.hospitalid);
    T.BED_CATEGORY = repmat("UNKNOWN", height(T), 1);
    T.TEACHING_STATUS = repmat("UNKNOWN", height(T), 1);
    T.REGION = repmat("UNKNOWN", height(T), 1);
    okH = hLoc > 0;
    T.BED_CATEGORY(okH) = H.numbedscategory(hLoc(okH));
    T.TEACHING_STATUS(okH) = H.teachingstatus(hLoc(okH));
    T.REGION(okH) = H.region(hLoc(okH));

    roster = table(T.CASE_ID, T.HOSPITAL, T.ROLE, T.score, T.age_num, ...
        double(upper(strtrim(T.gender)) == "FEMALE"), T.ethnicity, T.unittype, ...
        T.unitadmitsource, T.BED_CATEGORY, T.TEACHING_STATUS, T.REGION, ...
        'VariableNames', {'CASE_ID','HOSPITAL','ROLE','SCORE','AGE','FEMALE', ...
        'ETHNICITY','UNIT_TYPE','UNIT_ADMIT_SOURCE','BED_CATEGORY','TEACHING_STATUS','REGION'});

    roleTable = table(selectedPseudo, role, selectedN, ...
        'VariableNames', {'HOSPITAL','ROLE','OUTCOME_FREE_ROSTER_N'});
    roleTable = sortrows(roleTable, 'HOSPITAL');

    mapping = table(T.CASE_ID, T.HOSPITAL, T.hospitalid, T.patientunitstayid, ...
        T.patienthealthsystemstayid, T.uniquepid, ...
        'VariableNames', {'CASE_ID','HOSPITAL','RAW_HOSPITAL_ID','PATIENT_UNIT_STAY_ID', ...
        'PATIENT_HEALTH_SYSTEM_STAY_ID','UNIQUE_PID'});
    outcomes = table(T.CASE_ID, T.HOSPITAL, T.ROLE, T.outcome, ...
        'VariableNames', {'CASE_ID','HOSPITAL','ROLE','Y'});
    developmentOutcomes = outcomes(outcomes.ROLE ~= "RESERVE", {'CASE_ID','HOSPITAL','ROLE','Y'});
    reserveOutcomes = outcomes(outcomes.ROLE == "RESERVE", {'CASE_ID','HOSPITAL','ROLE','Y'});

    writetable(roster, C.roster_path);
    writetable(roleTable, C.roles_path);
    writetable(mapping, C.mapping_path);
    writetable(developmentOutcomes, C.development_outcome_path);
    writetable(reserveOutcomes, C.reserve_vault_path);

    adapterSeal = struct();
    adapterSeal.stage = C.stage;
    adapterSeal.version = C.version;
    adapterSeal.created_at_singapore = cmdo_u9_timestamp();
    adapterSeal.decision = 'SPLIT_OUTCOME_FREE_ROSTER_DEVELOPMENT_OUTCOMES_AND_SEALED_RESERVE_VAULT';
    adapterSeal.data_source = 'eICU Collaborative Research Database v2.0';
    adapterSeal.apache_version = C.apache_version;
    adapterSeal.minimum_age = C.minimum_age;
    adapterSeal.minimum_hospital_roster = C.minimum_hospital_roster;
    adapterSeal.role_seed = C.role_seed;
    adapterSeal.role_counts = struct('source',C.source_hospitals,'history',C.history_hospitals, ...
        'calibration',C.calibration_hospitals,'reserve',C.reserve_hospitals);
    adapterSeal.reserve_outcome_statistics_computed_or_printed = false;
    adapterSeal.patient_file_sha256 = cmdo_u9_sha256_file(patientPath);
    adapterSeal.apache_patient_result_file_sha256 = cmdo_u9_sha256_file(apachePath);
    adapterSeal.hospital_file_sha256 = cmdo_u9_sha256_file(hospitalPath);
    adapterSeal.outcome_free_roster_sha256 = cmdo_u9_sha256_file(C.roster_path);
    adapterSeal.hospital_roles_sha256 = cmdo_u9_sha256_file(C.roles_path);
    adapterSeal.development_outcomes_sha256 = cmdo_u9_sha256_file(C.development_outcome_path);
    adapterSeal.reserve_outcome_vault_sha256 = cmdo_u9_sha256_file(C.reserve_vault_path);
    adapterSeal.restricted_mapping_sha256 = cmdo_u9_sha256_file(C.mapping_path);
    adapterSeal.outcome_free_roster_rows = height(roster);
    adapterSeal.reserve_hospital_count = sum(roleTable.ROLE == "RESERVE");
    adapterSeal.restricted_data_sharing = 'PROHIBITED_BY_PACKAGE_GOVERNANCE_AND_SUBJECT_TO_PHYSIONET_DUA';
    cmdo_u9_write_json(C.adapter_seal_path, adapterSeal);

    note = sprintf(['CMDO U9 DATA ADAPTER COMPLETE\n' ...
        'No reserve outcome prevalence or performance statistic was computed or printed.\n' ...
        'Adapter seal: %s\n' ...
        'Adapter seal SHA-256: %s\n' ...
        'Reserve vault SHA-256: %s\n' ...
        'Next action: run RUN_PREPARE.m. Do not open the reserve vault.\n'], ...
        C.adapter_seal_path, cmdo_u9_sha256_file(C.adapter_seal_path), ...
        adapterSeal.reserve_outcome_vault_sha256);
    cmdo_u9_write_text(fullfile(C.logs_dir, 'StageU9_DATA_ADAPTER_COMPLETE_v1_0.txt'), note);
    fprintf('\n%s\n', note);
end

function [repTable, stateTable, hospitalTable, methodTable, decisionTable, pairTable, summary, gateTable] = ...
        cmdo_u9_execute_frozen_evaluation(C, truth, telemetry, telemetryPairs, S)
    allHospitals = sort(unique(truth.HOSPITAL));
    evaluable = strings(0,1);
    for i = 1:numel(allHospitals)
        if sum(truth.HOSPITAL == allHospitals(i)) >= max(C.budgets)
            evaluable(end+1,1) = allHospitals(i); %#ok<AGROW>
        end
    end
    if isempty(evaluable)
        error('CMDO:U9:NoEvaluableHospitals', 'No reserve hospital retains enough finite outcomes for the largest frozen budget.');
    end

    repRecords = repmat(cmdo_u9_empty_rep_record(), 0, 1);
    hospitalRecords = repmat(cmdo_u9_empty_hospital_record(), 0, 1);
    for hi = 1:numel(evaluable)
        hospital = evaluable(hi);
        T = truth(truth.HOSPITAL == hospital, :);
        theta = mean(T.CORRECT);
        trueAUC = cmdo_u9_auc(T.SCORE, T.Y);
        tele = telemetry(telemetry.HOSPITAL == hospital, :);
        if height(tele) ~= 1
            error('CMDO:U9:TelemetryJoin', 'Expected exactly one telemetry row for %s.', hospital);
        end

        hrec = cmdo_u9_empty_hospital_record();
        hrec.hospital = hospital;
        hrec.n = height(T);
        hrec.prevalence = mean(T.Y);
        hrec.true_accuracy = theta;
        hrec.true_auc = trueAUC;
        hrec.historical_bias = S.historicalAccuracy - theta;
        hrec.atc_estimate = tele.ATC_ESTIMATE(1);
        hrec.proxy_mean = mean(T.PROXY_CORRECTNESS);
        hrec.true_state = cmdo_u9_true_state(theta, S.primaryFloor);
        hrec.lenient_state = cmdo_u9_true_state(theta, S.lenientFloor);
        hrec.strict_state = cmdo_u9_true_state(theta, S.strictFloor);
        hrec.in_primary_indifference_zone = abs(theta - S.primaryFloor) < C.decision_guard_band;
        hospitalRecords(end+1) = hrec; %#ok<AGROW>

        for ri = 1:C.replicates
            seed = cmdo_u9_derived_seed(C.master_seed, hi, ri);
            rng(seed, 'twister');
            order = randperm(height(T), max(C.budgets));
            for bi = 1:numel(C.budgets)
                b = C.budgets(bi);
                W = T(order(1:b), :);
                direct = mean(W.CORRECT);
                staticEstimate = (1 - S.staticWeight) * direct + S.staticWeight * S.historicalAccuracy;
                [ppiEstimate, ppiLambda] = cmdo_u9_ppi_estimate(W.CORRECT, W.PROXY_CORRECTNESS, ...
                    mean(T.PROXY_CORRECTNESS), C.ppi_lambda_min, C.ppi_lambda_max);
                [cmdoEstimate, meanWeight, maxWeight, fallbackResidual, simultaneousCoverage, certViolations] = ...
                    cmdo_u9_guarded_estimate(C, W.CORRECT, theta, S.historicalAccuracy);
                atcEstimate = tele.ATC_ESTIMATE(1);

                rec = cmdo_u9_empty_rep_record();
                rec.hospital = hospital;
                rec.budget = b;
                rec.replicate = ri;
                rec.seed = seed;
                rec.target_n = height(T);
                rec.audit_positive_n = sum(W.Y == 1);
                rec.audit_negative_n = sum(W.Y == 0);
                rec.true_accuracy = theta;
                rec.primary_floor = S.primaryFloor;
                rec.true_state = cmdo_u9_true_state(theta, S.primaryFloor);
                rec.indifference_zone = abs(theta - S.primaryFloor) < C.decision_guard_band;
                rec.direct_estimate = direct;
                rec.static_estimate = min(1, max(0, staticEstimate));
                rec.atc_estimate = min(1, max(0, atcEstimate));
                rec.ppi_estimate = min(1, max(0, ppiEstimate));
                rec.cmdo_estimate = min(1, max(0, cmdoEstimate));
                rec.direct_abs_error = abs(rec.direct_estimate - theta);
                rec.static_abs_error = abs(rec.static_estimate - theta);
                rec.atc_abs_error = abs(rec.atc_estimate - theta);
                rec.ppi_abs_error = abs(rec.ppi_estimate - theta);
                rec.cmdo_abs_error = abs(rec.cmdo_estimate - theta);
                rec.cmdo_regret = rec.cmdo_abs_error - rec.direct_abs_error;
                rec.static_weight = S.staticWeight;
                rec.ppi_lambda = ppiLambda;
                rec.mean_transport_weight = meanWeight;
                rec.max_transport_weight = maxWeight;
                rec.fallback_residual = fallbackResidual;
                rec.simultaneous_coverage = simultaneousCoverage;
                rec.covered_event_certificate_violations = certViolations;
                rec.direct_decision = cmdo_u9_estimated_decision(rec.direct_estimate, S.primaryFloor, C.decision_guard_band);
                rec.static_decision = cmdo_u9_estimated_decision(rec.static_estimate, S.primaryFloor, C.decision_guard_band);
                rec.atc_decision = cmdo_u9_estimated_decision(rec.atc_estimate, S.primaryFloor, C.decision_guard_band);
                rec.ppi_decision = cmdo_u9_estimated_decision(rec.ppi_estimate, S.primaryFloor, C.decision_guard_band);
                rec.cmdo_decision = cmdo_u9_estimated_decision(rec.cmdo_estimate, S.primaryFloor, C.decision_guard_band);
                repRecords(end+1) = rec; %#ok<AGROW>
            end
        end
    end
    repTable = struct2table(repRecords);
    hospitalTable = struct2table(hospitalRecords);

    stateTable = cmdo_u9_make_state_table(C, repTable);
    hospitalTable = cmdo_u9_add_hospital_results(repTable, hospitalTable);
    methodTable = cmdo_u9_make_method_table(repTable);
    decisionTable = cmdo_u9_make_decision_table(C, repTable);
    pairTable = cmdo_u9_reveal_telemetry_pairs(telemetryPairs, hospitalTable);

    directRow = methodTable(methodTable.method == "DIRECT", :);
    cmdoRow = methodTable(methodTable.method == "CMDO", :);
    directDecision = decisionTable(decisionTable.method == "DIRECT" & decisionTable.budget == max(C.budgets), :);
    cmdoDecision = decisionTable(decisionTable.method == "CMDO" & decisionTable.budget == max(C.budgets), :);
    directCost = cmdo_u9_mean_stable_cost(C, repTable, 'direct_decision');
    cmdoCost = cmdo_u9_mean_stable_cost(C, repTable, 'cmdo_decision');

    summary = struct();
    summary.selected_reserve_hospital_count = C.reserve_hospitals;
    summary.reserve_hospital_count = numel(evaluable);
    summary.hospitals_lost_to_outcome_completeness = C.reserve_hospitals - numel(evaluable);
    summary.direct_mae = directRow.mae(1);
    summary.cmdo_mae = cmdoRow.mae(1);
    summary.relative_mae_gain = (summary.direct_mae - summary.cmdo_mae) / max(summary.direct_mae, eps);
    summary.worst_state_regret = max(stateTable.cmdo_regret);
    summary.hospitals_noninferior = sum(hospitalTable.cmdo_mae <= hospitalTable.direct_mae);
    summary.hospital_noninferiority_fraction = summary.hospitals_noninferior / max(height(hospitalTable), 1);
    summary.mean_transport_weight = mean(repTable.mean_transport_weight);
    summary.mean_simultaneous_coverage = mean(stateTable.simultaneous_coverage);
    summary.minimum_state_simultaneous_coverage = min(stateTable.simultaneous_coverage);
    summary.covered_event_certificate_violations = sum(repTable.covered_event_certificate_violations);
    summary.maximum_fallback_residual = max(repTable.fallback_residual);
    summary.direct_false_assurance_rate = directDecision.false_assurance_rate(1);
    summary.cmdo_false_assurance_rate = cmdoDecision.false_assurance_rate(1);
    summary.direct_max_budget_correct_resolution = directDecision.correct_resolution_rate(1);
    summary.cmdo_max_budget_correct_resolution = cmdoDecision.correct_resolution_rate(1);
    summary.direct_stable_decision_cost = directCost;
    summary.cmdo_stable_decision_cost = cmdoCost;
    summary.decision_cost_reduction = (directCost - cmdoCost) / max(directCost, eps);
    summary.maximum_matched_pair_accuracy_gap = max(pairTable.TRUE_ACCURACY_GAP, [], 'omitnan');
    summary.median_matched_pair_accuracy_gap = median(pairTable.TRUE_ACCURACY_GAP, 'omitnan');
    if height(hospitalTable) >= 3 && numel(unique(abs(hospitalTable.historical_bias))) > 1
        summary.bias_weight_spearman = corr(tiedrank(abs(hospitalTable.historical_bias)), ...
            tiedrank(hospitalTable.mean_transport_weight), 'Rows', 'complete');
    else
        summary.bias_weight_spearman = NaN;
    end

    gates = repmat(cmdo_u9_gate('', '', NaN, false, ''), 0, 1);
    gates(end+1) = cmdo_u9_gate('twenty_independent_reserve_hospitals', '>=20', summary.reserve_hospital_count, ...
        summary.reserve_hospital_count >= 20, 'integrity'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('exact_full_direct_fallback', '<1e-12', summary.maximum_fallback_residual, ...
        summary.maximum_fallback_residual < 1e-12, 'integrity'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('covered_event_certificate_violations', '=0', summary.covered_event_certificate_violations, ...
        summary.covered_event_certificate_violations == 0, 'certification'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('mean_simultaneous_coverage', '>=0.90', summary.mean_simultaneous_coverage, ...
        summary.mean_simultaneous_coverage >= 0.90, 'certification'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('minimum_state_simultaneous_coverage', '>=0.80', summary.minimum_state_simultaneous_coverage, ...
        summary.minimum_state_simultaneous_coverage >= 0.80, 'certification'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('pooled_cmdo_mae_noninferiority', 'CMDO<=Direct', summary.cmdo_mae - summary.direct_mae, ...
        summary.cmdo_mae <= summary.direct_mae, 'empirical_safety'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('worst_hospital_budget_regret', '<=0.010', summary.worst_state_regret, ...
        summary.worst_state_regret <= 0.010, 'empirical_safety'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('hospital_breadth', '>=75%', summary.hospital_noninferiority_fraction, ...
        summary.hospital_noninferiority_fraction >= 0.75, 'empirical_safety'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('false_assurance_noninferiority', 'CMDO<=Direct+0.005', ...
        summary.cmdo_false_assurance_rate - summary.direct_false_assurance_rate, ...
        summary.cmdo_false_assurance_rate <= summary.direct_false_assurance_rate + 0.005, 'decision_safety'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('stable_decision_cost_reduction', '>=10%', summary.decision_cost_reduction, ...
        summary.decision_cost_reduction >= 0.10, 'decision_efficiency'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('max_budget_correct_resolution_noninferiority', 'CMDO>=Direct', ...
        summary.cmdo_max_budget_correct_resolution - summary.direct_max_budget_correct_resolution, ...
        summary.cmdo_max_budget_correct_resolution >= summary.direct_max_budget_correct_resolution, 'decision_efficiency'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('bias_guard_mechanism', 'Spearman<=-0.50', summary.bias_weight_spearman, ...
        isfinite(summary.bias_weight_spearman) && summary.bias_weight_spearman <= -0.50, 'mechanism'); %#ok<AGROW>
    gates(end+1) = cmdo_u9_gate('matched_telemetry_witness', 'max accuracy gap>=0.03', ...
        summary.maximum_matched_pair_accuracy_gap, summary.maximum_matched_pair_accuracy_gap >= 0.03, 'conceptual_witness'); %#ok<AGROW>
    gateTable = struct2table(gates);

    integrityCategories = ["integrity","certification"];
    coreCategories = [integrityCategories,"empirical_safety","decision_safety"];
    categoryChangingCategories = [coreCategories,"decision_efficiency","mechanism","conceptual_witness"];
    integrityPass = all(gateTable.passed(ismember(gateTable.category, integrityCategories)));
    corePass = all(gateTable.passed(ismember(gateTable.category, coreCategories)));
    categoryPass = all(gateTable.passed(ismember(gateTable.category, categoryChangingCategories)));
    if categoryPass
        summary.decision = 'SUPPORT_CATEGORY_CHANGING_MULTICENTRE_DECISION_OBSERVABILITY_U9';
    elseif corePass
        summary.decision = 'SUPPORT_MULTICENTRE_SAFETY_EVIDENCE_DECISION_EFFICIENCY_OR_WITNESS_INCOMPLETE';
    elseif integrityPass
        summary.decision = 'INTEGRITY_SUPPORTED_EMPIRICAL_SAFETY_NOT_CONFIRMED';
    else
        summary.decision = 'FAIL_U9_INTEGRITY_OR_CERTIFICATION_GATE';
    end
end

function [estimate, meanWeight, maxWeight, fallbackResidual, simultaneousCoverage, certViolations] = ...
        cmdo_u9_guarded_estimate(C, z, theta, historicalAccuracy)
    b = numel(z);
    if mod(b, C.folds) ~= 0
        error('CMDO:U9:FoldBudget', 'Budget %d is not divisible by %d folds.', b, C.folds);
    end
    foldSize = b / C.folds;
    fold = reshape(1:b, foldSize, C.folds);
    E = zeros(C.folds, 1);
    D = zeros(C.folds, 1);
    weights = zeros(C.folds, 1);
    cover = false(C.folds, 1);
    violation = false(C.folds, 1);
    for q = 1:C.folds
        directRows = fold(:, q);
        auxRows = fold(:, C.opposite_fold(q));
        zDirect = z(directRows);
        zAux = z(auxRows);
        D(q) = mean(zDirect);
        [lo, hi] = cmdo_u9_clopper_pearson(sum(zAux), numel(zAux), C.delta_block);
        L = min(lo * (1 - lo), hi * (1 - hi)) / numel(zDirect);
        U = max((historicalAccuracy - lo)^2, (historicalAccuracy - hi)^2);
        if L <= 0
            w = 0;
        else
            w = min(C.max_transport_weight, 2 * L / (L + U + eps));
        end
        weights(q) = w;
        E(q) = (1 - w) * D(q) + w * historicalAccuracy;
        cover(q) = lo <= theta && theta <= hi;
        Vtrue = theta * (1 - theta) / numel(zDirect);
        Btrue2 = (historicalAccuracy - theta)^2;
        oracleCap = 2 * Vtrue / (Vtrue + Btrue2 + eps);
        violation(q) = cover(q) && w > oracleCap + 1e-12;
    end
    estimate = mean(E);
    meanWeight = mean(weights);
    maxWeight = max(weights);
    fallbackResidual = abs(mean(D) - mean(z));
    simultaneousCoverage = all(cover);
    certViolations = sum(violation);
end

function [estimate, lambda] = cmdo_u9_ppi_estimate(z, proxyAudit, proxyPopulationMean, lambdaMin, lambdaMax)
    z = double(z(:));
    proxyAudit = double(proxyAudit(:));
    if numel(z) < 2 || var(proxyAudit, 1) < 1e-12
        lambda = 0;
    else
        centeredZ = z - mean(z);
        centeredP = proxyAudit - mean(proxyAudit);
        lambda = mean(centeredZ .* centeredP) / max(mean(centeredP.^2), eps);
        lambda = min(lambdaMax, max(lambdaMin, lambda));
    end
    estimate = mean(z) + lambda * (proxyPopulationMean - mean(proxyAudit));
end

function stateTable = cmdo_u9_make_state_table(C, R)
    hospitals = sort(unique(R.hospital));
    records = repmat(cmdo_u9_empty_state_record(), 0, 1);
    for hi = 1:numel(hospitals)
        for bi = 1:numel(C.budgets)
            X = R(R.hospital == hospitals(hi) & R.budget == C.budgets(bi), :);
            if isempty(X)
                continue;
            end
            s = cmdo_u9_empty_state_record();
            s.hospital = hospitals(hi);
            s.budget = C.budgets(bi);
            s.target_n = X.target_n(1);
            s.true_accuracy = X.true_accuracy(1);
            s.true_state = X.true_state(1);
            s.direct_mae = mean(X.direct_abs_error);
            s.static_mae = mean(X.static_abs_error);
            s.atc_mae = mean(X.atc_abs_error);
            s.ppi_mae = mean(X.ppi_abs_error);
            s.cmdo_mae = mean(X.cmdo_abs_error);
            s.cmdo_regret = s.cmdo_mae - s.direct_mae;
            s.relative_gain = (s.direct_mae - s.cmdo_mae) / max(s.direct_mae, eps);
            s.mean_transport_weight = mean(X.mean_transport_weight);
            s.mean_ppi_lambda = mean(X.ppi_lambda);
            s.simultaneous_coverage = mean(X.simultaneous_coverage);
            s.covered_event_certificate_violations = sum(X.covered_event_certificate_violations);
            s.maximum_fallback_residual = max(X.fallback_residual);
            s.direct_correct_resolution_rate = mean(X.direct_decision == X.true_state);
            s.cmdo_correct_resolution_rate = mean(X.cmdo_decision == X.true_state);
            s.direct_false_assurance_rate = cmdo_u9_false_assurance_rate(X.direct_decision, X.true_state);
            s.cmdo_false_assurance_rate = cmdo_u9_false_assurance_rate(X.cmdo_decision, X.true_state);
            records(end+1) = s; %#ok<AGROW>
        end
    end
    stateTable = struct2table(records);
end

function H = cmdo_u9_add_hospital_results(R, H)
    H.direct_mae = zeros(height(H), 1);
    H.static_mae = zeros(height(H), 1);
    H.atc_mae = zeros(height(H), 1);
    H.ppi_mae = zeros(height(H), 1);
    H.cmdo_mae = zeros(height(H), 1);
    H.relative_gain = zeros(height(H), 1);
    H.mean_transport_weight = zeros(height(H), 1);
    H.direct_false_assurance_rate = zeros(height(H), 1);
    H.cmdo_false_assurance_rate = zeros(height(H), 1);
    H.criterion_reversal = false(height(H), 1);
    for i = 1:height(H)
        X = R(R.hospital == H.hospital(i), :);
        H.direct_mae(i) = mean(X.direct_abs_error);
        H.static_mae(i) = mean(X.static_abs_error);
        H.atc_mae(i) = mean(X.atc_abs_error);
        H.ppi_mae(i) = mean(X.ppi_abs_error);
        H.cmdo_mae(i) = mean(X.cmdo_abs_error);
        H.relative_gain(i) = (H.direct_mae(i) - H.cmdo_mae(i)) / max(H.direct_mae(i), eps);
        H.mean_transport_weight(i) = mean(X.mean_transport_weight);
        H.direct_false_assurance_rate(i) = cmdo_u9_false_assurance_rate(X.direct_decision, X.true_state);
        H.cmdo_false_assurance_rate(i) = cmdo_u9_false_assurance_rate(X.cmdo_decision, X.true_state);
        H.criterion_reversal(i) = H.lenient_state(i) ~= H.strict_state(i);
    end
end

function methodTable = cmdo_u9_make_method_table(R)
    method = ["DIRECT";"STATIC";"ATC";"PPI_PLUS_PLUS_STYLE";"CMDO"];
    errorFields = {'direct_abs_error','static_abs_error','atc_abs_error','ppi_abs_error','cmdo_abs_error'};
    estimateFields = {'direct_estimate','static_estimate','atc_estimate','ppi_estimate','cmdo_estimate'};
    decisionFields = {'direct_decision','static_decision','atc_decision','ppi_decision','cmdo_decision'};
    mae = zeros(numel(method),1);
    rmse = zeros(numel(method),1);
    bias = zeros(numel(method),1);
    correctResolution = zeros(numel(method),1);
    falseAssurance = zeros(numel(method),1);
    falseRejection = zeros(numel(method),1);
    unresolved = zeros(numel(method),1);
    for i = 1:numel(method)
        err = R.(errorFields{i});
        est = R.(estimateFields{i});
        dec = R.(decisionFields{i});
        mae(i) = mean(err);
        rmse(i) = sqrt(mean((est - R.true_accuracy).^2));
        bias(i) = mean(est - R.true_accuracy);
        correctResolution(i) = mean(dec == R.true_state);
        falseAssurance(i) = cmdo_u9_false_assurance_rate(dec, R.true_state);
        falseRejection(i) = cmdo_u9_false_rejection_rate(dec, R.true_state);
        unresolved(i) = mean(dec == 0);
    end
    methodTable = table(method, mae, rmse, bias, correctResolution, falseAssurance, falseRejection, unresolved, ...
        'VariableNames', {'method','mae','rmse','bias','correct_resolution_rate','false_assurance_rate', ...
        'false_rejection_rate','unresolved_rate'});
end

function decisionTable = cmdo_u9_make_decision_table(C, R)
    methods = ["DIRECT","STATIC","ATC","PPI_PLUS_PLUS_STYLE","CMDO"];
    fields = {'direct_decision','static_decision','atc_decision','ppi_decision','cmdo_decision'};
    records = repmat(struct('method',"",'budget',0,'correct_resolution_rate',NaN, ...
        'false_assurance_rate',NaN,'false_rejection_rate',NaN,'unresolved_rate',NaN, ...
        'stable_decision_cost',NaN), 0, 1);
    for mi = 1:numel(methods)
        stableCost = cmdo_u9_mean_stable_cost(C, R, fields{mi});
        for bi = 1:numel(C.budgets)
            X = R(R.budget == C.budgets(bi), :);
            rec = struct();
            rec.method = methods(mi);
            rec.budget = C.budgets(bi);
            dec = X.(fields{mi});
            rec.correct_resolution_rate = mean(dec == X.true_state);
            rec.false_assurance_rate = cmdo_u9_false_assurance_rate(dec, X.true_state);
            rec.false_rejection_rate = cmdo_u9_false_rejection_rate(dec, X.true_state);
            rec.unresolved_rate = mean(dec == 0);
            rec.stable_decision_cost = stableCost;
            records(end+1) = rec; %#ok<AGROW>
        end
    end
    decisionTable = struct2table(records);
end

function costMean = cmdo_u9_mean_stable_cost(C, R, decisionField)
    hospitals = sort(unique(R.hospital));
    costs = zeros(numel(hospitals) * C.replicates, 1);
    cursor = 0;
    for hi = 1:numel(hospitals)
        for ri = 1:C.replicates
            X = R(R.hospital == hospitals(hi) & R.replicate == ri, :);
            X = sortrows(X, 'budget');
            if isempty(X)
                continue;
            end
            cursor = cursor + 1;
            dec = X.(decisionField);
            trueState = X.true_state(1);
            stableIdx = [];
            for j = 1:height(X)
                if all(dec(j:end) == trueState)
                    stableIdx = j;
                    break;
                end
            end
            if isempty(stableIdx)
                costs(cursor) = 2 * max(C.budgets);
            elseif strcmp(decisionField, 'atc_decision')
                costs(cursor) = 0;
            else
                costs(cursor) = X.budget(stableIdx);
            end
        end
    end
    costs = costs(1:cursor);
    costMean = mean(costs);
end

function rate = cmdo_u9_false_assurance_rate(decision, trueState)
    denom = sum(trueState == -1);
    if denom == 0
        rate = 0;
    else
        rate = sum(decision == 1 & trueState == -1) / denom;
    end
end

function rate = cmdo_u9_false_rejection_rate(decision, trueState)
    denom = sum(trueState == 1);
    if denom == 0
        rate = 0;
    else
        rate = sum(decision == -1 & trueState == 1) / denom;
    end
end

function pairTable = cmdo_u9_reveal_telemetry_pairs(P, H)
    pairTable = P;
    pairTable.TRUE_ACCURACY_A = NaN(height(P),1);
    pairTable.TRUE_ACCURACY_B = NaN(height(P),1);
    pairTable.TRUE_ACCURACY_GAP = NaN(height(P),1);
    pairTable.ATC_ESTIMATE_A = NaN(height(P),1);
    pairTable.ATC_ESTIMATE_B = NaN(height(P),1);
    pairTable.ATC_ESTIMATE_GAP = NaN(height(P),1);
    pairTable.ATC_GAP_UNDERESTIMATION = NaN(height(P),1);
    for i = 1:height(P)
        ia = find(H.hospital == P.HOSPITAL_A(i), 1);
        ib = find(H.hospital == P.HOSPITAL_B(i), 1);
        if isempty(ia) || isempty(ib)
            continue;
        end
        pairTable.TRUE_ACCURACY_A(i) = H.true_accuracy(ia);
        pairTable.TRUE_ACCURACY_B(i) = H.true_accuracy(ib);
        pairTable.TRUE_ACCURACY_GAP(i) = abs(H.true_accuracy(ia) - H.true_accuracy(ib));
        pairTable.ATC_ESTIMATE_A(i) = H.atc_estimate(ia);
        pairTable.ATC_ESTIMATE_B(i) = H.atc_estimate(ib);
        pairTable.ATC_ESTIMATE_GAP(i) = abs(H.atc_estimate(ia) - H.atc_estimate(ib));
        pairTable.ATC_GAP_UNDERESTIMATION(i) = pairTable.TRUE_ACCURACY_GAP(i) - pairTable.ATC_ESTIMATE_GAP(i);
    end
end

function state = cmdo_u9_true_state(theta, floorValue)
    if theta >= floorValue
        state = 1;
    else
        state = -1;
    end
end

function decision = cmdo_u9_estimated_decision(estimate, floorValue, guardBand)
    if estimate >= floorValue + guardBand
        decision = 1;
    elseif estimate <= floorValue - guardBand
        decision = -1;
    else
        decision = 0;
    end
end

function telemetry = cmdo_u9_hospital_telemetry(roster, roles, threshold, atcThreshold)
    hospitals = sort(unique(roster.HOSPITAL));
    records = repmat(struct('HOSPITAL',"",'ROLE',"",'N',0,'SCORE_MEAN',NaN,'SCORE_SD',NaN, ...
        'SCORE_Q10',NaN,'SCORE_Q25',NaN,'SCORE_Q50',NaN,'SCORE_Q75',NaN,'SCORE_Q90',NaN, ...
        'PREDICTED_POSITIVE_RATE',NaN,'CONFIDENCE_MEAN',NaN,'CONFIDENCE_SD',NaN, ...
        'AGE_MEAN',NaN,'AGE_SD',NaN,'FEMALE_FRACTION',NaN,'ATC_ESTIMATE',NaN, ...
        'PROXY_MEAN',NaN), 0, 1);
    for i = 1:numel(hospitals)
        X = roster(roster.HOSPITAL == hospitals(i), :);
        roleRow = roles(roles.HOSPITAL == hospitals(i), :);
        rec = struct();
        rec.HOSPITAL = hospitals(i);
        if isempty(roleRow), rec.ROLE = "UNKNOWN"; else, rec.ROLE = roleRow.ROLE(1); end
        rec.N = height(X);
        rec.SCORE_MEAN = mean(X.SCORE);
        rec.SCORE_SD = std(X.SCORE);
        q = quantile(X.SCORE, [0.10 0.25 0.50 0.75 0.90]);
        rec.SCORE_Q10 = q(1);
        rec.SCORE_Q25 = q(2);
        rec.SCORE_Q50 = q(3);
        rec.SCORE_Q75 = q(4);
        rec.SCORE_Q90 = q(5);
        rec.PREDICTED_POSITIVE_RATE = mean(X.SCORE >= threshold);
        rec.CONFIDENCE_MEAN = mean(X.CONFIDENCE);
        rec.CONFIDENCE_SD = std(X.CONFIDENCE);
        rec.AGE_MEAN = mean(X.AGE, 'omitnan');
        rec.AGE_SD = std(X.AGE, 'omitnan');
        rec.FEMALE_FRACTION = mean(X.FEMALE, 'omitnan');
        rec.ATC_ESTIMATE = mean(X.CONFIDENCE >= atcThreshold);
        if ismember('PROXY_CORRECTNESS', X.Properties.VariableNames)
            rec.PROXY_MEAN = mean(X.PROXY_CORRECTNESS);
        else
            rec.PROXY_MEAN = NaN;
        end
        records(end+1) = rec; %#ok<AGROW>
    end
    telemetry = struct2table(records);
end

function pairs = cmdo_u9_select_telemetry_pairs(T, requestedPairs)
    featureNames = {'SCORE_MEAN','SCORE_SD','SCORE_Q10','SCORE_Q25','SCORE_Q50', ...
        'SCORE_Q75','SCORE_Q90','PREDICTED_POSITIVE_RATE','CONFIDENCE_MEAN', ...
        'CONFIDENCE_SD','AGE_MEAN','AGE_SD','FEMALE_FRACTION','ATC_ESTIMATE','PROXY_MEAN'};
    X = T{:, featureNames};
    for j = 1:size(X,2)
        bad = ~isfinite(X(:,j));
        if any(bad)
            X(bad,j) = median(X(~bad,j), 'omitnan');
        end
    end
    mu = mean(X,1);
    sd = std(X,0,1);
    keep = isfinite(sd) & sd > 1e-12;
    X = (X(:,keep) - mu(keep)) ./ sd(keep);
    available = true(height(T),1);
    nPairs = min(requestedPairs, floor(height(T)/2));
    records = repmat(struct('PAIR_ID',0,'HOSPITAL_A',"",'HOSPITAL_B',"",'TELEMETRY_DISTANCE',NaN), 0, 1);
    for k = 1:nPairs
        idx = find(available);
        bestD = Inf; bestA = NaN; bestB = NaN;
        for ai = 1:numel(idx)-1
            for bi = ai+1:numel(idx)
                d = sqrt(sum((X(idx(ai),:) - X(idx(bi),:)).^2));
                if d < bestD - 1e-12 || (abs(d-bestD) <= 1e-12 && ...
                        (idx(ai) < bestA || (idx(ai) == bestA && idx(bi) < bestB)))
                    bestD = d; bestA = idx(ai); bestB = idx(bi);
                end
            end
        end
        if ~isfinite(bestD), break; end
        rec = struct('PAIR_ID',k,'HOSPITAL_A',T.HOSPITAL(bestA), ...
            'HOSPITAL_B',T.HOSPITAL(bestB),'TELEMETRY_DISTANCE',bestD);
        records(end+1) = rec; %#ok<AGROW>
        available([bestA bestB]) = false;
    end
    pairs = struct2table(records);
end

function [bestWeight, diagnostics] = cmdo_u9_tune_static_weight(C, calibration, historicalAccuracy)
    hospitals = sort(unique(calibration.HOSPITAL));
    errorSum = zeros(numel(C.static_weight_grid),1);
    errorN = zeros(numel(C.static_weight_grid),1);
    for hi = 1:numel(hospitals)
        T = calibration(calibration.HOSPITAL == hospitals(hi), :);
        if height(T) < max(C.budgets), continue; end
        theta = mean(T.CORRECT);
        for ri = 1:C.calibration_replicates
            seed = cmdo_u9_derived_seed(C.calibration_seed, hi, ri);
            rng(seed, 'twister');
            order = randperm(height(T), max(C.budgets));
            for bi = 1:numel(C.budgets)
                direct = mean(T.CORRECT(order(1:C.budgets(bi))));
                for wi = 1:numel(C.static_weight_grid)
                    w = C.static_weight_grid(wi);
                    estimate = (1-w)*direct + w*historicalAccuracy;
                    errorSum(wi) = errorSum(wi) + abs(estimate-theta);
                    errorN(wi) = errorN(wi) + 1;
                end
            end
        end
    end
    if any(errorN == 0)
        error('CMDO:U9:Calibration', 'Insufficient calibration hospitals for the frozen maximum budget.');
    end
    mae = errorSum ./ errorN;
    [~, bestIdx] = min(mae);
    bestWeight = C.static_weight_grid(bestIdx);
    diagnostics = table(C.static_weight_grid(:), mae, errorN, ...
        (1:numel(C.static_weight_grid))' == bestIdx, ...
        'VariableNames', {'STATIC_WEIGHT','CALIBRATION_MAE','WITNESS_COUNT','SELECTED'});
end

function X = cmdo_u9_proxy_features(T, threshold)
    score = min(1-eps, max(eps, double(T.SCORE)));
    confidence = cmdo_u9_operating_confidence(score, threshold);
    predicted = double(score >= threshold);
    age = double(T.AGE) / 100;
    age(~isfinite(age)) = median(age(isfinite(age)), 'omitnan');
    if all(~isfinite(age)), age(:) = 0.65; end
    female = double(T.FEMALE);
    female(~isfinite(female)) = 0;
    X = [score, score.^2, confidence, predicted, age, female];
end

function confidence = cmdo_u9_operating_confidence(score, threshold)
    p = min(1-eps, max(eps, double(score)));
    t = min(1-eps, max(eps, double(threshold)));
    margin = abs(log(p ./ (1-p)) - log(t/(1-t)));
    confidence = 1 ./ (1 + exp(-margin));
end

function threshold = cmdo_u9_atc_threshold(confidence, sourceAccuracy)
    q = min(1, max(0, 1-sourceAccuracy));
    threshold = quantile(confidence, q);
end

function threshold = cmdo_u9_youden_threshold(y, score)
    y = double(y(:)); score = double(score(:));
    [fpr, tpr, thresholds] = perfcurve(y, score, 1);
    J = tpr - fpr;
    finiteMask = isfinite(thresholds) & isfinite(J);
    if ~any(finiteMask)
        error('CMDO:U9:Threshold', 'No finite Youden threshold could be selected.');
    end
    idxFinite = find(finiteMask);
    [~, loc] = max(J(finiteMask));
    threshold = thresholds(idxFinite(loc));
end

function auc = cmdo_u9_auc(score, y)
    score = double(score(:)); y = double(y(:));
    ok = isfinite(score) & isfinite(y);
    score = score(ok); y = y(ok);
    if numel(unique(y)) < 2
        auc = NaN;
        return;
    end
    [~,~,~,auc] = perfcurve(y, score, 1);
end

function [lo, hi] = cmdo_u9_clopper_pearson(x, n, delta)
    if x == 0
        lo = 0;
    else
        lo = betainv(delta/2, x, n-x+1);
    end
    if x == n
        hi = 1;
    else
        hi = betainv(1-delta/2, x+1, n-x);
    end
end

function seed = cmdo_u9_derived_seed(masterSeed, hospitalIndex, replicate)
    seed = mod(double(masterSeed) + 1000003*double(hospitalIndex) + 7919*double(replicate), 2^31-1);
    if seed <= 0, seed = seed + 1; end
end

function path = cmdo_u9_locate_table(C, baseName)
    if ~isfolder(C.raw_root)
        error('CMDO:U9:RawRoot', ['eICU root not found: ' C.raw_root '. ' ...
            'Download the official credentialed eICU-CRD v2.0 files and set CMDO_EICU_ROOT or edit RUN_DATA_ADAPTER.m.']);
    end
    candidates = [dir(fullfile(C.raw_root, '**', [baseName '.csv'])); ...
                  dir(fullfile(C.raw_root, '**', [lower(baseName) '.csv'])); ...
                  dir(fullfile(C.raw_root, '**', [baseName '.csv.gz'])); ...
                  dir(fullfile(C.raw_root, '**', [lower(baseName) '.csv.gz']))];
    candidates = candidates(~[candidates.isdir]);
    if isempty(candidates)
        allFiles = dir(fullfile(C.raw_root, '**', '*'));
        allFiles = allFiles(~[allFiles.isdir]);
        target1 = lower([baseName '.csv']);
        target2 = lower([baseName '.csv.gz']);
        keep = strcmpi({allFiles.name}, target1) | strcmpi({allFiles.name}, target2);
        candidates = allFiles(keep);
    end
    if isempty(candidates)
        error('CMDO:U9:MissingTable', 'Could not find %s.csv or %s.csv.gz under %s.', baseName, baseName, C.raw_root);
    end
    paths = strings(numel(candidates),1);
    for i = 1:numel(candidates)
        paths(i) = string(fullfile(candidates(i).folder, candidates(i).name));
    end
    paths = unique(paths);
    if numel(paths) > 1
        error('CMDO:U9:AmbiguousTable', 'Multiple candidates found for %s: %s', baseName, strjoin(cellstr(paths), '; '));
    end
    path = char(paths(1));
end

function T = cmdo_u9_read_selected(C, path, requested)
    csvPath = cmdo_u9_materialize_csv(C, path);
    opts = detectImportOptions(csvPath, 'FileType', 'text', 'VariableNamingRule', 'preserve');
    available = string(opts.VariableNames);
    availableNorm = cmdo_u9_norm_names(available);
    requested = string(requested);
    requestedNorm = cmdo_u9_norm_names(requested);
    selected = strings(numel(requested),1);
    for i = 1:numel(requested)
        idx = find(availableNorm == requestedNorm(i), 1);
        if isempty(idx)
            error('CMDO:U9:Column', 'Required column %s was not found in %s.', requested(i), csvPath);
        end
        selected(i) = available(idx);
    end
    opts.SelectedVariableNames = cellstr(selected);
    T = readtable(csvPath, opts);
    canonical = cellstr(requestedNorm);
    T.Properties.VariableNames = canonical;
end

function csvPath = cmdo_u9_materialize_csv(C, path)
    pathString = string(path);
    if endsWith(lower(pathString), '.gz')
        [~, name, ext] = fileparts(char(pathString));
        outputName = name;
        if endsWith(lower(outputName), '.csv')
            outputName = outputName;
        else
            outputName = [outputName ext];
        end
        csvPath = fullfile(C.cache_dir, outputName);
        if ~isfile(csvPath)
            outputs = gunzip(char(pathString), C.cache_dir);
            csvPath = outputs{1};
        end
    else
        csvPath = char(pathString);
    end
end

function out = cmdo_u9_norm_names(names)
    out = lower(regexprep(string(names), '[^A-Za-z0-9]', ''));
end

function x = cmdo_u9_to_double(v)
    if isnumeric(v) || islogical(v)
        x = double(v);
    else
        x = str2double(string(v));
    end
end

function age = cmdo_u9_parse_age(v)
    s = upper(strtrim(string(v)));
    age = str2double(s);
    age(startsWith(s, '>')) = 90;
    age(age < 0 | age > 120) = NaN;
end

function version = cmdo_u9_parse_apache_version(v)
    s = upper(strtrim(string(v)));
    version = str2double(s);
    version(contains(s, 'IVA')) = 4;
    version(s == "IV") = 3;
end

function y = cmdo_u9_parse_mortality(v)
    s = upper(strtrim(string(v)));
    y = NaN(numel(s),1);
    y(s == "ALIVE") = 0;
    y(s == "EXPIRED" | s == "DEAD") = 1;
end

function cmdo_u9_assert_adapter_ready(C)
    required = {C.adapter_seal_path, C.roster_path, C.roles_path, ...
        C.development_outcome_path, C.reserve_vault_path};
    missing = required(~cellfun(@isfile, required));
    if ~isempty(missing)
        error('CMDO:U9:AdapterMissing', ['Run RUN_DATA_ADAPTER.m first. Missing: ' strjoin(missing, '; ')]);
    end
end

function cmdo_u9_require_nonempty(T, role)
    if isempty(T)
        error('CMDO:U9:RoleEmpty', 'The %s role has no finite development outcomes.', role);
    end
end

function J = cmdo_u9_config_for_json(C)
    J = struct();
    J.stage = C.stage;
    J.version = C.version;
    J.protocol_name = C.protocol_name;
    J.data_source = 'eICU Collaborative Research Database v2.0';
    J.apache_version = C.apache_version;
    J.minimum_age = C.minimum_age;
    J.minimum_hospital_roster = C.minimum_hospital_roster;
    J.role_counts = struct('source',C.source_hospitals,'history',C.history_hospitals, ...
        'calibration',C.calibration_hospitals,'reserve',C.reserve_hospitals);
    J.budgets = C.budgets;
    J.replicates = C.replicates;
    J.calibration_replicates = C.calibration_replicates;
    J.folds = C.folds;
    J.opposite_fold = C.opposite_fold;
    J.delta_family = C.delta_family;
    J.delta_block = C.delta_block;
    J.max_transport_weight = C.max_transport_weight;
    J.static_weight_grid = C.static_weight_grid;
    J.decision_guard_band = C.decision_guard_band;
    J.role_seed = C.role_seed;
    J.master_seed = C.master_seed;
    J.calibration_seed = C.calibration_seed;
    J.telemetry_pair_count = C.telemetry_pair_count;
    J.primary_metric = 'natural-prevalence fixed-threshold accuracy';
    J.primary_acceptance_rule = 'accuracy at least the median across historical hospitals';
    J.comparators = {'DIRECT','STATIC_HISTORICAL_BORROWING','ATC_STYLE', ...
        'PPI_PLUS_PLUS_STYLE_MEAN_CORRECTION','CMDO_GUARDED_OBSERVER'};
    J.restricted_data_rule = 'No row-level eICU data enter the shareable canonical ZIP.';
end

function cmdo_u9_selftest(C, verbose)
    rng(2026081099, 'twister');
    codeHash = cmdo_u9_sha256_file(C.code_path);
    assert(~isempty(regexp(codeHash, '^[0-9a-f]{64}$', 'once')), 'SHA-256 helper failed.');
    theta = 0.73;
    historical = 0.70;
    z = double(rand(256,1) < theta);
    [estimate, meanWeight, maxWeight, fallbackResidual, coverage, violations] = ...
        cmdo_u9_guarded_estimate(C, z, theta, historical);
    assert(isfinite(estimate), 'Guarded estimate is not finite.');
    assert(meanWeight >= 0 && maxWeight <= C.max_transport_weight + eps, 'Weight bounds failed.');
    assert(fallbackResidual < 1e-12, 'Exact fallback identity failed.');
    assert(islogical(coverage) || isnumeric(coverage), 'Coverage type failed.');
    assert(violations >= 0, 'Certificate count failed.');

    [ppi, lambda] = cmdo_u9_ppi_estimate(z, ones(size(z))*0.5, 0.5, 0, 1);
    assert(abs(ppi-mean(z)) < 1e-12 && lambda == 0, 'PPI constant-proxy fallback failed.');
    assert(cmdo_u9_true_state(0.8,0.75) == 1 && cmdo_u9_true_state(0.7,0.75) == -1, 'Truth-state rule failed.');
    assert(cmdo_u9_estimated_decision(0.8,0.75,0.01) == 1, 'Accept decision failed.');
    assert(cmdo_u9_estimated_decision(0.75,0.75,0.01) == 0, 'Unresolved decision failed.');

    seeds = zeros(C.reserve_hospitals*C.replicates,1);
    k = 0;
    for h = 1:C.reserve_hospitals
        for r = 1:C.replicates
            k = k+1; seeds(k) = cmdo_u9_derived_seed(C.master_seed,h,r);
        end
    end
    assert(numel(unique(seeds)) == numel(seeds), 'Derived seeds are not unique.');

    for n = [16 32 64]
        for x = 0:n
            [lo, hi] = cmdo_u9_clopper_pearson(x,n,C.delta_block);
            assert(lo >= 0 && hi <= 1 && lo <= hi, 'Clopper-Pearson interval failed.');
        end
    end
    if verbose
        selftest = struct();
        selftest.stage = C.stage;
        selftest.version = C.version;
        selftest.completed_at_singapore = cmdo_u9_timestamp();
        selftest.status = 'PASSED';
        selftest.code_sha256 = codeHash;
        selftest.synthetic_estimate = estimate;
        selftest.exact_fallback_residual = fallbackResidual;
        selftest.unique_frozen_seeds_checked = numel(seeds);
        cmdo_u9_write_json(fullfile(C.logs_dir, 'StageU9_SELFTEST_COMPLETE_v1_0.json'), selftest);
        fprintf('CMDO U9 SELFTEST PASSED\n');
        fprintf('Code SHA-256: %s\n', codeHash);
        fprintf('Synthetic estimate: %.6f\n', estimate);
        fprintf('Exact fallback residual: %.3g\n', fallbackResidual);
        fprintf('Unique frozen seeds checked: %d\n', numel(seeds));
    end
end

function rec = cmdo_u9_empty_history_record()
    rec = struct('hospital',"",'n',0,'prevalence',NaN,'accuracy',NaN,'auc',NaN);
end

function rec = cmdo_u9_empty_rep_record()
    rec = struct('hospital',"",'budget',0,'replicate',0,'seed',0,'target_n',0, ...
        'audit_positive_n',0,'audit_negative_n',0,'true_accuracy',NaN,'primary_floor',NaN, ...
        'true_state',0,'indifference_zone',false,'direct_estimate',NaN,'static_estimate',NaN, ...
        'atc_estimate',NaN,'ppi_estimate',NaN,'cmdo_estimate',NaN,'direct_abs_error',NaN, ...
        'static_abs_error',NaN,'atc_abs_error',NaN,'ppi_abs_error',NaN,'cmdo_abs_error',NaN, ...
        'cmdo_regret',NaN,'static_weight',NaN,'ppi_lambda',NaN,'mean_transport_weight',NaN, ...
        'max_transport_weight',NaN,'fallback_residual',NaN,'simultaneous_coverage',false, ...
        'covered_event_certificate_violations',0,'direct_decision',0,'static_decision',0, ...
        'atc_decision',0,'ppi_decision',0,'cmdo_decision',0);
end

function rec = cmdo_u9_empty_state_record()
    rec = struct('hospital',"",'budget',0,'target_n',0,'true_accuracy',NaN,'true_state',0, ...
        'direct_mae',NaN,'static_mae',NaN,'atc_mae',NaN,'ppi_mae',NaN,'cmdo_mae',NaN, ...
        'cmdo_regret',NaN,'relative_gain',NaN,'mean_transport_weight',NaN,'mean_ppi_lambda',NaN, ...
        'simultaneous_coverage',NaN,'covered_event_certificate_violations',0, ...
        'maximum_fallback_residual',NaN,'direct_correct_resolution_rate',NaN, ...
        'cmdo_correct_resolution_rate',NaN,'direct_false_assurance_rate',NaN, ...
        'cmdo_false_assurance_rate',NaN);
end

function rec = cmdo_u9_empty_hospital_record()
    rec = struct('hospital',"",'n',0,'prevalence',NaN,'true_accuracy',NaN,'true_auc',NaN, ...
        'historical_bias',NaN,'atc_estimate',NaN,'proxy_mean',NaN,'true_state',0, ...
        'lenient_state',0,'strict_state',0,'in_primary_indifference_zone',false);
end

function rec = cmdo_u9_gate(name, threshold, observed, passed, category)
    rec = struct('gate',string(name),'threshold',string(threshold),'observed',double(observed), ...
        'passed',logical(passed),'category',string(category));
end

function cmdo_u9_write_source_data_workbook(C, path, hospitals, states, methods, decisions, pairs, gates)
    template = fullfile(C.package_dir, 'SourceData_U9_Empty_Template_v1_0.xlsx');
    if isfile(path), delete(path); end
    if isfile(template)
        copyfile(template, path);
    else
        readme = table(["U9 source data";"Primary metric";"Primary decision";"Restricted data"], ...
            ["Hospital-level and aggregate result outputs"; ...
             "Natural-prevalence fixed-threshold accuracy"; ...
             "Acceptable if hospital accuracy is at least the historical-hospital median"; ...
             "No row-level eICU records are included"], ...
            'VariableNames', {'ITEM','VALUE'});
        writetable(readme, path, 'Sheet', 'README');
    end
    writetable(hospitals, path, 'Sheet', 'Hospital_Summary', 'Range', 'A1');
    writetable(states, path, 'Sheet', 'Budget_States', 'Range', 'A1');
    writetable(methods, path, 'Sheet', 'Method_Summary', 'Range', 'A1');
    writetable(decisions, path, 'Sheet', 'Decision_Summary', 'Range', 'A1');
    writetable(pairs, path, 'Sheet', 'Telemetry_Pairs', 'Range', 'A1');
    writetable(gates, path, 'Sheet', 'Gate_Table', 'Range', 'A1');
end

function cmdo_u9_write_figures(C, hospitals, states, methods, decisions, pairs, summary)
    colors = struct('direct',[0.20 0.20 0.20],'cmdo',[0.10 0.45 0.75], ...
        'static',[0.85 0.45 0.10],'atc',[0.55 0.35 0.70],'ppi',[0.20 0.65 0.45]);
    fig = figure('Color','w','Position',[80 80 1320 900]);
    tiledlayout(2,2,'Padding','compact','TileSpacing','compact');

    nexttile;
    scatter(hospitals.atc_estimate, hospitals.true_accuracy, 46, abs(hospitals.historical_bias), 'filled');
    hold on; lim = [min([hospitals.atc_estimate;hospitals.true_accuracy])-0.02, ...
        max([hospitals.atc_estimate;hospitals.true_accuracy])+0.02];
    plot(lim,lim,'k--','LineWidth',1); xline(median(hospitals.atc_estimate),'Color',[0.7 0.7 0.7]);
    yline(median(hospitals.true_accuracy),'Color',[0.7 0.7 0.7]);
    xlim(lim); ylim(lim); axis square; grid on;
    xlabel('ATC-style outcome-free estimate'); ylabel('True hospital accuracy');
    title('a  Telemetry alone can misstate deployment performance','FontWeight','bold');
    cb = colorbar; cb.Label.String = '|Historical transport bias|';

    nexttile;
    budgetList = unique(states.budget);
    methodNames = {'direct_mae','static_mae','atc_mae','ppi_mae','cmdo_mae'};
    labels = {'Direct','Static history','ATC','PPI++ style','CMDO'};
    methodColors = {colors.direct,colors.static,colors.atc,colors.ppi,colors.cmdo};
    for mi = 1:numel(methodNames)
        y = zeros(numel(budgetList),1);
        for bi = 1:numel(budgetList)
            y(bi) = mean(states.(methodNames{mi})(states.budget == budgetList(bi)));
        end
        plot(budgetList,y,'-o','LineWidth',1.8,'MarkerSize',5,'Color',methodColors{mi},'DisplayName',labels{mi}); hold on;
    end
    set(gca,'XScale','log','XTick',budgetList); grid on;
    xlabel('Screened cases'); ylabel('Mean absolute error');
    title(sprintf('b  Multicentre estimation (CMDO gain %.1f%%)',100*summary.relative_mae_gain),'FontWeight','bold');
    legend('Location','best','Box','off');

    nexttile;
    dDirect = decisions(decisions.method=="DIRECT",:);
    dCmdo = decisions(decisions.method=="CMDO",:);
    plot(dDirect.budget,dDirect.correct_resolution_rate,'-o','Color',colors.direct,'LineWidth',1.8,'DisplayName','Direct correct resolution'); hold on;
    plot(dCmdo.budget,dCmdo.correct_resolution_rate,'-o','Color',colors.cmdo,'LineWidth',1.8,'DisplayName','CMDO correct resolution');
    plot(dDirect.budget,dDirect.false_assurance_rate,'--s','Color',colors.direct,'LineWidth',1.5,'DisplayName','Direct false assurance');
    plot(dCmdo.budget,dCmdo.false_assurance_rate,'--s','Color',colors.cmdo,'LineWidth',1.5,'DisplayName','CMDO false assurance');
    set(gca,'XScale','log','XTick',budgetList); ylim([0 1]); grid on;
    xlabel('Screened cases'); ylabel('Rate');
    title(sprintf('c  Decision observability (cost reduction %.1f%%)',100*summary.decision_cost_reduction),'FontWeight','bold');
    legend('Location','best','Box','off');

    nexttile;
    x = abs(hospitals.historical_bias); y = hospitals.mean_transport_weight;
    scatter(x,y,54,colors.cmdo,'filled'); hold on;
    if numel(x) >= 2
        p = polyfit(x,y,1); xx = linspace(min(x),max(x),100); plot(xx,polyval(p,xx),'Color',colors.cmdo,'LineWidth',1.5);
    end
    grid on; xlabel('|Historical accuracy - target truth|'); ylabel('Mean transport weight');
    title(sprintf('d  Guard withdrawal (Spearman \\rho = %.2f)',summary.bias_weight_spearman),'FontWeight','bold');

    sgtitle('U9: sealed multicentre decision observability','FontWeight','bold');
    exportgraphics(fig, fullfile(C.results_dir,'Figure_U9_Multicentre_Decision_Observability_v1_0.pdf'),'ContentType','vector');
    exportgraphics(fig, fullfile(C.results_dir,'Figure_U9_Multicentre_Decision_Observability_v1_0.png'),'Resolution',300);
    close(fig);

    fig2 = figure('Color','w','Position',[100 100 1200 760]);
    tiledlayout(1,2,'Padding','compact','TileSpacing','compact');
    nexttile;
    bar(categorical(pairs.PAIR_ID), [pairs.TELEMETRY_DISTANCE pairs.TRUE_ACCURACY_GAP]);
    ylabel('Distance or absolute gap'); xlabel('Pre-outcome matched pair'); grid on;
    legend({'Telemetry distance','True accuracy gap'},'Location','best','Box','off');
    title('a  Outcome-free matched hospital pairs','FontWeight','bold');
    nexttile;
    hospitalOrder = categorical(states.hospital, unique(states.hospital,'stable'));
    M = NaN(numel(unique(states.hospital,'stable')),numel(budgetList));
    hList = unique(states.hospital,'stable');
    for hi = 1:numel(hList)
        for bi = 1:numel(budgetList)
            row = states(states.hospital==hList(hi) & states.budget==budgetList(bi),:);
            if ~isempty(row), M(hi,bi)=row.cmdo_regret(1); end
        end
    end
    imagesc(M); colorbar; colormap(parula); xticks(1:numel(budgetList)); xticklabels(string(budgetList));
    yticks(1:numel(hList)); yticklabels(hList); xlabel('Screened cases'); ylabel('Hospital');
    title('b  CMDO minus direct MAE','FontWeight','bold');
    sgtitle('U9 extended multicentre evidence','FontWeight','bold');
    exportgraphics(fig2, fullfile(C.results_dir,'ExtendedDataFigure_U9_Multicentre_v1_0.pdf'),'ContentType','vector');
    exportgraphics(fig2, fullfile(C.results_dir,'ExtendedDataFigure_U9_Multicentre_v1_0.png'),'Resolution',300);
    close(fig2);
end

function cmdo_u9_write_report(C, path, summary, methods, decisions, pairs, gates)
    lines = strings(0,1);
    lines(end+1) = "# CMDO U9 sealed multicentre decision-observability report";
    lines(end+1) = "";
    lines(end+1) = "**Frozen protocol:** " + string(C.protocol_name) + " (" + string(C.version) + ")";
    lines(end+1) = "";
    lines(end+1) = "**Canonical decision:** `" + string(summary.decision) + "`";
    lines(end+1) = "";
    lines(end+1) = "## Primary reserve summary";
    lines(end+1) = "";
    lines(end+1) = "- Evaluable reserve hospitals: " + string(summary.reserve_hospital_count) + ...
        " of " + string(summary.selected_reserve_hospital_count) + ".";
    lines(end+1) = sprintf('- Pooled direct MAE: %.6f.', summary.direct_mae);
    lines(end+1) = sprintf('- Pooled CMDO MAE: %.6f.', summary.cmdo_mae);
    lines(end+1) = sprintf('- Relative CMDO MAE gain: %.2f%%.', 100*summary.relative_mae_gain);
    lines(end+1) = sprintf('- Stable-decision cost reduction: %.2f%%.', 100*summary.decision_cost_reduction);
    lines(end+1) = sprintf('- Maximum hospital-budget CMDO regret: %.6f.', summary.worst_state_regret);
    lines(end+1) = sprintf('- Hospital noninferiority breadth: %.1f%%.', 100*summary.hospital_noninferiority_fraction);
    lines(end+1) = sprintf('- Mean/minimum simultaneous coverage: %.3f / %.3f.', ...
        summary.mean_simultaneous_coverage, summary.minimum_state_simultaneous_coverage);
    lines(end+1) = sprintf('- Covered-event certificate violations: %d.', ...
        summary.covered_event_certificate_violations);
    lines(end+1) = sprintf('- Maximum direct-fallback residual: %.3g.', summary.maximum_fallback_residual);
    lines(end+1) = sprintf('- Maximum outcome-free matched-pair accuracy gap after reveal: %.4f.', ...
        summary.maximum_matched_pair_accuracy_gap);
    lines(end+1) = "";
    lines(end+1) = "## Method comparison";
    lines(end+1) = "";
    lines(end+1) = "| Method | MAE | RMSE | Bias | Correct resolution | False assurance | Unresolved |";
    lines(end+1) = "|---|---:|---:|---:|---:|---:|---:|";
    for i = 1:height(methods)
        lines(end+1) = sprintf('| %s | %.6f | %.6f | %.6f | %.3f | %.3f | %.3f |', ...
            char(methods.method(i)), methods.mae(i), methods.rmse(i), methods.bias(i), ...
            methods.correct_resolution_rate(i), methods.false_assurance_rate(i), methods.unresolved_rate(i));
    end
    lines(end+1) = "";
    lines(end+1) = "## Decision summary by screened-case budget";
    lines(end+1) = "";
    lines(end+1) = "| Method | Budget | Correct resolution | False assurance | False rejection | Unresolved | Stable cost |";
    lines(end+1) = "|---|---:|---:|---:|---:|---:|---:|";
    for i = 1:height(decisions)
        lines(end+1) = sprintf('| %s | %d | %.3f | %.3f | %.3f | %.3f | %.1f |', ...
            char(decisions.method(i)), decisions.budget(i), decisions.correct_resolution_rate(i), ...
            decisions.false_assurance_rate(i), decisions.false_rejection_rate(i), ...
            decisions.unresolved_rate(i), decisions.stable_decision_cost(i));
    end
    lines(end+1) = "";
    lines(end+1) = "## Frozen gate table";
    lines(end+1) = "";
    lines(end+1) = "| Gate | Category | Threshold | Observed | Result |";
    lines(end+1) = "|---|---|---|---:|---|";
    for i = 1:height(gates)
        result = "FAIL";
        if gates.passed(i), result = "PASS"; end
        lines(end+1) = sprintf('| %s | %s | %s | %.6g | %s |', ...
            char(gates.gate(i)), char(gates.category(i)), char(gates.threshold(i)), ...
            gates.observed(i), char(result));
    end
    lines(end+1) = "";
    lines(end+1) = "## Matched-hospital witness";
    lines(end+1) = "";
    lines(end+1) = sprintf('%d hospital pairs were selected before reserve outcomes were opened using outcome-free telemetry only.', height(pairs));
    lines(end+1) = sprintf('After reveal, the median and maximum absolute true-accuracy gaps were %.4f and %.4f.', ...
        summary.median_matched_pair_accuracy_gap, summary.maximum_matched_pair_accuracy_gap);
    lines(end+1) = "";
    lines(end+1) = "## Interpretation boundary";
    lines(end+1) = "";
    lines(end+1) = ["Hospitals are deidentified deployment units in a retrospective database. " + ...
        "The blockwise certificate is interpreted under the prespecified patient-independence superpopulation model. " + ...
        "Aggregate MAE, decision efficiency and matched-pair contrasts are empirical reserve results, not a universal no-harm theorem."];
    lines(end+1) = "";
    lines(end+1) = "No row-level eICU record, target-score file, outcome vault, raw hospital identifier or patient identifier is included in the canonical shareable ZIP.";
    cmdo_u9_write_text(path, strjoin(lines, newline));
end

function cmdo_u9_copy_authority_files(C)
    codeDir = fullfile(C.canonical_dir, 'Protocol_and_Code');
    authorityDir = fullfile(C.canonical_dir, 'PreOutcome_Authority');
    resultDir = fullfile(C.canonical_dir, 'Results');
    for d = {codeDir, authorityDir, resultDir}
        if ~isfolder(d{1}), mkdir(d{1}); end
    end

    packageNames = { ...
        'CMDO_U9_eICU_Multicentre_Decision_Observability_v1_0.m', ...
        'RUN_SELFTEST.m', 'RUN_DATA_ADAPTER.m', 'RUN_PREPARE.m', 'RUN_UNSEAL.m', ...
        'README_U9_FIRST.md', 'StageU9_Protocol_v1_0.md', 'StageU9_Protocol_v1_0.docx', ...
        'StageU9_EXECUTION_AUTHORIZATION_TEMPLATE_v1_0.json', ...
        'U9_Results_Return_Checklist_v1_0.md', ...
        'U9_Chinese_Quickstart_v1_0.md', ...
        'U9_STATIC_QA_REPORT_v1_0.txt', ...
        'PACKAGE_MANIFEST_SHA256_v1_0.csv', ...
        'SourceData_U9_Empty_Template_v1_0.xlsx'};
    for i = 1:numel(packageNames)
        src = fullfile(C.package_dir, packageNames{i});
        if isfile(src), copyfile(src, fullfile(codeDir, packageNames{i})); end
    end

    authorityFiles = {C.adapter_seal_path, C.config_path, C.seal_path, C.authorization_path, ...
        fullfile(C.seal_dir, 'StageU9_AUTHORIZATION_REVIEW_RECORD_v1_0.json'), ...
        C.history_path, C.calibration_path, C.telemetry_path, C.telemetry_pairs_path};
    for i = 1:numel(authorityFiles)
        if isfile(authorityFiles{i})
            [~, name, ext] = fileparts(authorityFiles{i});
            copyfile(authorityFiles{i}, fullfile(authorityDir, [name ext]));
        end
    end

    resultListing = dir(C.results_dir);
    blocked = lower(["stageu9_witness_replicates_v1_0.csv"]);
    for i = 1:numel(resultListing)
        if resultListing(i).isdir, continue; end
        name = string(resultListing(i).name);
        if any(lower(name) == blocked), continue; end
        copyfile(fullfile(resultListing(i).folder, resultListing(i).name), ...
            fullfile(resultDir, resultListing(i).name));
    end
end

function cmdo_u9_write_manifest(C, manifestPath)
    listing = dir(fullfile(C.canonical_dir, '**', '*'));
    listing = listing(~[listing.isdir]);
    manifestName = string(manifestPath);
    rows = repmat(struct('RELATIVE_PATH',"",'BYTES',0,'SHA256',"",'CATEGORY',""), 0, 1);
    prefix = string(C.canonical_dir) + string(filesep);
    for i = 1:numel(listing)
        fullPath = string(fullfile(listing(i).folder, listing(i).name));
        if fullPath == manifestName, continue; end
        rel = erase(fullPath, prefix);
        rel = replace(rel, string(filesep), "/");
        parts = split(rel, "/");
        category = parts(1);
        if numel(parts) == 1, category = "Canonical_Root"; end
        rec = struct('RELATIVE_PATH',rel,'BYTES',double(listing(i).bytes), ...
            'SHA256',string(cmdo_u9_sha256_file(char(fullPath))),'CATEGORY',category);
        rows(end+1) = rec; %#ok<AGROW>
    end
    if isempty(rows)
        error('CMDO:U9:CanonicalEmpty', 'No canonical files were available for the durable manifest.');
    end
    T = sortrows(struct2table(rows), 'RELATIVE_PATH');
    writetable(T, manifestPath);
end

function zipPath = cmdo_u9_make_canonical_zip(C)
    if isfile(C.canonical_zip_path)
        error('CMDO:U9:CanonicalZipExists', ['Canonical ZIP already exists: ' C.canonical_zip_path ...
            '. Successful archive recreation is prohibited.']);
    end
    listing = dir(fullfile(C.canonical_dir, '**', '*'));
    listing = listing(~[listing.isdir]);
    if isempty(listing)
        error('CMDO:U9:CanonicalEmpty', 'Canonical directory is empty.');
    end
    prefix = string(C.canonical_dir) + string(filesep);
    rel = strings(numel(listing),1);
    forbidden = ["target_scores","reserve_outcome","development_outcomes", ...
        "hospital_and_case_mapping","restricted_do_not_share"];
    for i = 1:numel(listing)
        fullPath = string(fullfile(listing(i).folder, listing(i).name));
        rel(i) = erase(fullPath, prefix);
        low = lower(rel(i));
        if any(contains(low, forbidden))
            error('CMDO:U9:RestrictedCanonicalFile', ...
                'Restricted or row-level file was about to enter the canonical ZIP: %s', rel(i));
        end
    end
    zip(C.canonical_zip_path, cellstr(rel), C.canonical_dir);
    zipPath = C.canonical_zip_path;
end

function hash = cmdo_u9_optional_hash(path)
    if isfile(path)
        hash = cmdo_u9_sha256_file(path);
    else
        hash = 'NOT_PRESENT_AT_SEAL_TIME';
    end
end

function hash = cmdo_u9_sha256_file(path)
    if ~isfile(path)
        error('CMDO:U9:HashMissing', 'Cannot hash missing file: %s', path);
    end
    md = java.security.MessageDigest.getInstance('SHA-256');
    fid = fopen(path, 'r');
    if fid < 0, error('CMDO:U9:HashOpen', 'Cannot open file for hashing: %s', path); end
    cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
    while ~feof(fid)
        bytes = fread(fid, 1024*1024, '*uint8');
        if ~isempty(bytes), md.update(bytes); end
    end
    raw = md.digest();
    hash = lower(reshape(dec2hex(typecast(raw, 'uint8'), 2).', 1, []));
end

function cmdo_u9_write_json(path, value)
    try
        body = jsonencode(value, 'PrettyPrint', true);
    catch
        body = jsonencode(value);
    end
    cmdo_u9_write_text(path, body);
end

function cmdo_u9_write_text(path, body)
    parent = fileparts(path);
    if ~isempty(parent) && ~isfolder(parent), mkdir(parent); end
    fid = fopen(path, 'w', 'n', 'UTF-8');
    if fid < 0, error('CMDO:U9:Write', 'Cannot open file for writing: %s', path); end
    cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
    fprintf(fid, '%s\n', char(body));
end

function stamp = cmdo_u9_timestamp()
    stamp = char(string(datetime('now', 'TimeZone', 'Asia/Singapore', ...
        'Format', "yyyy-MM-dd'T'HH:mm:ssXXX")));
end

function cmdo_u9_assert_text_equal(actual, expected, label)
    actual = string(actual);
    expected = string(expected);
    if ~isscalar(actual) || ~isscalar(expected) || actual ~= expected
        error('CMDO:U9:AuthorityMismatch', '%s mismatch. Expected "%s" but found "%s".', ...
            label, expected, actual);
    end
end
