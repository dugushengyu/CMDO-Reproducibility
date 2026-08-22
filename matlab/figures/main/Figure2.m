function Figure2(outputDir)
%FIGURE2 CMDO Figure 2 — standalone renderer
%
% Revised to improve:
%   1) larger spacing between panels
%   2) unified font sizes
%   3) adjustable style block at the top
%   4) panel-c fitted-slope box moved to lower-left
%
% Standalone:
%   - no cmdo_config
%   - no cmdo_safe_* helpers
%   - no external source-data input files
%
% Scientific settings preserved:
%   rng seed = 20260728
%   budgets  = [16 32 64 128 256 512 1024]
%   theta    = 0.70
%   nRep     = 500
%   R        = 400
%
% Usage:
%   Figure2
%   Figure2('path/to/output')

close all;

%% ========================================================================
% USER-ADJUSTABLE STYLE BLOCK
% ========================================================================

% ------------------------------
% Output / canvas
% ------------------------------
FIG_W = 1600;
FIG_H = 500;
FIG_POS = [40 50 FIG_W FIG_H];

TILE_SPACING = 'loose';
TILE_PADDING = 'loose';

% ------------------------------
% Font settings
% ------------------------------
FONT_NAME = 'Arial';

FS_BASE          = 10;

FS_SUPTITLE      = FS_BASE ;     % 12
FS_PANEL_TITLE   = FS_BASE ;     % 11
FS_AXIS_LABEL    = FS_BASE;         % 10
FS_AXIS_TICK     = FS_BASE ;     % 9
FS_LEGEND        = FS_BASE ;     % 9
FS_PANEL_LETTER  = FS_BASE ;     % 11
FS_ANNOTATION    = FS_BASE ;     % 9
FS_SMALL         = FS_BASE ;     % 9
FS_FORMULA       = FS_BASE;         % 10

% ------------------------------
% Colors
% ------------------------------
blue   = [0.0000 0.4470 0.7410];
orange = [0.8500 0.3250 0.0980];
red    = [0.78 0.08 0.08];
grey   = [0.38 0.38 0.38];

% ------------------------------
% Panel-a layout
% A now spans two tiles, so let it use
% a wider internal composition.
% ------------------------------
PA_WORLD_X  = 0.52;
PA_WORLD_W  = 0.22;
PA_WORLD_H  = 0.24;

PA_WORLDP_Y = 0.58;
PA_WORLDQ_Y = 0.15;

PA_DELTA_X  = 0.77;
PA_NOTE_X   = 0.74;

% ------------------------------
% Panel-c textbox
% ------------------------------
PC_BOX_X = 0.06;
PC_BOX_Y = 0.08;

%% ========================================================================
% 0. Output path
% ========================================================================

thisFile = mfilename('fullpath');

if isempty(thisFile)
    scriptDir = pwd;
else
    scriptDir = fileparts(thisFile);
end

reviewerRoot = strtrim(getenv('CMDO_OUTPUT_ROOT'));

if nargin < 1 || isempty(outputDir)
    if ~isempty(reviewerRoot)
        outputDir = fullfile(reviewerRoot,'figures','main');
    else
        outputDir = fullfile(scriptDir,'output');
    end
end

if ~exist(outputDir,'dir')
    mkdir(outputDir);
end

stem = 'Figure2_Observability_And_Information_Cost';

fprintf('\n');
fprintf('============================================================\n');
fprintf(' CMDO FIGURE 2 — STANDALONE RENDERER\n');
fprintf('============================================================\n');
fprintf('Output: %s\n\n',outputDir);

%% ========================================================================
% 1. Frozen scientific settings
% ========================================================================

seed = 20260728;
budgets = [16 32 64 128 256 512 1024];
theta = 0.70;
nRep = 500;
R = 400;
n = numel(budgets);

rng(seed,'twister');

%% ========================================================================
% 2. PANEL B DATA
% ========================================================================

intervalMedian = zeros(n,1);
intervalLo = zeros(n,1);
intervalHi = zeros(n,1);

for i = 1:n
    m = budgets(i);
    estimates = mean(rand(nRep,m) < theta, 2);

    intervalMedian(i) = local_quantile(estimates,0.50);
    intervalLo(i)     = local_quantile(estimates,0.025);
    intervalHi(i)     = local_quantile(estimates,0.975);
end

%% ========================================================================
% 3. PANEL C DATA
% ========================================================================

truth = [ ...
    0.5*(1 + erf(0.5)), ...
    0.70, ...
    5/7, ...
    0.62];

