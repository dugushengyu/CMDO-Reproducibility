function ED5
%ED5 Generate CURRENT CMDO Extended Data Figure 5.
% Standalone: reads the frozen canonical ZIP records directly.

close all;
clc;
rng(20260728,'twister');

cfg = cmdo_config('ED5');
DATA_DIR  = cfg.canonicalRecordDir;
CACHE_DIR = fullfile(cfg.cacheRoot,'ED_CURRENT_FINAL');
OUT_DIR   = cfg.extendedOutputDir;

if ~exist(DATA_DIR,'dir')
    error('ED5:MissingData','Canonical record folder not found: %s',DATA_DIR);
end
if ~exist(CACHE_DIR,'dir'), mkdir(CACHE_DIR); end
if ~exist(OUT_DIR,'dir'), mkdir(OUT_DIR); end

U7 = ed_load_u7(DATA_DIR,CACHE_DIR);
ed_make_5(U7,OUT_DIR);

fprintf('\nED5 completed. Output folder:\n%s\n',OUT_DIR);
end


function ed_make_5(U7,outDir)

S = U7.state(string(U7.state.metric)=="AUC",:);
strata = unique(string(S.stratum),'stable');
budgets = sort(unique(S.budget));
G = nan(numel(strata),numel(budgets));
W = nan(size(G));

for i = 1:numel(strata)
    for j = 1:numel(budgets)
        m = string(S.stratum)==strata(i) & S.budget==budgets(j);
        G(i,j) = mean(S.direct_mae(m)-S.mae(m),'omitnan');
        W(i,j) = mean(S.mean_weight(m),'omitnan');
    end
end

stratumLabels = arrayfun(@ed_pretty_stratum,strata,'UniformOutput',false);

fig = figure('Position',[40 40 900 700],'Color','w', ...
    'Name','Extended Data Figure 5','NumberTitle','off');
tl = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');

% a
ax = nexttile(tl,1);
imagesc(ax,G);
colormap(ax,ed_white_to_color([.84 .15 .16],256));
cb = colorbar(ax); cb.Label.String = 'Direct MAE - observer MAE';
xticks(ax,1:numel(budgets)); xticklabels(ax,string(budgets));
yticks(ax,1:numel(strata)); yticklabels(ax,stratumLabels);
xlabel(ax,'Outcome budget');
title(ax,'AUC gain by clinical state','FontWeight','bold');
ed_panel_letter(ax,'a');
ed_style(ax,8.5);

% b
ax = nexttile(tl,2);
imagesc(ax,W);
colormap(ax,ed_white_to_color([.12 .47 .71],256));
cb = colorbar(ax); cb.Label.String = 'Mean transport weight';
xticks(ax,1:numel(budgets)); xticklabels(ax,string(budgets));
yticks(ax,1:numel(strata)); yticklabels(ax,stratumLabels);
xlabel(ax,'Outcome budget');
title(ax,'Transport weight by state','FontWeight','bold');
ed_panel_letter(ax,'b');
ed_style(ax,8.5);

% c
ax = nexttile(tl,3);
transportError = nan(numel(strata),1);
transportSign = nan(numel(strata),1);
for i = 1:numel(strata)
    m = string(S.stratum)==strata(i);
    transportError(i) = mean(S.transport_abs_error(m),'omitnan');
    transportSign(i) = mean(S.transport_metric(m)-S.true_metric(m),'omitnan');
end
barC = barh(ax,transportError,'FaceColor','flat','EdgeColor','none');
colors = repmat([.12 .47 .71],numel(strata),1);
colors(transportSign>0,:) = repmat([.84 .15 .16],nnz(transportSign>0),1);
barC.CData = colors;
set(ax,'YDir','reverse');
yticks(ax,1:numel(strata)); yticklabels(ax,stratumLabels);
xlabel(ax,'Absolute transport error');
title(ax,'Transport bias across strata','FontWeight','bold');
hold(ax,'on');
h1 = scatter(ax,nan,nan,55,[.84 .15 .16],'s','filled');
h2 = scatter(ax,nan,nan,55,[.12 .47 .71],'s','filled');
legend(ax,[h1 h2],{'Transported AUC above truth','Transported AUC below truth'}, ...
    'Location','southeast','Box','off','FontSize',8);
grid(ax,'on');
ed_panel_letter(ax,'c');
ed_style(ax,8.5);

