function Figure6
%FIGURE6 Generate the corrected CMDO Figure 6 and export all formats.
close all;
rng(20260728,'twister');
fprintf('Executing Figure6 from: %s\n', mfilename('fullpath'));

scriptDir = fileparts(mfilename('fullpath'));
if ~isempty(scriptDir)
    addpath(genpath(scriptDir));
end

cfg = cmdo_config('Figure6');
D   = cmdo_load_all(cfg);

% Figure output folder
outDir = cfg.outputDir;

if ~exist(outDir, 'dir')
    mkdir(outDir);
end

fig = figure('Position',[30 30 1100 950],'Color','w');
tl  = tiledlayout(fig,2,2,'TileSpacing','loose','Padding','loose');
tl.OuterPosition = [0.055 0.055 0.91 0.91];
sgtitle(tl,'Natural clinical deployment and general performance support', ...
    'FontWeight','bold','FontSize',18);

%% shared data
A = D.u7_target(string(D.u7_target.metric)=="AUC",:);
[~,ordA] = sort(A.gain,'ascend');
A = A(ordA,:);

strataNames = cell(height(A),1);
for i = 1:height(A)
    strataNames{i} = cmdo_pretty_stratum(string(A.stratum(i)));
end

U7M = D.u7_metric;
mAUC = find(string(U7M.metric)=="AUC",1);
if isempty(mAUC)
    error('Figure6: AUC row not found in D.u7_metric');
end
aucm = U7M(mAUC,:);

