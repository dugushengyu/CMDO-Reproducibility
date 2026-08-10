function D = cmdo_load_all(cfg)
%CMDO_LOAD_ALL Load the frozen U4C-U7 tables used by manuscript figures.

if nargin < 1 || isempty(cfg)
    cfg = cmdo_config('all');
end

u4 = cmdo.extract_canonical(cfg, 'StageU4C_Canonical_Records_v1.1.zip');
u5b = cmdo.extract_canonical(cfg, 'StageU5B_Canonical_Records_v1.0.zip');
u5d = cmdo.extract_canonical(cfg, 'StageU5D_Canonical_Records_v1.0.zip');
u5e = cmdo.extract_canonical(cfg, 'StageU5E_Canonical_Records_v1.0.zip');
u5f = cmdo.extract_canonical(cfg, 'StageU5F_Canonical_Records_v1.0.zip');
u6 = cmdo.extract_canonical(cfg, 'StageU6_Canonical_Records_v1.0.zip');
u7 = cmdo.extract_canonical(cfg, 'StageU7_Canonical_Records_v1.0.zip');

D = struct();
D.u4c_fits = cmdo.read_canonical_table(u4, 'StageU4C_Component_Fits_v1.1.csv');
D.u4c_pred = cmdo.read_canonical_table(u4, 'StageU4C_Component_Trajectory_Predictions_v1.1.csv');
D.u5b_state = cmdo.read_canonical_table(u5b, 'StageU5B_Audit_State_Results_v1.0.csv');
D.u5d_state = cmdo.read_canonical_table(u5d, 'StageU5D_Raw_Sample_Crossfit_State_Results_v1.0.csv');
D.u5d_summary = cmdo.read_canonical_table(u5d, 'StageU5D_Method_Summary_v1.0.csv');
D.u5e_state = cmdo.read_canonical_table(u5e, 'StageU5E_Pair_Complete_State_Results_v1.0.csv');
D.u5e_summary = cmdo.read_canonical_table(u5e, 'StageU5E_Method_Summary_v1.0.csv');
D.u5f_audit = cmdo.read_canonical_table(u5f, 'StageU5F_Candidate_Selection_Audit_v1.0.csv');
D.u6_rep = cmdo.read_canonical_table(u6, 'StageU6_Pair_Complete_Witness_Replicates_v1.0.csv.gz');
D.u6_state = cmdo.read_canonical_table(u6, 'StageU6_Audit_State_Results_v1.0.csv');
D.u6_target = cmdo.read_canonical_table(u6, 'StageU6_Target_Summary_v1.0.csv');
D.u7_rep = cmdo.read_canonical_table(u7, 'StageU7_Witness_Replicates_v1.0.csv.gz');
D.u7_state = cmdo.read_canonical_table(u7, 'StageU7_State_Results_v1.0.csv');
D.u7_target = cmdo.read_canonical_table(u7, 'StageU7_Target_Metric_Summary_v1.0.csv');
D.u7_metric = cmdo.read_canonical_table(u7, 'StageU7_Metric_Summary_v1.0.csv');
D.u7_rates = cmdo.read_canonical_table(u7, 'StageU7_Label_Complexity_Rates_v1.0.csv');
end
