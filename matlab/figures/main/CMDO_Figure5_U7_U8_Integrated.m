function CMDO_Figure5_U7_U8_Integrated(sourceWorkbook, outputDir)
%CMDO_FIGURE5_U7_U8_INTEGRATED Build revised main Figure 5.
%
% The figure combines the separately sealed U7 clinical transition with the
% U8 natural-prevalence temporal reserve. All plotted values are read from
% SourceData_Figure5_U7_U8_and_ED7_U8.xlsx; no result is hard-coded.
%
% Usage:
%   CMDO_Figure5_U7_U8_Integrated
%   CMDO_Figure5_U7_U8_Integrated('SourceData_Figure5_U7_U8_and_ED7_U8.xlsx')
%   CMDO_Figure5_U7_U8_Integrated(sourceWorkbook, outputDir)

if nargin < 1 || strlength(string(sourceWorkbook)) == 0
    sourceWorkbook = fullfile(cmdo.repo_root(), 'source_data', ...
        'SourceData_Figure5_U7_U8_and_ED7_U8.xlsx');
end
if nargin < 2 || strlength(string(outputDir)) == 0
    cfg = cmdo_config('Figure5_U7_U8');
    outputDir = cfg.outputDir;
end
if ~isfile(sourceWorkbook)
    error('CMDO:MissingSourceWorkbook', ...
        'Source workbook not found: %s', sourceWorkbook);
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end

U7 = readtable(sourceWorkbook, 'Sheet', 'U7_Strata', ...
    'VariableNamingRule', 'preserve');
S = readtable(sourceWorkbook, 'Sheet', 'U8_State', ...
    'VariableNamingRule', 'preserve');
C = readtable(sourceWorkbook, 'Sheet', 'U8_Cycles', ...
    'VariableNamingRule', 'preserve');

U7.clinical_stratum = string(U7.clinical_stratum);
S.cycle = string(S.cycle);
C.cycle = string(C.cycle);

u7Improved = sum(U7.observer_mae < U7.direct_mae);
u7Reduction = 100 .* (mean(U7.direct_mae) - mean(U7.observer_mae)) ./ mean(U7.direct_mae);
u8Improved = sum(S.observer_mae < S.direct_mae);
u8Reduction = 100 .* (mean(S.direct_mae) - mean(S.observer_mae)) ./ mean(S.direct_mae);
meanCoverage = mean(S.simultaneous_coverage);
minCoverage = min(S.simultaneous_coverage);
certificateViolations = sum(S.covered_event_certificate_violations);
worstRegret = max(S.regret);
maxFallback = max(abs(S.maximum_fallback_residual));

cycleOrder = ["NHANES_2015_2016", "NHANES_2017_2018", "NHANES_2021_2023"];
cycleLabels = ["2015-2016", "2017-2018", "2021-2023"];
cycleColors = [0.1216 0.4667 0.7059; 0.9294 0.4941 0.1922; 0.3294 0.6275 0.4118];
directColor = [0.25 0.33 0.43];
observerColor = [0.86 0.33 0.10];

fig = figure('Color', 'w', 'Position', [30 30 1160 920], ...
    'Renderer', 'painters', 'Name', 'CMDO revised Figure 5', ...
    'NumberTitle', 'off');
tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'loose', 'Padding', 'loose');
tl.OuterPosition = [0.06 0.10 0.90 0.87];

%% a — U7 clinical transition
ax = nexttile(tl, 1); hold(ax, 'on');
[~, ord] = sort(U7.relative_gain, 'descend');
U7p = U7(ord, :);
x = 1:height(U7p);
for i = 1:height(U7p)
    plot(ax, [i i], [U7p.observer_mae(i) U7p.direct_mae(i)], '-', ...
        'Color', [0.78 0.78 0.78], 'LineWidth', 0.8, 'HandleVisibility', 'off');
end
scatter(ax, x, U7p.direct_mae, 34, 'o', 'MarkerFaceColor', 'w', ...
    'MarkerEdgeColor', directColor, 'LineWidth', 1.1, ...
    'DisplayName', 'Full direct');
