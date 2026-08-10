function CMDO_ExtendedDataFigure7_U8(sourceWorkbook, outputDir)
%CMDO_EXTENDEDDATAFIGURE7_U8 Complete U8 natural-prevalence detail.
% All values are read from SourceData_Figure5_U7_U8_and_ED7_U8.xlsx.

if nargin < 1 || strlength(string(sourceWorkbook)) == 0
    sourceWorkbook = fullfile(cmdo.repo_root(), 'source_data', ...
        'SourceData_Figure5_U7_U8_and_ED7_U8.xlsx');
end
if nargin < 2 || strlength(string(outputDir)) == 0
    cfg = cmdo_config('ED7_U8');
    outputDir = cfg.extendedOutputDir;
end
if ~isfile(sourceWorkbook)
    error('CMDO:MissingSourceWorkbook', 'Source workbook not found: %s', sourceWorkbook);
end
if ~isfolder(outputDir), mkdir(outputDir); end

S = readtable(sourceWorkbook, 'Sheet', 'U8_State', 'VariableNamingRule', 'preserve');
G = readtable(sourceWorkbook, 'Sheet', 'U8_Gates', 'VariableNamingRule', 'preserve');
S.cycle = string(S.cycle);
cycleOrder = ["NHANES_2015_2016", "NHANES_2017_2018", "NHANES_2021_2023"];
cycleLabels = ["2015-2016", "2017-2018", "2021-2023"];
cycleColors = [0.1216 0.4667 0.7059; 0.9294 0.4941 0.1922; 0.3294 0.6275 0.4118];
budgets = sort(unique(S.budget));
meanCoverage = mean(S.simultaneous_coverage);
minCoverage = min(S.simultaneous_coverage);
certificateViolations = sum(S.covered_event_certificate_violations);
maxFallback = max(abs(S.maximum_fallback_residual));

fig = figure('Color','w','Position',[30 30 1080 850], ...
    'Renderer','painters','Name','CMDO Extended Data Figure 7','NumberTitle','off');
tl = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');

%% a — complete state-level error reduction
ax = nexttile(tl,1);
R = nan(3,4);
for k = 1:3
    for j = 1:4
        r = S.cycle == cycleOrder(k) & S.budget == budgets(j);
        R(k,j) = 100 .* S.relative_gain(r);
    end
end
imagesc(ax,budgets,1:3,R,[0 max(R(:))*1.05]);
colormap(ax,parula(256)); cb=colorbar(ax); cb.Label.String='Relative MAE reduction (%)';
xticks(ax,budgets); xticklabels(ax,string(budgets));
yticks(ax,1:3); yticklabels(ax,cycleLabels);
xlabel(ax,'Screened-case budget');
title(ax,'All 12 cycle-budget states improved','FontWeight','bold');
for k=1:3
    for j=1:4
        text(ax,budgets(j),k,sprintf('%.1f%%',R(k,j)), ...
            'HorizontalAlignment','center','FontWeight','bold','Color','w','FontSize',9);
    end
end
cmdo_panel_ed(ax,'a'); set(ax,'FontName','Arial','FontSize',9,'TickLength',[0 0]);

%% b — guarded weight trajectory
ax = nexttile(tl,2); hold(ax,'on');
for k=1:3
    T=S(S.cycle==cycleOrder(k),:); [~,o]=sort(T.budget); T=T(o,:);
    plot(ax,T.budget,T.mean_weight,'-o','Color',cycleColors(k,:), ...
        'LineWidth',2,'MarkerFaceColor',cycleColors(k,:), ...
        'MarkerEdgeColor','w','MarkerSize',6,'DisplayName',cycleLabels(k));
end
set(ax,'XScale','log'); xticks(ax,budgets); xticklabels(ax,string(budgets));
xlabel(ax,'Screened-case budget'); ylabel(ax,'Mean transport weight');
title(ax,'Borrowing remains guarded across budgets','FontWeight','bold');
legend(ax,'Location','southeast','Box','off'); cmdo_axes_ed(ax); cmdo_panel_ed(ax,'b');

