function stageDir = extract_canonical(cfg, archiveName)
%EXTRACT_CANONICAL Extract a canonical ZIP to a content-addressed cache.

archivePath = cmdo.find_unique_file(cfg.canonicalRecordDir, archiveName);
archiveHash = cmdo.sha256_file(archivePath);
[~, stem] = fileparts(archiveName);
stageDir = fullfile(cfg.cacheRoot, 'canonical_records', ...
    sprintf('%s_%s', stem, archiveHash(1:12)));
readyPath = fullfile(stageDir, '.ready');

if ~isfile(readyPath)
    if ~isfolder(stageDir)
        mkdir(stageDir);
    end
    unzip(archivePath, stageDir);
    fid = fopen(readyPath, 'w');
    if fid < 0
        error('CMDO:WriteFailed', 'Could not create cache marker: %s', readyPath);
    end
    cleanup = onCleanup(@() fclose(fid));
    fprintf(fid, '%s\n', archiveHash);
end
end