scatter(ax, x, U7p.observer_mae, 34, 'o', 'MarkerFaceColor', observerColor, ...
    'MarkerEdgeColor', 'w', 'LineWidth', 0.6, 'DisplayName', 'Guarded observer');
xticks(ax, []);
xlabel(ax, 'Clinical stratum (ordered by gain)');
ylabel(ax, 'AUC MAE');
title(ax, 'Clinical transition (U7)', 'FontWeight', 'bold');
legend(ax, 'Location', 'northwest', 'Box', 'off', 'FontSize', 8);
text(ax, 0.98, 0.11, sprintf('%d/%d improved\nPooled MAE -%.2f%%', ...
    u7Improved, height(U7), u7Reduction), 'Units', 'normalized', ...
    'HorizontalAlignment', 'right', 'Color', [0.10 0.50 0.22], ...
    'FontWeight', 'bold', 'FontSize', 8, ...
    'BackgroundColor', 'w', 'Margin', 2);
cmdo_axes(ax); cmdo_panel(ax, 'a');

%% b — U8 natural-prevalence performance
ax = nexttile(tl, 2); hold(ax, 'on');
for k = 1:numel(cycleOrder)
    T = S(S.cycle == cycleOrder(k), :);
    [~, o] = sort(T.budget); T = T(o, :);
    plot(ax, T.budget, T.direct_mae, '--o', 'Color', cycleColors(k,:), ...
        'LineWidth', 1.2, 'MarkerFaceColor', 'w', 'MarkerSize', 5, ...
        'HandleVisibility', 'off');
    plot(ax, T.budget, T.observer_mae, '-o', 'Color', cycleColors(k,:), ...
        'LineWidth', 2.0, 'MarkerFaceColor', cycleColors(k,:), 'MarkerSize', 5, ...
        'DisplayName', cycleLabels(k));
end
set(ax, 'XScale', 'log', 'YScale', 'log');
xticks(ax, unique(S.budget)); xticklabels(ax, string(unique(S.budget)));
xlabel(ax, 'Screened-case budget'); ylabel(ax, 'Accuracy MAE');
title(ax, 'Natural-prevalence reserve (U8)', 'FontWeight', 'bold');
legend(ax, 'Location', 'southwest', 'Box', 'off', 'FontSize', 8);
text(ax, 0.98, 0.96, {'solid: observer; dashed: direct'; ...
    sprintf('%d/%d improved; pooled reduction %.2f%%', u8Improved, height(S), u8Reduction)}, ...
    'Units', 'normalized', 'HorizontalAlignment', 'right', 'VerticalAlignment', 'top', ...
    'FontSize', 8.5, 'BackgroundColor', 'w', 'Margin', 3);
cmdo_axes(ax); cmdo_panel(ax, 'b');

%% c — transport mismatch and guarded borrowing
ax = nexttile(tl, 3); hold(ax, 'on');
[~, idx] = ismember(cycleOrder, C.cycle);
Cc = C(idx, :);
yyaxis(ax, 'left');
b = bar(ax, 1:3, 100 .* Cc.historical_accuracy_bias, 0.52, ...
    'FaceColor', [0.72 0.82 0.92], 'EdgeColor', [0.25 0.43 0.64]);
ylabel(ax, 'Historical accuracy mismatch (percentage points)');
ax.YAxis(1).Color = [0.20 0.37 0.58];
yyaxis(ax, 'right');
p = plot(ax, 1:3, Cc.mean_weight, '-o', 'Color', observerColor, ...
    'MarkerFaceColor', observerColor, 'MarkerEdgeColor', 'w', ...
    'LineWidth', 2.2, 'MarkerSize', 7);
ylabel(ax, 'Mean transport weight');
ax.YAxis(2).Color = observerColor;
xticks(ax, 1:3); xticklabels(ax, {'15-16', '17-18', '21-23'});
title(ax, 'Guarded borrowing under shift', 'FontWeight', 'bold');
legend(ax, [b p], {'Historical mismatch', 'Guarded weight'}, ...
    'Location', 'northwest', 'Box', 'off', 'FontSize', 8);
cmdo_axes(ax); cmdo_panel(ax, 'c');

