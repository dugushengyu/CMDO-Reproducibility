function CMDO_Figure6_U8_U9_OperationalBoundary(sourceDir, outputDir)
%CMDO_FIGURE6_U8_U9_OPERATIONALBOUNDARY Final U8/U9 operational figure.
% Reads share-safe CSV/JSON source data only. No raw patient data are used.

if nargin < 1 || strlength(string(sourceDir)) == 0
    here = fileparts(mfilename('fullpath'));
    repo = fileparts(fileparts(fileparts(here)));
    sourceDir = fullfile(repo,'source_data','figure6_u8_u9');
end
if nargin < 2 || strlength(string(outputDir)) == 0
    here = fileparts(mfilename('fullpath'));
    repo = fileparts(fileparts(fileparts(here)));
    outputDir = fullfile(repo,'outputs','figures','main');
end
if ~isfolder(outputDir), mkdir(outputDir); end

U8 = readtable(fullfile(sourceDir,'U8_state.csv'),'TextType','string');
U8C = readtable(fullfile(sourceDir,'U8_cycles.csv'),'TextType','string');
U9A = readtable(fullfile(sourceDir,'U9A_targets.csv'),'TextType','string');
U9B = readtable(fullfile(sourceDir,'U9B_states.csv'),'TextType','string');
S9A = jsondecode(fileread(fullfile(sourceDir,'U9A_summary.json')));
S9B = jsondecode(fileread(fullfile(sourceDir,'U9B_summary.json')));

fig = figure('Color','w','Position',[40 25 920 1050],'Renderer','painters', ...
    'Name','CMDO Figure 6','NumberTitle','off');
tl=tiledlayout(fig,3,2,'TileSpacing','compact','Padding','compact');
title(tl,'Operational confirmation and the external boundary of guarded evidence reuse', ...
    'FontWeight','bold','FontSize',15);

% a U8 natural-prevalence trajectories
ax=nexttile; hold(ax,'on');
cycles=unique(U8.cycle,'stable');
mk={'o','s','^'};
for i=1:numel(cycles)
    T=sortrows(U8(U8.cycle==cycles(i),:),'budget');
    plot(ax,T.budget,T.observer_mae,['-' mk{i}],'LineWidth',1.6,'DisplayName','Observer');
    plot(ax,T.budget,T.direct_mae,['--' mk{i}],'LineWidth',1.0,'HandleVisibility','off');
end
set(ax,'XScale','log'); xticks(ax,[128 256 512 1024]); xticklabels(ax,{'128','256','512','1024'});
xlabel(ax,'Screened-case budget'); ylabel(ax,'Accuracy MAE'); grid(ax,'on');
title(ax,'U8: natural-prevalence temporal reserve','FontWeight','bold');
text(ax,0.03,0.95,'12/12 states improved; pooled reduction 10.07%','Units','normalized', ...
    'VerticalAlignment','top','FontWeight','bold','BackgroundColor','w');

% b U8 mismatch vs weight
ax=nexttile; hold(ax,'on');
x=100*abs(U8C.historical_accuracy_bias); y=U8C.mean_weight;
plot(ax,x,y,'-o','LineWidth',1.2,'MarkerFaceColor','auto');
for i=1:height(U8C), text(ax,x(i)+0.04,y(i),erase(U8C.cycle(i),'NHANES_'),'FontSize',7); end
xlabel(ax,'Historical-target accuracy mismatch (percentage points)'); ylabel(ax,'Mean transport weight'); grid(ax,'on');
title(ax,'U8: borrowing adapts while certification holds','FontWeight','bold');
text(ax,0.03,0.08,'coverage mean/min 0.968/0.940; 0 violations; fallback 0','Units','normalized', ...
    'FontWeight','bold','BackgroundColor','w');

% c U9A centres
ax=nexttile; hold(ax,'on');
order=["hungary","switzerland","va_long_beach"];
labels={'Hungary','Switzerland','VA Long Beach'};
for i=1:3
    r=U9A(U9A.target==order(i),:);
    plot(ax,[r.direct_mae r.observer_mae],[i i],'-','Color',[.7 .7 .7]);
    plot(ax,r.direct_mae,i,'o','MarkerFaceColor','w','MarkerEdgeColor',[.25 .25 .25]);
    plot(ax,r.observer_mae,i,'s','MarkerFaceColor',[.2 .5 .8],'MarkerEdgeColor','w');
    text(ax,max(r.direct_mae,r.observer_mae)+0.001,i,sprintf('%+.2f%%',100*r.relative_gain),'FontWeight','bold');
