function Figure3_REUSE_Refined(outputDir, repoRoot, eicuResultDir)
% CMDO Figure 3 — REUSE
% A Frozen U6/U7 confirmation
% B Current-audit discrepancy tracks later-revealed historical mismatch
% C Post-completion fixed-use risk geometry across 185 completed states
% D Deferred sealed multicentre eICU replication
%
% IMPORTANT:
%   Panel D reads only SHARE-SAFE aggregate U9/eICU result tables.
%   It does not read the reserve-outcome vault and does not rerun U9.
%   The frozen 185-state synthesis in panel C remains unchanged.

close all;
thisFile=mfilename('fullpath');
if isempty(thisFile), scriptDir=pwd; else, scriptDir=fileparts(thisFile); end

if nargin<2 || isempty(repoRoot)
    repoRoot=local_find_repo(scriptDir);
end
if nargin<1 || isempty(outputDir)
    outputDir=fullfile(scriptDir,'output');
end
if nargin<3
    eicuResultDir='';
end

if ~isfolder(outputDir), mkdir(outputDir); end
assert(isfolder(repoRoot),'CMDO repository not found: %s',repoRoot);

addpath(scriptDir);
D=cmdo_submission_load(repoRoot);

FONT='Arial';
blue=[0.04 .30 .75];
green=[.02 .48 .20];
red=[.82 .08 .06];
dark=[.18 .18 .18];
grey=[.48 .48 .48];

%% ------------------------------------------------------------------------
% A/B source data: frozen U6/U7
% -------------------------------------------------------------------------

% U6 target gains
U6=D.u6_target;
u6gain=100*double(U6.gain_vs_full_direct)./double(U6.direct_mae);
u6pooled=100*(mean(double(D.u6_state.direct_mae))-mean(double(D.u6_state.mae))) ...
    /mean(double(D.u6_state.direct_mae));
u6gain=sort(u6gain,'descend');

% U7 AUC target gains
mc=local_find_var(D.u7_target,{'metric'});
U7=D.u7_target(string(D.u7_target.(mc))=="AUC",:);
u7gain=100*double(U7.gain)./double(U7.direct_mae);
u7gain=sort(u7gain,'descend');
mcM=local_find_var(D.u7_metric,{'metric'});
rr=find(string(D.u7_metric.(mcM))=="AUC",1);
u7pooled=100*double(D.u7_metric.relative_gain(rr));

% Largest-budget mismatch sensing
max6=max(double(D.u6_state.budget));
M6=D.u6_state(double(D.u6_state.budget)==max6,:);
x6=double(M6.mean_sensor_abs_gap);
y6=double(M6.transport_abs_error);
rho6=local_spearman(x6,y6);

mcS=local_find_var(D.u7_state,{'metric'});
S7=D.u7_state(string(D.u7_state.(mcS))=="AUC",:);
max7=max(double(S7.budget));
M7=S7(double(S7.budget)==max7,:);
x7=double(M7.mean_sensor_gap);
y7=double(M7.transport_abs_error);
rho7=local_spearman(x7,y7);

%% ------------------------------------------------------------------------
% C source data: frozen 185-state post-completion synthesis
% -------------------------------------------------------------------------

statePath=fullfile(repoRoot,'source_data','figure6_admissibility', ...
    'CMDO_Admissibility_State_MSE_Audit.csv');
assert(isfile(statePath),'Missing 185-state audit table: %s',statePath);

T=readtable(statePath,'VariableNamingRule','preserve');
stage=string(T.stage); %#ok<NASGU>
w=double(T.mean_weight);
lam=double(T.lambda_ean);
gain=double(T.mse_gain_pct);
benefit=gain>=0;

assert(height(T)==185, ...
    'Panel C must remain the frozen 185-state synthesis; found %d rows.',height(T));

%% ------------------------------------------------------------------------
% D source data: deferred sealed multicentre eICU replication
% -------------------------------------------------------------------------

eicuResultDir=local_find_eicu_result_dir(repoRoot,eicuResultDir);

hospitalPath=fullfile(eicuResultDir,'StageU9_Hospital_Summary_v1_0.csv');
gatePath=fullfile(eicuResultDir,'StageU9_Gate_Table_v1_0.csv');

assert(isfile(hospitalPath),'Missing eICU hospital summary: %s',hospitalPath);

H=readtable(hospitalPath,'VariableNamingRule','preserve');