% d
ax = nexttile(tl,4);
gain = S.direct_mae-S.mae;
scatter(ax,S.mean_weight,gain,34,S.transport_abs_error,'filled');
yline(ax,0,'--','Color',[1 0 0],'LineWidth',1.2);
cb = colorbar(ax); cb.Label.String = 'True transport error';
xlabel(ax,'Mean transport weight');
ylabel(ax,'Direct MAE - observer MAE');
title(ax,'Borrowing and realised gain','FontWeight','bold');
grid(ax,'on');
ed_panel_letter(ax,'d');
ed_style(ax,8.5);

ed_save(fig,outDir,'ExtendedData5_U7_Clinical_Detail');
end

function U7 = ed_load_u7(dataDir,cacheDir)
d = ed_extract(dataDir,cacheDir,'StageU7_Canonical_Records_v1.0.zip');
U7.state  = ed_read(d,'StageU7_State_Results_v1.0.csv');
U7.target = ed_read(d,'StageU7_Target_Metric_Summary_v1.0.csv');
U7.metric = ed_read(d,'StageU7_Metric_Summary_v1.0.csv');
U7.rates  = ed_read(d,'StageU7_Label_Complexity_Rates_v1.0.csv');
end

function stageDir = ed_extract(dataDir,cacheDir,zipName)
zipPath = cmdo.find_unique_file(dataDir,zipName);
if ~exist(zipPath,'file')
    error('ED:MissingZip','Missing canonical archive: %s',zipPath);
end
stageDir = fullfile(cacheDir,erase(zipName,'.zip'));
ready = fullfile(stageDir,'.ready');
if ~exist(ready,'file')
    if exist(stageDir,'dir'), rmdir(stageDir,'s'); end
    mkdir(stageDir);
    unzip(zipPath,stageDir);
    fid = fopen(ready,'w');
    if fid>0, fprintf(fid,'ready\n'); fclose(fid); end
end
end

function T = ed_read(stageDir,fileName)
hits = dir(fullfile(stageDir,'**',fileName));
if isempty(hits)
    error('ED:MissingCSV','CSV not found after extraction: %s',fileName);
end
T = readtable(fullfile(hits(1).folder,hits(1).name), ...
    'VariableNamingRule','preserve');
end

function ed_save(fig,outDir,stem)
drawnow;
exportgraphics(fig,fullfile(outDir,[stem '.png']), ...
    'Resolution',300,'BackgroundColor','white');
exportgraphics(fig,fullfile(outDir,[stem '.tiff']), ...
    'Resolution',300,'BackgroundColor','white');
exportgraphics(fig,fullfile(outDir,[stem '.pdf']), ...
    'ContentType','vector','BackgroundColor','white');
savefig(fig,fullfile(outDir,[stem '.fig']));
fprintf('Saved: %s\n',stem);
end

function ed_style(ax,fontSize)
set(ax,'FontName','Arial','FontSize',fontSize, ...
    'LineWidth',.85,'TickDir','out','Box','off','Layer','top');
end

function ed_panel_letter(ax,s)
text(ax,-.11,1.06,s,'Units','normalized','FontName','Arial', ...
    'FontSize',15,'FontWeight','bold','HorizontalAlignment','left', ...
    'VerticalAlignment','top','Clipping','off');
end

function ed_violin(ax,x0,v,faceColor,halfWidth,faceAlpha)
v = double(v(:));
v = v(isfinite(v));
if numel(v)<2, return; end

vmin = min(v); vmax = max(v);
if vmax<=vmin
    vmin = vmin-1e-6; vmax = vmax+1e-6;