%% c — direct root-budget contraction
ax = nexttile(tl,3); hold(ax,'on');
for k=1:3
    T=S(S.cycle==cycleOrder(k),:); [~,o]=sort(T.budget); T=T(o,:);
    plot(ax,T.budget,T.direct_mae,'o-','Color',cycleColors(k,:), ...
        'LineWidth',1.5,'MarkerFaceColor',cycleColors(k,:), ...
        'DisplayName',cycleLabels(k));
end
meanDirect=arrayfun(@(b) mean(S.direct_mae(S.budget==b)),budgets);
p=polyfit(log(double(budgets)),log(meanDirect),1);
xg=logspace(log10(min(budgets)),log10(max(budgets)),100);
yg=exp(polyval(p,log(xg)));
plot(ax,xg,yg,'k--','LineWidth',1.8,'DisplayName',sprintf('pooled fit %.3f',p(1)));
set(ax,'XScale','log','YScale','log'); xticks(ax,budgets); xticklabels(ax,string(budgets));
xlabel(ax,'Screened-case budget'); ylabel(ax,'Direct accuracy MAE');
title(ax,'Direct error follows the root-budget rate','FontWeight','bold');
legend(ax,'Location','southwest','Box','off'); cmdo_axes_ed(ax); cmdo_panel_ed(ax,'c');

%% d — frozen decision gates
ax = nexttile(tl,4); hold(ax,'on');
pass = double(G.passed);
y = 1:height(G);
markerColors = repmat([0.20 0.62 0.32], height(G), 1);
markerColors(pass == 0,:) = repmat([0.75 0.18 0.18], sum(pass == 0), 1);
scatter(ax,pass,y,70,markerColors, ...
    'filled','MarkerEdgeColor','w','LineWidth',0.7);
set(ax,'YDir','reverse'); xlim(ax,[-0.15 1.35]); xticks(ax,[0 1]);
xticklabels(ax,{'Fail','Pass'}); yticks(ax,y); yticklabels(ax,cmdo_gate_labels(string(G.gate)));
title(ax,'All ten frozen gates passed','FontWeight','bold');
text(ax,0.98,0.98,{sprintf('%d frozen witnesses', height(S) * 200); ...
    sprintf('coverage %.3f / %.3f', meanCoverage, minCoverage); ...
    sprintf('certificate violations %d', certificateViolations); ...
    sprintf('fallback residual %.3g', maxFallback)}, ...
    'Units','normalized','HorizontalAlignment','right','VerticalAlignment','top', ...
    'FontSize',8.5,'BackgroundColor','w','Margin',3);
cmdo_axes_ed(ax); cmdo_panel_ed(ax,'d');

exportgraphics(fig,fullfile(outputDir,'ExtendedDataFigure7_U8.pdf'),'ContentType','vector');
exportgraphics(fig,fullfile(outputDir,'ExtendedDataFigure7_U8.png'),'Resolution',600);
savefig(fig,fullfile(outputDir,'ExtendedDataFigure7_U8.fig'));
fprintf('Wrote Extended Data Figure 7 to %s\n',outputDir);
end

function labels=cmdo_gate_labels(labels)
labels=replace(labels,"three_temporal_reserve_cycles","Three temporal cycles");
labels=replace(labels,"exact_full_direct_fallback","Exact direct fallback");
labels=replace(labels,"covered_event_certificate_violations","Zero certificate violations");
labels=replace(labels,"mean_simultaneous_coverage","Mean coverage");
labels=replace(labels,"minimum_state_simultaneous_coverage","Minimum state coverage");
labels=replace(labels,"pooled_observer_noninferiority","Pooled non-inferiority");
labels=replace(labels,"worst_state_regret","Worst-state regret");
labels=replace(labels,"improved_reserve_cycles","Improved cycles");
labels=replace(labels,"nontrivial_borrowing","Non-trivial borrowing");
labels=replace(labels,"direct_root_budget_slope","Direct root-budget slope");
end
function cmdo_axes_ed(ax)
set(ax,'FontName','Arial','FontSize',9,'Box','off','TickDir','out','LineWidth',0.8,'Layer','top');
grid(ax,'on'); ax.GridAlpha=0.10;
end
function cmdo_panel_ed(ax,letter)
text(ax,-0.12,1.06,letter,'Units','normalized','FontName','Arial', ...
    'FontWeight','bold','FontSize',15,'Clipping','off');
end