requiredVars={'hospital','direct_mae','cmdo_mae','historical_bias','mean_transport_weight'};
for ii=1:numel(requiredVars)
    assert(ismember(requiredVars{ii},H.Properties.VariableNames), ...
        'eICU hospital summary is missing required variable: %s',requiredVars{ii});
end

assert(height(H)==20, ...
    'Panel D requires the sealed 20-hospital reserve; found %d hospitals.',height(H));

deltaMAE=1000*(double(H.cmdo_mae)-double(H.direct_mae));
[deltaMAE,ord]=sort(deltaMAE,'ascend');
hospitalOrder=string(H.hospital(ord)); %#ok<NASGU>

pooledDirect=mean(double(H.direct_mae),'omitnan');
pooledCMDO=mean(double(H.cmdo_mae),'omitnan');
eicuPooledGain=100*(pooledDirect-pooledCMDO)/pooledDirect;

eicuBreadth=sum(deltaMAE<=0);
eicuBreadthFrac=eicuBreadth/height(H);
eicuBreadthGate=0.75;

eicuGuardRho=local_spearman(abs(double(H.historical_bias)), ...
    double(H.mean_transport_weight));

% If the share-safe frozen gate table is present, verify that the plotted
% breadth agrees exactly with the one-shot record.
if isfile(gatePath)
    G=readtable(gatePath,'VariableNamingRule','preserve');
    gateName=string(G.gate);
    k=find(gateName=="hospital_breadth",1);
    if ~isempty(k)
        assert(abs(double(G.observed(k))-eicuBreadthFrac)<1e-12, ...
            'eICU breadth computed from hospital summary disagrees with frozen gate table.');
    end
end

%% ------------------------------------------------------------------------
% Figure
% -------------------------------------------------------------------------

fig=figure('Color','w','Position',[40 30 1180 800], ...
    'Renderer','painters', ...
    'Name','CMDO Figure 3 — REUSE', ...
    'NumberTitle','off');

t=tiledlayout(fig,2,2,'TileSpacing','loose','Padding','loose');

% -------------------------------------------------------------------------
% A: frozen confirmation
% -------------------------------------------------------------------------
ax=nexttile(t,1);
hold(ax,'on');

plot(ax,1:numel(u6gain),u6gain,'o-', ...
    'Color',blue,'MarkerFaceColor',blue, ...
    'LineWidth',1.0,'MarkerSize',4.5, ...
    'DisplayName',sprintf('Cross-domain, 16/16, +%.2f%%',u6pooled));

plot(ax,1:numel(u7gain),u7gain,'s-', ...
    'Color',green,'MarkerFaceColor',green, ...
    'LineWidth',1.0,'MarkerSize',4.5, ...
    'DisplayName',sprintf('Clinical, 16/16, +%.2f%%',u7pooled));

yline(ax,0,'--','Color',grey,'HandleVisibility','off');

xlabel(ax,'Target / stratum ordered by observed gain');
ylabel(ax,'Relative MAE gain (%)');
title(ax,'Frozen adaptive-observer confirmation','FontSize',11.5);

lgd=legend(ax,'Location','southwest','Box','off');
lgd.FontSize=8.1;

grid(ax,'on');
local_style(ax,FONT);
local_letter(fig,ax,'A',green);

% -------------------------------------------------------------------------
% B: mismatch sensing
% -------------------------------------------------------------------------
ax=nexttile(t,2);
hold(ax,'on');

scatter(ax,x6,y6,42,blue,'filled', ...
    'DisplayName',sprintf('Cross-domain, \\rho=%.2f',rho6));

scatter(ax,x7,y7,42,green,'s','filled', ...
    'DisplayName',sprintf('Clinical, \\rho=%.2f',rho7));

local_fitline(ax,x6,y6,blue);
local_fitline(ax,x7,y7,green);

xlabel(ax,'Current-audit discrepancy');
ylabel(ax,'Later-revealed |historical mismatch|');
title(ax,'Current outcomes sense historical mismatch','FontSize',11.5);

lgd=legend(ax,'Location','northwest','Box','off');
lgd.FontSize=8.1;

grid(ax,'on');
local_style(ax,FONT);
local_letter(fig,ax,'B',green);

% -------------------------------------------------------------------------
% C: frozen 185-state fixed-use geometry
% -------------------------------------------------------------------------
ax=nexttile(t,3);
hold(ax,'on');

