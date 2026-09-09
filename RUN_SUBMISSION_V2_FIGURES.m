function RUN_CMDO_PCC_FIGURES(varargin)
p=inputParser;
addParameter(p,'RepoRoot',fullfile(getenv('USERPROFILE'),'CMDO-Reproducibility'),@(x)ischar(x)||isstring(x));
addParameter(p,'OutDir','',@(x)ischar(x)||isstring(x));
addParameter(p,'Strict',true,@(x)islogical(x)||isnumeric(x));
parse(p,varargin{:}); opt=p.Results;
thisFile=mfilename('fullpath'); root=fileparts(thisFile); matdir=fullfile(root,'matlab'); pccdir=fullfile(root,'source_data','pcc'); addpath(matdir);
repo=char(opt.RepoRoot); assert(isfolder(repo),'CMDO repository not found: %s',repo);
if strlength(string(opt.OutDir))==0, out=fullfile(root,'output'); else, out=char(opt.OutDir); end
if isfolder(out), try, rmdir(out,'s'); catch, end; end; if ~isfolder(out), mkdir(out); end
names=["Figure1";"Figure2_IDENTIFY";"Figure3_REUSE";"Figure4_CERTIFY";"Figure5_PRESERVE";"ED1";"ED2";"ED3"];
status=strings(8,1); msg=strings(8,1); sec=zeros(8,1);
for i=1:8
    tic;
    try
        switch i
            case 1, Figure1_Evidential_Order_PCC(out,repo);
            case 2, Figure2_IDENTIFY_Validation(out,repo);
            case 3, Figure3_REUSE_Refined(out,repo);
            case 4, Figure4_CERTIFY(out,pccdir);
            case 5, Figure5_PRESERVE_PCC(out,repo,pccdir);
            case 6, ED1_OutcomeFreeBoundary_v9(out,repo);
            case 7, ED2_IntegrityControls_v2(out,repo);
            case 8, ED3_RobustnessEfficiency_v1('CSVPath',fullfile(repo,'source_data','figure5_submission','CMDO_SystemStress_AUC_StateSummary_v1_1.csv'),'OutDir',out);
        end
        status(i)="PASS";
    catch ME
        status(i)="FAIL"; msg(i)=string(ME.message); if logical(opt.Strict), rethrow(ME); end
    end
    sec(i)=toc;
end
summary=table(names,status,sec,msg,'VariableNames',{'figure','status','seconds','message'}); disp(summary);
expected={ ...
'Figure1_Evidential_Order_PCC';'Figure2_IDENTIFY_Validation';'Figure3_REUSE_Refined';'Figure4_CERTIFY';'Figure5_PRESERVE_PCC';'ED1_OutcomeFreeBoundary_v9';'ED2_IntegrityControls_v2';'ED3_RobustnessEfficiency_v1'};
for i=1:numel(expected)
    assert(isfile(fullfile(out,[expected{i} '.png'])),'Missing PNG: %s',expected{i});
    assert(isfile(fullfile(out,[expected{i} '.pdf'])),'Missing PDF: %s',expected{i});
end
fprintf('\n============================================================\n');
fprintf(' CMDO SUBMISSION V2 FIGURES COMPLETE: %d/8 PASS\n',sum(status=="PASS"));
fprintf(' Output: %s\n',out);
fprintf(' Repository was read only; no files were written into it.\n');
fprintf('============================================================\n');
end
