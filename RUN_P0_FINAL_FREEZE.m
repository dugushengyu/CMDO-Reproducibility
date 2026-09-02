function report = RUN_P0_FINAL_FREEZE(varargin)
%RUN_P0_FINAL_FREEZE Final acceptance gate for the CMDO submission package.
%
% Required order:
%   1) generate provenance/submission_final_manifest_v1.csv once with
%      python scripts/build_submission_final_manifest.py
%   2) commit that manifest;
%   3) run this function from a clean checkout;
%   4) only after PASS, merge/tag the exact tested commit.

p=inputParser;
addParameter(p,'Strict',true,@(x)islogical(x)||isnumeric(x));
addParameter(p,'RunStressReplay',true,@(x)islogical(x)||isnumeric(x));
parse(p,varargin{:});
strict=logical(p.Results.Strict);

repoRoot=fileparts(mfilename('fullpath'));
report=struct();

fprintf('\n============================================================\n');
fprintf(' CMDO FINAL P0 REPRODUCIBILITY FREEZE\n');
fprintf('============================================================\n');

%% 1. P0-specific input checks
fprintf('\n[1/4] P0 scientific-source integrity\n');
report.p0=VERIFY_P0_SUBMISSION_INPUTS('Strict',strict);

%% 2. Final SHA-256 manifest
fprintf('\n[2/4] Final submission SHA-256 manifest\n');
manifest=fullfile(repoRoot,'provenance','submission_final_manifest_v1.csv');
assert(isfile(manifest),[ ...
    'Missing provenance/submission_final_manifest_v1.csv. ' ...
    'Generate it once with: python scripts/build_submission_final_manifest.py, ' ...
    'then commit it before running the final acceptance gate.']);
M=readtable(manifest,'TextType','string','VariableNamingRule','preserve');
verified=false(height(M),1);
for i=1:height(M)
    rel=char(M.path(i));
    rel=strrep(rel,'\',filesep); rel=strrep(rel,'/',filesep);
    pth=fullfile(repoRoot,rel);
    verified(i)=isfile(pth) && strcmpi(local_sha256(pth),char(M.sha256(i)));
    fprintf('  %-76s %s\n',rel,string(verified(i)));
end
report.finalManifestEntries=height(M);
report.finalManifestVerified=nnz(verified);
report.finalManifestPass=all(verified);
if strict, assert(all(verified),'Final submission manifest verification failed.'); end

%% 3. Existing reviewer end-to-end audit
fprintf('\n[3/4] Reviewer end-to-end audit\n');
report.reviewer=RUN_REVIEWER_END_TO_END('Strict',strict, ...
    'RunStressReplay',logical(p.Results.RunStressReplay));

%% 4. Git-clean acceptance
fprintf('\n[4/4] Exact tested-worktree status\n');
report.gitAvailable=false; report.gitClean=NaN; report.head='';
[st,~]=system('git --version');
if st==0 && isfolder(fullfile(repoRoot,'.git'))
    report.gitAvailable=true;
    [~,head]=system(sprintf('git -C "%s" rev-parse HEAD',repoRoot));
    report.head=strtrim(head);
    [gst,porcelain]=system(sprintf('git -C "%s" status --porcelain',repoRoot));
    if gst==0, report.gitClean=isempty(strtrim(porcelain)); end
end
if strict && report.gitAvailable
    assert(report.gitClean==1,'Final checkout is not Git-clean.');
end

report.pass=report.p0.pass && report.finalManifestPass && ...
    report.reviewer.fullPortableAuditPass && (~report.gitAvailable || report.gitClean==1);

fprintf('\n============================================================\n');
fprintf(' FINAL P0 FREEZE SUMMARY\n');
fprintf('============================================================\n');
fprintf('P0 scientific-source integrity : %s\n',string(report.p0.pass));
fprintf('Final SHA-256 manifest          : %d/%d\n',report.finalManifestVerified,report.finalManifestEntries);
fprintf('Reviewer portability audit      : %s\n',string(report.reviewer.fullPortableAuditPass));
fprintf('Git clean                       : %s\n',string(report.gitClean));
fprintf('Tested HEAD                     : %s\n',string(report.head));
fprintf('FINAL P0 FREEZE                 : %s\n',string(report.pass));
fprintf('============================================================\n\n');

if strict, assert(report.pass,'Final P0 reproducibility freeze did not pass.'); end
end

function out=local_sha256(path)
md=java.security.MessageDigest.getInstance('SHA-256');
fid=fopen(path,'rb'); assert(fid>=0,'Cannot open %s',path);
c=onCleanup(@()fclose(fid));
while true
    b=fread(fid,1024*1024,'*uint8');
    if isempty(b), break; end
    md.update(typecast(b,'int8'));
end
d=typecast(md.digest(),'uint8');
out=lower(reshape(dec2hex(d,2).',1,[]));
end