end
yg = linspace(vmin,vmax,180)';
sd = std(v,0);
bw = 1.06*sd*numel(v)^(-1/5);
if ~isfinite(bw) || bw<=0, bw=max((vmax-vmin)/20,eps); end
Z = bsxfun(@minus,yg,v')/bw;
f = mean(exp(-.5*Z.^2),2)/(bw*sqrt(2*pi));
if max(f)<=0 || ~all(isfinite(f)), f=ones(size(f)); end
w = halfWidth*f/max(f);
patch(ax,[x0-w;flipud(x0+w)],[yg;flipud(yg)],faceColor, ...
    'FaceAlpha',faceAlpha,'EdgeColor',[.45 .45 .45], ...
    'LineWidth',.6,'HandleVisibility','off');
end

function q = ed_quantile(v,p)
v = sort(double(v(:)));
v = v(isfinite(v));
if isempty(v), q=NaN; return; end
if numel(v)==1, q=v; return; end
r = 1 + (numel(v)-1)*p;
lo = floor(r); hi = ceil(r);
if lo==hi
    q = v(lo);
else
    q = v(lo)+(r-lo)*(v(hi)-v(lo));
end
end

function cmap = ed_diverging_map(n)
if nargin<1, n=256; end
n1 = floor(n/2); n2 = n-n1;
blue = [.12 .47 .71]; white = [1 1 1]; red = [.84 .15 .16];
c1 = [linspace(blue(1),white(1),n1)', ...
      linspace(blue(2),white(2),n1)', ...
      linspace(blue(3),white(3),n1)'];
c2 = [linspace(white(1),red(1),n2)', ...
      linspace(white(2),red(2),n2)', ...
      linspace(white(3),red(3),n2)'];
cmap = [c1;c2];
end


function cmap = ed_white_to_color(targetColor,n)
if nargin<2, n=256; end
targetColor = double(targetColor(:)');
cmap = [linspace(1,targetColor(1),n)', ...
        linspace(1,targetColor(2),n)', ...
        linspace(1,targetColor(3),n)'];
end

function s = ed_short_u4(x)
x = string(x);
switch x
    case "EMNIST_DIGITS", s='EMNIST DIGITS';
    case "QMNIST_TEST50K", s='QMNIST TEST50K';
    case "GENRE_facetoface", s='facetoface';
    case "GENRE_letters", s='letters';
    case "GENRE_nineeleven", s='nineeleven';
    case "GENRE_oup", s='oup';
    case "GENRE_verbatim", s='verbatim';
    otherwise, s=char(x);
end
end

function s = ed_short_u6(x)
x = string(x);
switch x
    case "ACS_PUBLIC_COVERAGE_2024_FL", s='ACS-FL';
    case "ACS_PUBLIC_COVERAGE_2024_IL", s='ACS-IL';
    case "ACS_PUBLIC_COVERAGE_2024_OH", s='ACS-OH';
    case "ACS_PUBLIC_COVERAGE_2024_PA", s='ACS-PA';
    case "ACS_PUBLIC_COVERAGE_2024_TX", s='ACS-TX';
    case "DERMA_CLEAN", s='Derma-clean';
    case "DERMA_NOISE_0_08", s='Derma-noise';
    case "DERMA_BLUR_1_0", s='Derma-blur';
    case "DERMA_GAMMA_1_4", s='Derma-gamma';
    case "DERMA_JPEG_35", s='Derma-JPEG';
    case "DERMA_DOWNSAMPLE_14", s='Derma-downsample';
    case "CIFAR_CAT_DOG_CLEAN", s='CIFAR-clean';
    case "CIFAR_CAT_DOG_GRAYSCALE", s='CIFAR-greyscale';
    case "CIFAR_CAT_DOG_NOISE_0_10", s='CIFAR-noise';
    case "CIFAR_CAT_DOG_BLUR_1_2", s='CIFAR-blur';
    case "CIFAR_CAT_DOG_JPEG_30", s='CIFAR-JPEG';
    otherwise, s=char(replace(x,"_","-"));
end
end

function s = ed_pretty_stratum(x)
x = string(x);
switch x
    case "ER_AGE_50_69", s='Age 50-69';
    case "ER_AGE_GE70", s='Age >=70';
    case "ER_AGE_LT50", s='Age <50';
    case "ER_ALL", s='All ER';
    case "ER_DIAGNOSES_GE7", s='Diagnoses >=7';
    case "ER_DIAGNOSES_LE6", s='Diagnoses <=6';
    case "ER_FEMALE", s='Female';
    case "ER_INSULIN_ACTIVE", s='Insulin active';
    case "ER_INSULIN_NONE", s='No insulin';
    case "ER_LONG_STAY_GE5", s='Stay >=5 d';
    case "ER_MALE", s='Male';
    case "ER_PRIOR_UTILIZATION_POSITIVE", s='Prior use >0';
    case "ER_PRIOR_UTILIZATION_ZERO", s='Prior use =0';
    case "ER_RACE_AFRICAN_AMERICAN", s='African American';
    case "ER_RACE_CAUCASIAN", s='Caucasian';
    case "ER_SHORT_STAY_LE4", s='Stay <=4 d';
    otherwise, s=char(replace(x,"_"," "));
end
end

function out = ternary(cond,a,b)
if cond, out=a; else, out=b; end
end