mae = zeros(4,n);

for i = 1:n
    m = budgets(i);

    acc = mean(rand(R,m) < truth(2),2);
    sens = mean(rand(R,m) < truth(4),2);

    g1 = randg(5,R,m);
    g2 = randg(2,R,m);
    brier = mean(g1 ./ (g1 + g2),2);

    aucv = zeros(R,1);
    h = max(2,floor(m/2));

    for r = 1:R
        positiveScores = randn(h,1) + 1;
        negativeScores = randn(h,1);
        aucv(r) = local_auc(positiveScores,negativeScores);
    end

    mae(:,i) = [ ...
        mean(abs(aucv - truth(1))); ...
        mean(abs(acc  - truth(2))); ...
        mean(abs(brier - truth(3))); ...
        mean(abs(sens - truth(4)))];
end

rootReference = mae(1,1) .* (budgets ./ budgets(1)).^(-0.5);

slopes = zeros(4,1);
for j = 1:4
    p = polyfit(log10(budgets),log10(mae(j,:)),1);
    slopes(j) = p(1);
end

%% ========================================================================
% 4. Save numerical companions
% ========================================================================

panelB = table( ...
    budgets(:), ...
    repmat(theta,n,1), ...
    intervalMedian, ...
    intervalLo, ...
    intervalHi, ...
    'VariableNames',{ ...
    'audit_budget_m', ...
    'true_performance_theta', ...
    'median_estimate', ...
    'empirical_q025', ...
    'empirical_q975'});

writetable(panelB,fullfile(outputDir,[stem '_PanelB_Intervals.csv']));

panelC = table( ...
    budgets(:), ...
    mae(1,:).', ...
    mae(2,:).', ...
    mae(3,:).', ...
    mae(4,:).', ...
    rootReference(:), ...
    'VariableNames',{ ...
    'audit_budget_m', ...
    'auc_mae', ...
    'accuracy_mae', ...
    'brier_utility_mae', ...
    'sensitivity_mae', ...
    'm_minus_half_reference'});

writetable(panelC,fullfile(outputDir,[stem '_PanelC_RootBudget.csv']));

slopeTable = table( ...
    ["AUC";"Accuracy";"Brier utility";"Sensitivity"], ...
    slopes, ...
    'VariableNames',{'metric','fitted_loglog_slope'});

writetable(slopeTable,fullfile(outputDir,[stem '_PanelC_Slopes.csv']));

%% ========================================================================
% 5. Figure canvas
% ========================================================================

fig = figure( ...
    'Position',FIG_POS, ...
    'Color','w', ...
    'Renderer','painters', ...
    'Name','CMDO Figure 2', ...
    'NumberTitle','off');

tl = tiledlayout(fig,1,4, ...
    'TileSpacing',TILE_SPACING, ...
    'Padding',TILE_PADDING);

axA = nexttile(tl,[1 2]);   % A 占两列
axB = nexttile(tl);         % B 一列
axC = nexttile(tl);         % C 一列

title(tl, ...
    'From structural ambiguity to sampling uncertainty', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_SUPTITLE);

drawnow;

%% ========================================================================
% PANEL A
% ========================================================================

hold(axA,'on');
axis(axA,[0 1 0 1]);
axis(axA,'off');

local_panel_letter(axA,'a',FONT_NAME,FS_PANEL_LETTER);

title(axA, ...
    'Structural ambiguity without outcomes', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_PANEL_TITLE);

% Same-evidence box
rectangle(axA, ...
    'Position',[0.05 0.34 0.20 0.37], ...
    'Curvature',0.08, ...
    'FaceColor',[0.98 0.98 0.98], ...
    'EdgeColor',[0.15 0.15 0.15], ...
    'LineWidth',1.0);

text(axA,0.15,0.645, ...
    {'Same outcome-free','evidence O'}, ...
    'HorizontalAlignment','center', ...
    'VerticalAlignment','middle', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_AXIS_LABEL);

plot(axA,[0.085 0.285],[0.585 0.585],'-', ...
    'Color',[0.58 0.58 0.58], ...
    'LineWidth',0.8);

text(axA,0.15,0.505, ...
    {'scores  S','confidence  C','drift summaries'}, ...
    'HorizontalAlignment','center', ...
    'VerticalAlignment','middle', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_ANNOTATION);

text(axA,0.15,0.295, ...
    'identical in both worlds', ...
    'HorizontalAlignment','center', ...
    'VerticalAlignment','top', ...
    'FontName',FONT_NAME, ...
    'FontAngle','italic', ...
    'FontSize',FS_SMALL, ...
    'Color',grey);