scatter(ax,lam(benefit),w(benefit),28,green,'filled', ...
    'MarkerFaceAlpha',0.62,'DisplayName','Observed benefit');

scatter(ax,lam(~benefit),w(~benefit),54,red,'filled', ...
    'DisplayName','Observed harm');

L=logspace(-3,3,500);
wcrit=2./(1+L);

plot(ax,L,wcrit,'k--','LineWidth',1.45, ...
    'DisplayName','Fixed-use zero-gain boundary');

set(ax,'XScale','log');

positiveLam=lam(isfinite(lam) & lam>0);
xlo=max(1e-3,min(positiveLam)*0.7);
xhi=max(400,max(lam(isfinite(lam)))*1.1);

xlim(ax,[xlo xhi]);
ylim(ax,[0 max(.22,max(w)*1.15)]);

xlabel(ax,'Post-completion evidence-admissibility coordinate, \Lambda = B^2/V');
ylabel(ax,'Mean historical borrowing weight');
title(ax,'Fixed-use geometry across 185 completed states','FontSize',11.5);

lgd=legend(ax,'Location','northeast','Box','off');
lgd.FontSize=7.7;

grid(ax,'on');
local_style(ax,FONT);
local_letter(fig,ax,'C',gree);

% --------------------------------------------------------------------------
% D: NEW — sealed 20-hospital eICU replication
% -------------------------------------------------------------------------
ax=nexttile(t,4);
hold(ax,'on');

nH=numel(deltaMAE);
barColors=repmat(green,nH,1);
barColors(deltaMAE>0,:)=repmat(red,sum(deltaMAE>0),1);

b=bar(ax,1:nH,deltaMAE,0.78, ...
    'FaceColor','flat','EdgeColor','none');
b.CData=barColors;

yline(ax,0,'-','Color',dark,'LineWidth',0.9,'HandleVisibility','off');

% Visual guide: negative values favour CMDO; positive values favour direct.
yl=local_padded_ylim(deltaMAE,0.18);
ylim(ax,yl);

xlim(ax,[0.3 nH+0.7]);
xticks(ax,[1 5 10 15 20]);
xticklabels(ax,{'1','5','10','15','20'});

xlabel(ax,'Ordered reserve hospitals');
ylabel(ax,'MAE difference: CMDO - direct (\times10^{-3})');
title(ax,'Sealed multicentre eICU replication','FontSize',11.5);

summaryText=sprintf([ ...
    '20 reserve hospitals\n' ...
    'Pooled MAE gain  +%.2f%%\n' ...
    'Breadth  %d/20 = %.0f%%  (gate %.0f%%)\n' ...
    'Guard withdrawal  \\rho = %.2f'], ...
    eicuPooledGain,eicuBreadth,100*eicuBreadthFrac, ...
    100*eicuBreadthGate,eicuGuardRho);

text(ax,0.03,0.97,summaryText, ...
    'Units','normalized', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','top', ...
    'FontName',FONT, ...
    'FontSize',8.0, ...
    'Color',dark, ...
    'BackgroundColor','w', ...
    'Margin',4);

% Compact directional labels without creating extra legend clutter.
text(ax,0.98,0.06,'CMDO favoured', ...
    'Units','normalized','HorizontalAlignment','right', ...
    'VerticalAlignment','bottom','FontName',FONT, ...
    'FontSize',7.8,'Color',green);

text(ax,0.98,0.94,'Direct favoured', ...
    'Units','normalized','HorizontalAlignment','right', ...
    'VerticalAlignment','top','FontName',FONT, ...
    'FontSize',7.8,'Color',red);

grid(ax,'on');
local_style(ax,FONT);
local_letter(fig,ax,'D',green);

%% ------------------------------------------------------------------------
% Export
% -------------------------------------------------------------------------

png=fullfile(outputDir,'Figure3_REUSE_Refined.png');
pdf=fullfile(outputDir,'Figure3_REUSE_Refined.pdf');

exportgraphics(fig,png,'Resolution',300);
exportgraphics(fig,pdf,'ContentType','vector');

fprintf('\nFigure 3 written:\n%s\n%s\n',png,pdf);
fprintf('\nPanel D eICU source:\n%s\n',eicuResultDir);
fprintf(['eICU summary: pooled MAE gain %.4f%%; breadth %d/20 (%.1f%%); ' ...
    'guard Spearman rho %.4f.\n'], ...
    eicuPooledGain,eicuBreadth,100*eicuBreadthFrac,eicuGuardRho);