S = D.u7_state(string(D.u7_state.metric)=="AUC",:);
budgets = unique(S.budget);
budgets = sort(budgets(:)');
maxBudget = max(budgets);

%% =======================================================================
% Panel a
% ========================================================================
axA = nexttile(tl); hold(axA,'on');
cmdo_safe_panel_letter(axA,'a');

bA = bar(axA,[A.direct_mae, A.mae],'grouped','BarWidth',0.78);
bA(1).FaceColor = [0.18 0.47 0.85];
bA(2).FaceColor = [0.98 0.56 0.13];
bA(1).EdgeColor = 'none';
bA(2).EdgeColor = 'none';

xticks(axA,1:height(A));
xticklabels(axA,strataNames);
xtickangle(axA,55);
ylabel(axA,'Same-budget AUC MAE');
title(axA,'All 16 prespecified clinical strata improved','FontWeight','bold');
legend(axA,{'Same-budget full-direct','Frozen observer'}, ...
    'Location','northwest','Box','off');

yMaxA = max([A.direct_mae; A.mae]);
ylim(axA,[0, 1.14*yMaxA]);

text(axA,0.98,0.97,'All strata improved', ...
    'Units','normalized', ...
    'HorizontalAlignment','right', ...
    'VerticalAlignment','top', ...
    'FontWeight','bold', ...
    'FontSize',10, ...
    'Color',[0.12 0.60 0.28]);

cmdo_safe_apply_axes_style(axA);


%% =======================================================================
% Panel b : all labels + draggable
% ========================================================================
axB = nexttile(tl); hold(axB,'on');
cmdo_safe_panel_letter(axB,'b');

M = S(S.budget==maxBudget,:);
x = double(M.mean_sensor_gap);
y = double(M.transport_abs_error);

% Sort for reproducible plotting and labelling
[~,ordB] = sort(x,'ascend');
x = x(ordB);
y = y(ordB);
M = M(ordB,:);

% Fit line + band
[xs,ys,ylo,yhi] = cmdo_linear_fit_band(x,y);
fill(axB,[xs; flipud(xs)], [ylo; flipud(yhi)], ...
    [0.75 0.75 0.75], 'FaceAlpha',0.22, 'EdgeColor','none');
plot(axB,xs,ys,'k-','LineWidth',1.5);

scatter(axB,x,y,38, ...
    'MarkerFaceColor',[0.08 0.33 0.95], ...
    'MarkerEdgeColor','white', ...
    'LineWidth',0.5);

% Spearman correlation and exact two-sided P value
[rho,pval] = cmdo_spearman_with_p(x,y);

fprintf('\nFigure 6b statistical check:\n');
fprintf('n     = %d\n', numel(x));
fprintf('rho   = %.15f\n', rho);
fprintf('P     = %.15g\n', pval);

% Integrity checks against the sealed U7 canonical record
expectedRho = 0.8705882352941177;
expectedP   = 1.149893480274162e-05;

assert(numel(x) == 16, ...
    'Figure6:UnexpectedSampleCount', ...
    'Expected 16 U7 AUC strata at the largest budget; found %d.', numel(x));

assert(abs(rho - expectedRho) < 1e-12, ...
    'Figure6:UnexpectedRho', ...
    'Unexpected Spearman rho: %.15g', rho);

assert(abs(pval - expectedP) < 1e-10, ...
    'Figure6:UnexpectedPValue', ...
    'Unexpected Spearman P value: %.15g', pval);

assert(pval > 0 && pval < 1, ...
    'Figure6:InvalidPValue', ...
    'Invalid P value: %.15g', pval);

xlabel(axB,'Paired-sensor discrepancy');
ylabel(axB,'Source-to-target transport absolute error');
title(axB,sprintf('Transport-bias observability (\\rho = %.3f)',rho), ...
    'FontWeight','bold');

% text(axB,0.03,1.02, ...
%     sprintf('\\rho = %.3f',rho),...
%     'Units','normalized', ...
%     'HorizontalAlignment','left', ...
%     'VerticalAlignment','top', ...
%     'FontSize',10, ...
%     'FontWeight','bold');

xlim(axB,[min(x)-0.004, max(x)+0.008]);
ylim(axB,[0, max(y)*1.15]);
cmdo_safe_apply_axes_style(axB);

% -------------------------------------------------------------------------
% Draggable textboxes for all panel-b data points
% Each textbox is connected to its data point by a leader line.
% -------------------------------------------------------------------------
panelBFile = fullfile( ...
    outDir, ...
    'Figure6_panelB_label_positions.mat');

labelNamesB = strings(height(M),1);

for i = 1:height(M)
    labelNamesB(i) = cmdo_pretty_stratum(string(M.stratum(i)));
end

% Default label locations are used only before the first manual adjustment.
defaultLabelPosB = f6_default_label_positions(string(M.stratum), x, y);
labelPosB = defaultLabelPosB;

if exist(panelBFile, 'file')
    savedB = load(panelBFile);

    if isfield(savedB, 'labelPosB') && ...
            isequal(size(savedB.labelPosB), [numel(x), 2])
        labelPosB = savedB.labelPosB;
    end
end

labelHandlesB  = gobjects(numel(x),1);
leaderHandlesB = gobjects(numel(x),1);

for i = 1:numel(x)

    % Leader line from the data point to the textbox centre.
    leaderHandlesB(i) = plot( ...
        axB, ...
        [x(i), labelPosB(i,1)], ...
        [y(i), labelPosB(i,2)], ...
        '-', ...
        'Color', [0.35 0.35 0.35], ...
        'LineWidth', 0.65, ...
        'HandleVisibility', 'off', ...
        'HitTest', 'off', ...
        'PickableParts', 'none');

    % Draggable textbox.
    labelHandlesB(i) = text( ...
        axB, ...
        labelPosB(i,1), ...
        labelPosB(i,2), ...
        labelNamesB(i), ...
        'FontName', 'Arial', ...
        'FontSize', 6.8, ...
        'HorizontalAlignment', 'center', ...
        'VerticalAlignment', 'middle', ...
        'BackgroundColor', 'w', ...
        'EdgeColor', [0.75 0.75 0.75], ...
        'LineWidth', 0.45, ...
        'Margin', 1.0, ...
        'Clipping', 'off', ...
        'PickableParts', 'all', ...
        'HitTest', 'on');

    % Store the data-point anchor and corresponding leader line.
    setappdata( ...
        labelHandlesB(i), ...
        'AnchorPoint', ...
        [x(i), y(i)]);

    setappdata( ...
        labelHandlesB(i), ...
        'LeaderHandle', ...
        leaderHandlesB(i));

    labelHandlesB(i).ButtonDownFcn = ...
        @(src, ~) f6_start_label_drag(src, fig);
end

%% =======================================================================
% Panel c
% ========================================================================
axC = nexttile(tl); hold(axC,'on');
cmdo_safe_panel_letter(axC,'c');

metricOrder = ["SENSITIVITY","SPECIFICITY","AUC","BALANCED_ACCURACY","BRIER_UTILITY"];
metricLabels = {'Sensitivity','Specificity','AUC','Balanced accuracy','Brier utility'};

metricVals  = nan(numel(metricOrder),1);
metricWorst = nan(numel(metricOrder),1);

for k = 1:numel(metricOrder)
    idx = find(string(U7M.metric)==metricOrder(k),1);
    if ~isempty(idx)
        metricVals(k)  = 100*double(U7M.relative_gain(idx));
        metricWorst(k) = double(U7M.worst_regret(idx));
    end
end

colorsC = zeros(numel(metricOrder),3);
for k = 1:numel(metricOrder)
    if metricWorst(k) > 0
        colorsC(k,:) = [0.97 0.58 0.15];
    else
        colorsC(k,:) = [0.20 0.68 0.38];
    end
end

bC = barh(axC,metricVals,'FaceColor','flat','EdgeColor','none','BarWidth',0.65);
bC.CData = colorsC;

yticks(axC,1:numel(metricOrder));
yticklabels(axC,metricLabels);
set(axC,'YDir','reverse');

xlabel(axC,'Relative pooled MAE reduction (%)');
title(axC,'General support across five bounded metrics','FontWeight','bold');

for k = 1:numel(metricVals)
    text(axC, metricVals(k)+0.12, k, sprintf('%.2f%%',metricVals(k)), ...
        'FontWeight','bold', ...
        'VerticalAlignment','middle', ...
        'FontSize',10);
end

p1 = plot(axC,nan,nan,'s', ...
    'MarkerFaceColor',[0.20 0.68 0.38], ...
    'MarkerEdgeColor',[0.20 0.68 0.38], ...
    'MarkerSize',8);
p2 = plot(axC,nan,nan,'s', ...
    'MarkerFaceColor',[0.97 0.58 0.15], ...
    'MarkerEdgeColor',[0.97 0.58 0.15], ...
    'MarkerSize',8);

legend(axC,[p1 p2], ...
    {'Non-positive observed worst regret', ...
     'Positive worst regret in at least one state'}, ...
    'Location','southeast', ...
    'Box','off');

xlim(axC,[0, max(metricVals)*1.28]);
cmdo_safe_apply_axes_style(axC);

%% =======================================================================
% Panel d : violin/envelope + points + median + inset
% ========================================================================
axD = nexttile(tl); hold(axD,'on');
hPanelD = cmdo_safe_panel_letter(axD,'d');
hPanelD.Position = [-0.12 1.13 0];
hPanelD.VerticalAlignment = 'bottom';

allW = cmdo_try_get_weight(S);
meanWByBudget = nan(numel(budgets),1);

for j = 1:numel(budgets)
    bj = budgets(j);
    v = double(S.regret(S.budget==bj));
    v = v(isfinite(v));

    % envelope / violin 先画
    cmdo_simple_violin(axD, j, v, 0.30, [0.96 0.73 0.45], 0.32);

    % 再画散点（放在包络上面）
    xj = j + 0.035*randn(size(v));
    scatter(axD,xj,v,16, ...
        'MarkerFaceColor',[0.95 0.52 0.05], ...
        'MarkerEdgeColor','white', ...
        'LineWidth',0.35);

    % 中位线
    medv = median(v,'omitnan');
    plot(axD,[j-0.16 j+0.16],[medv medv], ...
        'k-','LineWidth',1.8);

    if ~isempty(allW)
        meanWByBudget(j) = mean(allW(S.budget==bj),'omitnan');
    end
end

yline(axD,0,'--','Color',[0.15 0.45 0.95],'LineWidth',1);
xticks(axD,1:numel(budgets));
xticklabels(axD,string(budgets));
xlabel(axD,'Outcome budget');
ylabel(axD,'Stratum-level AUC regret');
title(axD,'Clinical AUC safety across outcome budgets','FontWeight','bold');
axD.YAxis.Exponent = 0;
ytickformat(axD,'%.3f');

worstReg = double(aucm.worst_regret);
covv     = double(aucm.coverage);
noharm   = double(aucm.no_harm);
meanWAll = mean(allW,'omitnan');

summaryText = { ...
    sprintf('Worst state   %.6f', worstReg), ...
    sprintf('Coverage / no-harm  %.3f / %.3f', covv, noharm), ...
    sprintf('Mean weight  %.4f', meanWAll)};

text(axD,0.03,0.96,summaryText, ...
    'Units','normalized', ...
    'VerticalAlignment','top', ...
    'FontSize',9.5, ...
    'BackgroundColor',[0.95 0.98 0.95], ...
    'EdgeColor',[0.60 0.75 0.60], ...
    'Margin',6);

% inset: mean transport weight
posD = axD.Position;
axInset = axes(fig,'Position',[posD(1)+0.67*posD(3), posD(2)+0.18*posD(4), 0.27*posD(3), 0.24*posD(4)]);
hold(axInset,'on');
plot(axInset,1:numel(budgets),meanWByBudget,'-o', ...
    'Color',[0.45 0.25 0.75], ...
    'MarkerFaceColor',[0.45 0.25 0.75], ...
    'LineWidth',1.2, ...
    'MarkerSize',4.5);
xticks(axInset,[1 numel(budgets)]);
xticklabels(axInset,string([budgets(1) budgets(end)]));
title(axInset,'Mean transport weight','FontSize',8,'FontWeight','bold');
set(axInset,'FontSize',6.5,'Box','on','XGrid','on','YGrid','on');

cmdo_safe_apply_axes_style(axD);

%% ------------------------------------------------------------------------
% Manual panel-b label adjustment
% The figure is exported only after the user clicks the save button.
% -------------------------------------------------------------------------
drawnow;

if usejava('desktop') && ~strcmp(getenv('CMDO_BATCH_MODE'), '1')

    instructionBox = annotation( ...
        fig, ...
        'textbox', ...
        [0.275 0.006 0.470 0.032], ...
        'String', ...
        ['Drag the panel b textboxes, then click ' ...
         '"Save labels & figure"'], ...
        'HorizontalAlignment', 'center', ...
        'VerticalAlignment', 'middle', ...
        'FontName', 'Arial', ...
        'FontSize', 9, ...
        'FontWeight', 'bold', ...
        'BackgroundColor', [1.00 1.00 0.88], ...
        'EdgeColor', [0.65 0.65 0.45], ...
        'FitBoxToText', 'off');

    finishButton = uicontrol( ...
        fig, ...
        'Style', 'pushbutton', ...
        'Units', 'normalized', ...
        'Position', [0.765 0.006 0.190 0.034], ...
        'String', 'Save labels & figure', ...
        'FontSize', 9.5, ...
        'FontWeight', 'bold', ...
        'Callback', @(~, ~) uiresume(fig));

    % Wait while the user manually arranges the textboxes.
    uiwait(fig);

    if ~isgraphics(fig)
        return;
    end

    % Save the manually selected textbox positions.
    labelPosB = NaN(numel(labelHandlesB), 2);

    for i = 1:numel(labelHandlesB)

        p = labelHandlesB(i).Position;
        labelPosB(i,:) = p(1:2);
    end

    save( ...
        panelBFile, ...
        'labelPosB', ...
        'labelNamesB');

    % Remove temporary UI before exporting the final publication figure.
    if isgraphics(finishButton)
        delete(finishButton);
    end

    if isgraphics(instructionBox)
        delete(instructionBox);
    end
end

drawnow;

% Export only after the label positions have been saved.
cmdo_safe_save_figure( ...
    fig, ...
    cfg, ...
    'Figure6_U7_Clinical_And_Multimetric');

fprintf( ...
    '\nPanel-b label positions saved to:\n%s\n', ...
    panelBFile);

end

%% =========================================================================
% HELPERS
% =========================================================================
function out = cmdo_pretty_stratum(s)
s = string(s);

switch upper(s)
    case "ALL"
        out = "All ER";
    case "ER_RACE_AFRICAN_AMERICAN"
        out = "African American";
    case "ER_RACE_CAUCASIAN"
        out = "Caucasian";
    case "ER_FEMALE"
        out = "Female";
    case "ER_MALE"
        out = "Male";
    case "ER_INSULIN_ACTIVE"
        out = "Insulin active";
    case "ER_INSULIN_NONE"
        out = "Insulin none";
    case "ER_PRIOR_UTILIZATION_POSITIVE"
        out = "Prior use >0";
    case "ER_PRIOR_UTILIZATION_ZERO"
        out = "Prior use =0";
    case "ER_AGE_LT50"
        out = "Age <50";
    case "ER_AGE_50_69"
        out = "Age 50-69";
    case "ER_AGE_GE70"
        out = "Age >=70";
    case "ER_SHORT_STAY_LE4"
        out = "Stay <=4 d";
    case "ER_LONG_STAY_GE5"
        out = "Stay >=5 d";
    case "ER_DIAGNOSES_GE7"
        out = "Diagnoses >=7";
    case "ER_DIAGNOSES_LE6"
        out = "Diagnoses <=6";
    otherwise
        out = strrep(char(s),'_',' ');
end
end

function [rho,pval] = cmdo_spearman_with_p(x,y)
% Robust Spearman correlation and two-sided asymptotic P value.
% This implementation does not use the second output of MATLAB corr,
% because some local MATLAB environments return P=0 for this dataset.

x = double(x(:));
y = double(y(:));

m = isfinite(x) & isfinite(y);
x = x(m);
y = y(m);

n = numel(x);

if n < 3
    rho  = NaN;
    pval = NaN;
    return;
end

% Spearman rho is Pearson correlation of tied ranks.
rx = cmdo_tied_rank(x);
ry = cmdo_tied_rank(y);

rx = rx - mean(rx);
ry = ry - mean(ry);

denom = sqrt(sum(rx.^2) * sum(ry.^2));

if denom <= 0
    rho  = NaN;
    pval = NaN;
    return;
end

rho = sum(rx .* ry) / denom;
rho = max(-1,min(1,rho));

% Match the canonical two-sided Spearman P value used in the sealed record:
% t = rho * sqrt((n-2)/(1-rho^2)), df = n-2.
df = n - 2;

if abs(rho) >= 1
    pval = 0;
else
    tstat = abs(rho) * sqrt(df / max(realmin('double'),1-rho^2));

    % Stable two-sided Student-t tail probability:
    % p = I_{df/(df+t^2)}(df/2, 1/2)
    z = df / (df + tstat^2);
    pval = betainc(z,df/2,0.5);
end

end

function r = cmdo_tied_rank(v)
% Average ranks for tied values, equivalent to MATLAB tiedrank.

v = double(v(:));
n = numel(v);

[sv,ord] = sort(v,'ascend');
r = zeros(n,1);

i = 1;
while i <= n
    j = i;

    while j < n && sv(j+1) == sv(i)
        j = j + 1;
    end

    meanRank = 0.5 * (i + j);
    r(ord(i:j)) = meanRank;

    i = j + 1;
end

end

function s = cmdo_format_pvalue(p)
if isnan(p)
    s = 'NaN';
elseif p < 1e-6
    s = sprintf('%.2g',p);
elseif p < 1e-4
    s = sprintf('%.2g',p);
else
    s = sprintf('%.4f',p);
end
end

function [xs,ys,ylo,yhi] = cmdo_linear_fit_band(x,y)
x = double(x(:));
y = double(y(:));
m = isfinite(x) & isfinite(y);
x = x(m); y = y(m);

xs = linspace(min(x),max(x),200)';
[p,S] = polyfit(x,y,1);
[ys,delta] = polyval(p,xs,S);

ylo = ys - delta;
yhi = ys + delta;
end

function w = cmdo_try_get_weight(T)
cands = {'mean_weight','transport_weight','weight','w','mean_transport_weight'};
w = [];
for i = 1:numel(cands)
    if ismember(cands{i}, T.Properties.VariableNames)
        w = double(T.(cands{i}));
        return;
    end
end
end

function cmdo_simple_violin(ax,x0,v,halfWidth,faceColor,faceAlpha)
% Robust violin/envelope without requiring Statistics Toolbox

v = double(v(:));
v = v(isfinite(v));

if numel(v) < 2
    return;
end

ymin = min(v);
ymax = max(v);
if ymin == ymax
    ymin = ymin - 1e-6;
    ymax = ymax + 1e-6;
end

nGrid = 200;
ygrid = linspace(ymin, ymax, nGrid);

% Try ksdensity first if available; otherwise use histogram-based density
useKsd = (exist('ksdensity','file') == 2);

if useKsd
    try
        f = ksdensity(v, ygrid, 'Function','pdf');
    catch
        useKsd = false;
    end
end

if ~useKsd
    nbins = max(8, min(20, round(sqrt(numel(v)))));
    edges = linspace(ymin, ymax, nbins+1);
    counts = histcounts(v, edges, 'Normalization', 'pdf');
    centers = (edges(1:end-1) + edges(2:end))/2;
    f = interp1(centers, counts, ygrid, 'pchip', 0);
end

f(~isfinite(f)) = 0;
f = max(f,0);

if max(f) <= 0
    % fallback: just create a slim symmetric envelope
    f = ones(size(ygrid));
end

f = f ./ max(f) * halfWidth;

patch(ax, ...
    [x0-f, fliplr(x0+f)], ...
    [ygrid, fliplr(ygrid)], ...
    faceColor, ...
    'FaceAlpha', faceAlpha, ...
    'EdgeColor', faceColor*0.85, ...
    'LineWidth', 0.8);
end

function offsets = cmdo_default_label_offsets_all(x,y)
n = numel(x);
offsets = zeros(n,2);
for i = 1:n
    if mod(i,4)==1
        offsets(i,:) = [ 0.0015,  0.0030];
    elseif mod(i,4)==2
        offsets(i,:) = [ 0.0015, -0.0025];
    elseif mod(i,4)==3
        offsets(i,:) = [-0.0020,  0.0025];
    else
        offsets(i,:) = [ 0.0010,  0.0010];
    end
end
end

function saved = cmdo_load_label_offsets(matFile, defaultOffsets)
saved = defaultOffsets;
if exist(matFile,'file')
    S = load(matFile);
    if isfield(S,'offsets') && isequal(size(S.offsets),size(defaultOffsets))
        saved = S.offsets;
    end
end
end


function labelPos = f6_default_label_positions(strata, x, y)
% Create deterministic, separated locations for all panel-b labels.

strata = string(strata(:));
x = double(x(:));
y = double(y(:));

n = numel(x);
labelPos = NaN(n,2);

xLimits = [min(x)-0.004, max(x)+0.008];
yLimits = [0, max(y)*1.15];

% Positions are fractions of the frozen panel limits. The layout uses
% three compact lanes for the dense low-error cluster and separate lanes
% for the higher-error strata.
fractionByStratum = containers.Map( ...
    { ...
     'ER_PRIOR_UTILIZATION_ZERO', 'ER_ALL', ...
     'ER_RACE_AFRICAN_AMERICAN', 'ER_RACE_CAUCASIAN', ...
     'ER_AGE_GE70', 'ER_MALE', 'ER_DIAGNOSES_GE7', 'ER_FEMALE', ...
     'ER_INSULIN_ACTIVE', 'ER_AGE_50_69', 'ER_LONG_STAY_GE5', ...
     'ER_SHORT_STAY_LE4', 'ER_INSULIN_NONE', ...
     'ER_PRIOR_UTILIZATION_POSITIVE', 'ER_AGE_LT50', ...
     'ER_DIAGNOSES_LE6'}, ...
    { ...
     [0.11 0.25], [0.28 0.16], ...
     [0.11 0.11], [0.28 0.22], ...
     [0.11 0.18], [0.28 0.09], [0.44 0.14], [0.44 0.07], ...
     [0.18 0.34], [0.31 0.39], [0.36 0.29], ...
     [0.43 0.49], [0.48 0.66], ...
     [0.64 0.60], [0.78 0.93], ...
     [0.83 0.80]});

for i = 1:n
    key = char(strata(i));
    if isKey(fractionByStratum,key)
        f = fractionByStratum(key);
    else
        f = [0.50 0.50];
    end
    labelPos(i,:) = [ ...
        xLimits(1) + f(1)*diff(xLimits), ...
        yLimits(1) + f(2)*diff(yLimits)];
end

end


function f6_start_label_drag(labelHandle, figHandle)
% Start dragging one panel-b textbox.

if ~isgraphics(labelHandle) || ~isgraphics(figHandle)
    return;
end

set(figHandle, ...
    'Pointer', 'fleur', ...
    'WindowButtonMotionFcn', ...
    @(~, ~) f6_drag_label(labelHandle), ...
    'WindowButtonUpFcn', ...
    @(~, ~) f6_stop_label_drag(figHandle));

end


function f6_drag_label(labelHandle)
% Move the textbox and continuously update its leader line.

if ~isgraphics(labelHandle)
    return;
end

ax = ancestor(labelHandle, 'axes');

if isempty(ax) || ~isgraphics(ax)
    return;
end

currentPoint = ax.CurrentPoint;

xValue = currentPoint(1,1);
yValue = currentPoint(1,2);

xLimits = ax.XLim;
yLimits = ax.YLim;

% Keep the textbox centre within the plotting area.
xPadding = 0.020 * diff(xLimits);
yPadding = 0.035 * diff(yLimits);

xValue = min( ...
    max(xValue, xLimits(1) + xPadding), ...
    xLimits(2) - xPadding);

yValue = min( ...
    max(yValue, yLimits(1) + yPadding), ...
    yLimits(2) - yPadding);

labelHandle.Position = [xValue, yValue, 0];

anchorPoint = getappdata( ...
    labelHandle, ...
    'AnchorPoint');

leaderHandle = getappdata( ...
    labelHandle, ...
    'LeaderHandle');

if isgraphics(leaderHandle)

    leaderHandle.XData = [anchorPoint(1), xValue];
    leaderHandle.YData = [anchorPoint(2), yValue];
end

drawnow limitrate nocallbacks;

end


function f6_stop_label_drag(figHandle)
% Finish dragging one textbox.

if ~isgraphics(figHandle)
    return;
end

set(figHandle, ...
    'Pointer', 'arrow', ...
    'WindowButtonMotionFcn', '', ...
    'WindowButtonUpFcn', '');

end