end
yticks(ax,1:3); yticklabels(ax,labels); set(ax,'YDir','reverse'); xlabel(ax,'Pooled accuracy MAE'); grid(ax,'on');
title(ax,'U9A: multicentre bridge becomes heterogeneous','FontWeight','bold');
text(ax,0.03,0.08,'2/3 centres improved; pooled change -0.11%','Units','normalized','FontWeight','bold','BackgroundColor','w');

% d U9B source-target shift
ax=nexttile; hold(ax,'on');
a=[S9B.source.system_A_prevalence,S9B.source.historical_auc,S9B.source.historical_accuracy];
b=[S9B.source.system_B_prevalence,S9B.source.target_auc,S9B.true_accuracy];
for i=1:3
    plot(ax,[a(i) b(i)],[i i],'-','Color',[.72 .72 .72],'LineWidth',1.4);
    plot(ax,a(i),i,'o','MarkerFaceColor',[.2 .5 .8],'MarkerEdgeColor','w');
    plot(ax,b(i),i,'s','MarkerFaceColor',[.95 .45 .1],'MarkerEdgeColor','w');
    text(ax,max(a(i),b(i))+0.025,i,sprintf('\\Delta %+.3f',b(i)-a(i)),'FontWeight','bold');
end
yticks(ax,1:3); yticklabels(ax,{'Prevalence','AUC','Accuracy'}); set(ax,'YDir','reverse'); xlim(ax,[0 .9]); grid(ax,'on');
xlabel(ax,'Value'); title(ax,'U9B: strong external hospital-system mismatch','FontWeight','bold');
text(ax,0.98,0.08,'historical accuracy bias = -0.132; AUC 0.757 -> 0.574','Units','normalized', ...
    'HorizontalAlignment','right','FontWeight','bold','BackgroundColor','w');

% e U9B MAE trajectory + weight
ax=nexttile; hold(ax,'on'); T=sortrows(U9B,'budget');
plot(ax,T.budget,T.direct_mae,'--o','LineWidth',1.2,'DisplayName','Same-budget direct');
plot(ax,T.budget,T.observer_mae,'-s','LineWidth',1.7,'DisplayName','Guarded observer');
set(ax,'XScale','log'); xticks(ax,[128 256 512 1024]); xticklabels(ax,{'128','256','512','1024'});
xlabel(ax,'Screened-case budget'); ylabel(ax,'Accuracy MAE'); grid(ax,'on');
title(ax,'U9B: integrity survives, pooled efficiency does not','FontWeight','bold'); legend(ax,'Location','northeast','Box','off');
yyaxis(ax,'right'); plot(ax,T.budget,T.mean_weight,'-^','LineWidth',1.0); ylabel(ax,'Mean weight');
yyaxis(ax,'left');
text(ax,0.03,0.08,'pooled change -3.67%; worst budget-mean regret 0.00105','Units','normalized','FontWeight','bold','BackgroundColor','w');

% f boundary profile
ax=nexttile; hold(ax,'on');
vals=[10.0728;100*S9A.pooled_relative_gain;100*S9B.relative_gain];
barh(ax,1:3,vals); xline(ax,0,'k-'); yticks(ax,1:3); yticklabels(ax,{'U8 pooled','U9A pooled','U9B pooled'}); set(ax,'YDir','reverse');
for i=1:3, text(ax,vals(i)+(0.25*sign(vals(i))),i,sprintf('%+.2f%%',vals(i)),'FontWeight','bold', ...
        'HorizontalAlignment', tern(vals(i)>=0,'left','right')); end
xlabel(ax,'Relative MAE change versus same-budget direct (%)'); grid(ax,'on');
title(ax,'From beneficial reuse to an external admissibility boundary','FontWeight','bold');
text(ax,0.98,0.08,'U9B coverage 0.970/0.945; 0 violations; fallback 0; slope -0.496', ...
    'Units','normalized','HorizontalAlignment','right','FontWeight','bold','BackgroundColor','w');

letters='abcdef';
for i=1:6
    a=nexttile(tl,i); text(a,-0.12,1.06,letters(i),'Units','normalized','FontWeight','bold','FontSize',12);
end

exportgraphics(fig,fullfile(outputDir,'Figure6_U8_U9_OperationalBoundary.png'),'Resolution',300);
exportgraphics(fig,fullfile(outputDir,'Figure6_U8_U9_OperationalBoundary.pdf'),'ContentType','vector');
close(fig);
end

function out=tern(tf,a,b)
if tf, out=a; else, out=b; end
end