%% d — certificate coverage and exact fallback
ax = nexttile(tl, 4);
M = nan(3, 4);
budgets = sort(unique(S.budget));
for k = 1:3
    for j = 1:numel(budgets)
        r = S.cycle == cycleOrder(k) & S.budget == budgets(j);
        M(k,j) = S.simultaneous_coverage(r);
    end
end
imagesc(ax, budgets, 1:3, M, [0.85 1.00]);
colormap(ax, cmdo_blue_map(256));
cb = colorbar(ax); cb.Label.String = 'Simultaneous coverage';
xticks(ax, budgets); xticklabels(ax, string(budgets));
yticks(ax, 1:3); yticklabels(ax, cycleLabels);
xlabel(ax, 'Screened-case budget');
title(ax, 'Certificate coverage', 'FontWeight', 'bold');
for k = 1:3
    for j = 1:4
        text(ax, budgets(j), k, sprintf('%.3f', M(k,j)), ...
            'HorizontalAlignment', 'center', 'FontWeight', 'bold', ...
            'Color', cmdo_contrast(M(k,j)), 'FontSize', 7.5);
    end
end
text(ax, 0.02, -0.14, ...
    sprintf(['Mean/min coverage %.3f/%.3f   |   certificate violations %d\n' ...
             'Worst state regret %.6f   |   maximum fallback residual %.3g'], ...
             meanCoverage, minCoverage, certificateViolations, worstRegret, maxFallback), ...
    'Units', 'normalized', 'FontSize', 8.8, 'VerticalAlignment', 'top');
set(ax, 'TickLength', [0 0], 'Box', 'off', 'FontName', 'Arial', 'FontSize', 9);
cmdo_panel(ax, 'd');

exportgraphics(fig, fullfile(outputDir, 'Figure5_U7_U8_Integrated.pdf'), ...
    'ContentType', 'vector');
exportgraphics(fig, fullfile(outputDir, 'Figure5_U7_U8_Integrated.png'), ...
    'Resolution', 600);
exportgraphics(fig, fullfile(outputDir, 'Figure5_U7_U8_Integrated.tiff'), ...
    'Resolution', 600);
savefig(fig, fullfile(outputDir, 'Figure5_U7_U8_Integrated.fig'));
fprintf('Wrote revised Figure 5 to %s\n', outputDir);
end

function labels = cmdo_short_strata(labels)
labels = replace(labels, "Age 50–69", "Age 50-69");
labels = replace(labels, "Age 70 or older", "Age >=70");
labels = replace(labels, "Age under 50", "Age <50");
labels = replace(labels, "Diagnoses 7 or more", "Dx >=7");
labels = replace(labels, "Diagnoses 6 or fewer", "Dx <=6");
labels = replace(labels, "Prior utilisation positive", "Prior use >0");
labels = replace(labels, "Prior utilisation zero", "Prior use 0");
labels = replace(labels, "Long stay, 5 days or more", "Stay >=5 d");
labels = replace(labels, "Short stay, 4 days or fewer", "Stay <=4 d");
labels = replace(labels, "African American", "African Am.");
end

function cmdo_axes(ax)
set(ax, 'FontName', 'Arial', 'FontSize', 9, 'Box', 'off', ...
    'TickDir', 'out', 'LineWidth', 0.8, 'Layer', 'top');
grid(ax, 'on'); ax.GridAlpha = 0.10; ax.GridColor = [0.4 0.4 0.4];
end

function cmdo_panel(ax, letter)
text(ax, -0.10, 1.05, letter, 'Units', 'normalized', ...
    'FontName', 'Arial', 'FontWeight', 'bold', 'FontSize', 15, ...
    'HorizontalAlignment', 'left', 'VerticalAlignment', 'bottom', ...
    'Clipping', 'off');
end

function c = cmdo_contrast(v)
if v < 0.93, c = [0.08 0.08 0.08]; else, c = [1 1 1]; end
end

function map = cmdo_blue_map(n)
x = linspace(0,1,n)';
map = [0.88-0.62*x, 0.94-0.50*x, 1.00-0.25*x];
map = max(0, min(1, map));
end