fprintf(['Panel C remains the original frozen 185-state synthesis; ' ...
    'eICU was NOT added to that pool.\n']);

end

%% =========================================================================
% Local helpers
% =========================================================================

function local_style(ax,FONT)
set(ax,'FontName',FONT,'FontSize',9.2,'LineWidth',.8, ...
    'TickDir','out','Box','off', ...
    'GridAlpha',0.14,'MinorGridAlpha',0.05, ...
    'XMinorGrid','off','YMinorGrid','off');
end

function local_letter(fig,ax,s,c)
drawnow;
p=ax.Position;
x=max(0.006,p(1)-0.033);
y=min(0.938,p(2)+p(4)+0.004);

annotation(fig,'textbox',[x y 0.030 0.035], ...
    'String',s,'LineStyle','none','FitBoxToText','on', ...
    'FontName','Arial','FontSize',14,'FontWeight','bold', ...
    'Color',c,'HorizontalAlignment','left', ...
    'VerticalAlignment','bottom');
end

function local_fitline(ax,x,y,c)
m=isfinite(x)&isfinite(y);
x=x(m);
y=y(m);
if numel(x)<2, return; end

p=polyfit(x,y,1);
xx=linspace(min(x),max(x),100);

plot(ax,xx,polyval(p,xx),'-', ...
    'Color',c,'LineWidth',1.3,'HandleVisibility','off');
end

function rho=local_spearman(x,y)
x=x(:);
y=y(:);
m=isfinite(x)&isfinite(y);
x=x(m);
y=y(m);

rx=local_rank(x);
ry=local_rank(y);

rho=corr(rx,ry,'Rows','complete');
end

function r=local_rank(x)
[~,o]=sort(x);
r=zeros(size(x));

i=1;
while i<=numel(x)
    j=i;
    while j<numel(x) && x(o(j+1))==x(o(i))
        j=j+1;
    end
    r(o(i:j))=(i+j)/2;
    i=j+1;
end
end

function name=local_find_var(T,candidates)
name='';
vars=T.Properties.VariableNames;
nv=cellfun(@(x)lower(regexprep(x,'[^a-zA-Z0-9]','')), ...
    vars,'UniformOutput',false);

for i=1:numel(candidates)
    c=lower(regexprep(candidates{i},'[^a-zA-Z0-9]',''));
    k=find(strcmp(nv,c),1);
    if ~isempty(k)
        name=vars{k};
        return;
    end
end

error('Could not find required variable: %s',strjoin(candidates,', '));
end

function resultDir=local_find_eicu_result_dir(repoRoot,userDir)
% Locate SHARE-SAFE aggregate eICU result tables.
% The submission renderer defaults only to repository-relative source data.
% An explicit userDir is permitted for local verification, but no author-
% machine absolute path is embedded in the frozen renderer.

required='StageU9_Hospital_Summary_v1_0.csv';

candidates={};
if nargin>=2 && strlength(string(userDir))>0
    candidates{end+1}=char(userDir); %#ok<AGROW>
end
candidates{end+1}=fullfile(repoRoot,'source_data','figure3_eicu');

for i=1:numel(candidates)
    p=candidates{i};
    if isfolder(p) && isfile(fullfile(p,required))
        resultDir=p;
        return;
    end
end

error('CMDO:Figure3:eICUResultsNotFound', ...
    ['Could not locate share-safe eICU aggregate result tables. ' ...
     'Expected repository-relative directory: %s'], ...
    fullfile(repoRoot,'source_data','figure3_eicu'));
end

function repoRoot=local_find_repo(scriptDir)
% submission_figures lives at <repo>/matlab/submission_figures.
repoRoot=fileparts(fileparts(scriptDir));
assert(isfile(fullfile(repoRoot,'README.md')), ...
    'Could not resolve repository root from renderer location.');
end

function yl=local_padded_ylim(y,padFrac)
y=y(isfinite(y));
if isempty(y)
    yl=[-1 1];
    return;
end

lo=min([0; y(:)]);
hi=max([0; y(:)]);

span=hi-lo;
if span<=0
    span=max(1,abs(hi));
end

yl=[lo-padFrac*span, hi+padFrac*span];
end