% Arrows
quiver(axA,0.27,0.54,0.08,0.145,0, ...
    'Color',[0.10 0.10 0.10], ...
    'LineWidth',1.15, ...
    'MaxHeadSize',0.9);

quiver(axA,0.27,0.50,0.08,-0.145,0, ...
    'Color',[0.10 0.10 0.10], ...
    'LineWidth',1.15, ...
    'MaxHeadSize',0.9);

% World inset axes
pA = axA.Position;

axP = axes(fig, ...
    'Position',[ ...
    pA(1)+PA_WORLD_X*pA(3), ...
    pA(2)+PA_WORLDP_Y*pA(4), ...
    PA_WORLD_W*pA(3), ...
    PA_WORLD_H*pA(4)], ...
    'Color','w');

axQ = axes(fig, ...
    'Position',[ ...
    pA(1)+PA_WORLD_X*pA(3), ...
    pA(2)+PA_WORLDQ_Y*pA(4), ...
    PA_WORLD_W*pA(3), ...
    PA_WORLD_H*pA(4)], ...
    'Color','w');

scores = linspace(0.08,0.92,10);
yP = [zeros(1,5) ones(1,5)];
yQ = 1 - yP;

% World P
hold(axP,'on');
scatter(axP,scores(yP==0),yP(yP==0),28,'o', ...
    'MarkerEdgeColor',blue, ...
    'LineWidth',1.1);
scatter(axP,scores(yP==1),yP(yP==1),28,'o','filled', ...
    'MarkerFaceColor',blue, ...
    'MarkerEdgeColor',blue);
plot(axP,[0.08 0.92],[0.05 0.95],'--', ...
    'Color',blue, ...
    'LineWidth',0.9);
xlim(axP,[0 1]); ylim(axP,[-0.05 1.05]);
xticks(axP,[0 0.5 1]); yticks(axP,[0 1]);
xlabel(axP,'Score S','FontName',FONT_NAME,'FontSize',FS_SMALL);
ylabel(axP,'Outcome Y','FontName',FONT_NAME,'FontSize',FS_SMALL);
title(axP,'World P: AUC = 1', ...
    'Color',blue, ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_SMALL);
local_axes_style(axP,FONT_NAME,FS_SMALL);

% World Q
hold(axQ,'on');
scatter(axQ,scores(yQ==0),yQ(yQ==0),28,'o', ...
    'MarkerEdgeColor',orange, ...
    'LineWidth',1.1);
scatter(axQ,scores(yQ==1),yQ(yQ==1),28,'o','filled', ...
    'MarkerFaceColor',orange, ...
    'MarkerEdgeColor',orange);
plot(axQ,[0.08 0.92],[0.95 0.05],'--', ...
    'Color',orange, ...
    'LineWidth',0.9);
xlim(axQ,[0 1]); ylim(axQ,[-0.05 1.05]);
xticks(axQ,[0 0.5 1]); yticks(axQ,[0 1]);
xlabel(axQ,'Score S','FontName',FONT_NAME,'FontSize',FS_SMALL);
ylabel(axQ,'Outcome Y','FontName',FONT_NAME,'FontSize',FS_SMALL);
title(axQ,'World Q: AUC = 0', ...
    'Color',orange, ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_SMALL);
local_axes_style(axQ,FONT_NAME,FS_SMALL);

% Quantitative consequence
text(axA,PA_DELTA_X,0.54, ...
    '\Delta_{AUC}(O) = 1', ...
    'Interpreter','tex', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','middle', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_FORMULA, ...
    'Color',red);

text(axA,PA_NOTE_X,0.43, ...
    {'same evidence','opposite performance'}, ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','middle', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_SMALL, ...
    'Color',grey);

