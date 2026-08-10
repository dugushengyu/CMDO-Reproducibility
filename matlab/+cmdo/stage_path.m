function path = stage_path(stage)
%STAGE_PATH Resolve the isolated directory for a native MATLAB stage.

root = cmdo.repo_root();
stage = upper(string(stage));
switch stage
    case "U8_V1_1"
        path = fullfile(root, 'matlab', 'stages', 'u8', 'v1_1_canonical');
    case "U8_V1_0"
        path = fullfile(root, 'matlab', 'stages', 'u8', 'v1_0_preoutcome');
    case "U9_V1_0"
        path = fullfile(root, 'matlab', 'stages', 'u9', 'v1_0_preoutcome');
    otherwise
        error('CMDO:UnknownStage', 'Unknown native MATLAB stage: %s', stage);
end
end