text(axA,0.39,0.06, ...
    'minimax error \geq 1/2', ...
    'Interpreter','tex', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','bottom', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_FORMULA);

%% ========================================================================
% PANEL B
% ========================================================================

hold(axB,'on');
local_panel_letter(axB,'b',FONT_NAME,FS_PANEL_LETTER);

title(axB, ...
    'Audits shrink performance uncertainty', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_PANEL_TITLE);

hStruct = line(axB,[0 1],[1 1], ...
    'Color',[0.62 0.62 0.62], ...
    'LineWidth',7);

hTruth = xline(axB,theta,'--', ...
    'Color',[0.82 0.12 0.12], ...
    'LineWidth',1.25);

hCI = gobjects(1);
hMed = gobjects(1);

for i = 1:n
    y = i + 1;

    line(axB,[intervalLo(i) intervalHi(i)],[y y], ...
        'Color',[0.58 0.76 0.90], ...
        'LineWidth',6, ...
        'HandleVisibility','off');

    h = line(axB,[intervalLo(i) intervalHi(i)],[y y], ...
        'Color',[0.05 0.31 0.56], ...
        'LineWidth',1.15);

    hm = plot(axB,intervalMedian(i),y,'o', ...
        'MarkerFaceColor','k', ...
        'MarkerEdgeColor','k', ...
        'MarkerSize',4.2);

    if i == 1
        hCI = h;
        hMed = hm;
    else
        set(h,'HandleVisibility','off');
        set(hm,'HandleVisibility','off');
    end
end

xlim(axB,[0 1]);
ylim(axB,[0.45 n+1.55]);
set(axB,'YDir','reverse');

yticks(axB,1:n+1);
labelsB = cell(n+1,1);
labelsB{1} = 'm = 0';
for i = 1:n
    labelsB{i+1} = sprintf('m = %d',budgets(i));
end
yticklabels(axB,labelsB);

xlabel(axB,'Performance (Bernoulli accuracy)', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_AXIS_LABEL);

ylabel(axB,'Outcome evidence', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_AXIS_LABEL);

text(axB,theta+0.018,0.72, ...
    sprintf('\\theta = %.2f',theta), ...
    'Interpreter','tex', ...
    'Color',[0.82 0.12 0.12], ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_SMALL);

text(axB,0.02,0.78, ...
    'structural range', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','bottom', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_SMALL, ...
    'Color',grey);

set(axB,'XGrid','on','YGrid','on');
axB.GridAlpha = 0.10;
local_axes_style(axB,FONT_NAME,FS_AXIS_TICK);

lgdB = legend(axB, ...
    [hStruct hTruth hCI hMed], ...
    { ...
    'm = 0 structural range', ...
    'True performance', ...
    '95% interval', ...
    'Median'}, ...
    'Location','southwest', ...
    'NumColumns',1, ...
    'Box','off', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_LEGEND);

try
    lgdB.ItemTokenSize = [12 8];
catch
end

%% ========================================================================
% PANEL C
% ========================================================================

cla(axC);
set(axC,'XScale','log','YScale','log');
hold(axC,'on');

local_panel_letter(axC,'c',FONT_NAME,FS_PANEL_LETTER);

title(axC, ...
    'Root-budget scaling across metrics', ...
    'FontName',FONT_NAME, ...
    'FontWeight','bold', ...
    'FontSize',FS_PANEL_TITLE);

names = {'AUC','Accuracy','Brier utility','Sensitivity'};
marks = {'o','s','^','d'};

for j = 1:4
    plot(axC,budgets,mae(j,:),'-', ...
        'Marker',marks{j}, ...
        'LineWidth',1.55, ...
        'MarkerSize',5.0, ...
        'DisplayName',names{j});
end

plot(axC,budgets,rootReference,'k--', ...
    'LineWidth',1.20, ...
    'DisplayName','m^{-1/2} reference');

xlim(axC,[14 1200]);
yMin = min([mae(:); rootReference(:)]) * 0.70;
yMax = max([mae(:); rootReference(:)]) * 1.30;
ylim(axC,[yMin yMax]);

xticks(axC,[16 64 256 1024]);
xticklabels(axC,{'16','64','256','1024'});

xlabel(axC,'Number of audited outcomes, m', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_AXIS_LABEL);

ylabel(axC,'Mean absolute error', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_AXIS_LABEL);

set(axC, ...
    'XGrid','on', ...
    'YGrid','on', ...
    'XMinorGrid','off', ...
    'YMinorGrid','off');
axC.GridAlpha = 0.10;

local_axes_style(axC,FONT_NAME,FS_AXIS_TICK);
set(axC,'XScale','log','YScale','log');

legend(axC,'Location','northeast', ...
    'Box','off', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_LEGEND);

% lower-left textbox as requested
text(axC,PC_BOX_X,PC_BOX_Y, ...
    sprintf([ ...
    'Fitted slopes (log-log)\n' ...
    'AUC          %.3f\n' ...
    'Accuracy     %.3f\n' ...
    'Brier        %.3f\n' ...
    'Sensitivity  %.3f'], ...
    slopes(1),slopes(2),slopes(3),slopes(4)), ...
    'Units','normalized', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','bottom', ...
    'FontName',FONT_NAME, ...
    'FontSize',FS_SMALL, ...
    'BackgroundColor','w', ...
    'EdgeColor',[0.75 0.75 0.75], ...
    'Margin',4);

uistack(axP,'top');
uistack(axQ,'top');

%% ========================================================================
% 6. Save outputs
% ========================================================================

figFile  = fullfile(outputDir,[stem '.fig']);
pdfFile  = fullfile(outputDir,[stem '.pdf']);
pngFile  = fullfile(outputDir,[stem '.png']);
tiffFile = fullfile(outputDir,[stem '.tiff']);

drawnow;
savefig(fig,figFile);

try
    exportgraphics(fig,pdfFile,'ContentType','vector');
    exportgraphics(fig,pngFile,'Resolution',600);
    exportgraphics(fig,tiffFile,'Resolution',600);
catch
    print(fig,pdfFile,'-dpdf','-painters');
    print(fig,pngFile,'-dpng','-r600');
    print(fig,tiffFile,'-dtiff','-r600');
end

%% ========================================================================
% Console audit
% ========================================================================

fprintf('Scientific settings\n');
fprintf('-------------------\n');
fprintf('Seed              : %d\n',seed);
fprintf('True performance  : %.2f\n',theta);
fprintf('Panel B repeats   : %d\n',nRep);
fprintf('Panel C repeats   : %d\n',R);
fprintf('Budgets           : ');
fprintf('%d ',budgets);
fprintf('\n\n');

fprintf('Fitted log-log slopes\n');
fprintf('---------------------\n');
fprintf('AUC         : %.6f\n',slopes(1));
fprintf('Accuracy    : %.6f\n',slopes(2));
fprintf('Brier       : %.6f\n',slopes(3));
fprintf('Sensitivity : %.6f\n',slopes(4));
fprintf('\n');

fprintf('Outputs\n');
fprintf('-------\n');
fprintf('FIG  : %s\n',figFile);
fprintf('PDF  : %s\n',pdfFile);
fprintf('PNG  : %s\n',pngFile);
fprintf('TIFF : %s\n',tiffFile);
fprintf('\n=== FIGURE 2 COMPLETE ===\n');

end

%% =========================================================================
% LOCAL QUANTILE
% =========================================================================
function q = local_quantile(values, probability)

values = double(values(:));
values = sort(values(isfinite(values)));
probability = double(probability);

if isempty(values)
    q = NaN(size(probability));
    return;
end

probability = min(max(probability,0),1);
index = 1 + (numel(values)-1).*probability;
lo = floor(index);
hi = ceil(index);
weight = index-lo;

q = (1-weight).*values(lo) + weight.*values(hi);
end

%% =========================================================================
% LOCAL AUC
% =========================================================================
function auc = local_auc(positiveScores, negativeScores)

positiveScores = double(positiveScores(:));
negativeScores = double(negativeScores(:));

positiveScores = positiveScores(isfinite(positiveScores));
negativeScores = negativeScores(isfinite(negativeScores));

if isempty(positiveScores) || isempty(negativeScores)
    auc = NaN;
    return;
end

scores = [positiveScores; negativeScores];
ranks = local_tied_rank(scores);

nPos = numel(positiveScores);
nNeg = numel(negativeScores);

auc = (sum(ranks(1:nPos)) - nPos*(nPos+1)/2) / (nPos*nNeg);
end

%% =========================================================================
% LOCAL TIED RANK
% =========================================================================
function ranks = local_tied_rank(values)

[sortedValues,order] = sort(values);
ranks = zeros(size(values));

i = 1;
while i <= numel(sortedValues)
    j = i;
    while j < numel(sortedValues) && sortedValues(j+1) == sortedValues(i)
        j = j+1;
    end
    ranks(order(i:j)) = (i+j)/2;
    i = j+1;
end
end

%% =========================================================================
% PANEL LETTER
% =========================================================================
function local_panel_letter(ax,letter,fontName,fontSize)

text(ax,-0.06,1.035,letter, ...
    'Units','normalized', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','bottom', ...
    'FontName',fontName, ...
    'FontWeight','bold', ...
    'FontSize',fontSize, ...
    'Clipping','off');
end

%% =========================================================================
% AXES STYLE
% =========================================================================
function local_axes_style(ax,fontName,fontSize)

set(ax, ...
    'FontName',fontName, ...
    'FontSize',fontSize, ...
    'LineWidth',0.8, ...
    'TickDir','out', ...
    'Box','off');
end
