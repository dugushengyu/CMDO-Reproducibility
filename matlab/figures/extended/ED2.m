function ED2
%ED2 Generate CURRENT CMDO Extended Data Figure 2.
% Standalone: reads the frozen canonical ZIP records directly.

close all;
clc;
rng(20260728,'twister');

cfg = cmdo_config('ED2');
DATA_DIR  = cfg.canonicalRecordDir;
CACHE_DIR = fullfile(cfg.cacheRoot,'ED_CURRENT_FINAL');
OUT_DIR   = cfg.extendedOutputDir;

if ~exist(DATA_DIR,'dir')
    error('ED2:MissingData','Canonical record folder not found: %s',DATA_DIR);
end
if ~exist(CACHE_DIR,'dir'), mkdir(CACHE_DIR); end
if ~exist(OUT_DIR,'dir'), mkdir(OUT_DIR); end

U5B = ed_load_u5b(DATA_DIR,CACHE_DIR);
ed_make_2(U5B,OUT_DIR);

fprintf('\nED2 completed. Output folder:\n%s\n',OUT_DIR);
end


function ed_make_2(U5B,outDir)

S = U5B.state;
fig = figure('Position',[40 40 900 800],'Color','w', ...
    'Name','Extended Data Figure 2','NumberTitle','off');

% Fixed layout: a/c left edges aligned, b/d left edges aligned
axA = axes(fig,'Units','normalized', ...
    'Position',[0.075 0.555 0.350 0.365]);

axB = axes(fig,'Units','normalized', ...
    'Position',[0.570 0.555 0.315 0.365]);

axC = axes(fig,'Units','normalized', ...
    'Position',[0.075 0.085 0.350 0.365]);

axD = axes(fig,'Units','normalized', ...
    'Position',[0.570 0.085 0.315 0.365]);

families = ["ACS_INCOME_2022","AMAZON_LANGUAGES","MEDICAL_XRAY"];
familyLabels = {'Population','Language','Medical'};
methodLabels = {'Direct','Static','Label-free','Sentinel','Oracle'};
methodCols = {'direct_mae','static_mae','label_free_mae','sentinel_mae','oracle_mae'};

% a
ax = axA;
Y = nan(3,5);
for i = 1:3
    m = string(S.family)==families(i);
    for j = 1:5
        Y(i,j) = mean(S.(methodCols{j})(m),'omitnan');
    end
end
bar(ax,Y,'grouped');
xticks(ax,1:3); xticklabels(ax,familyLabels);
ylabel(ax,'Mean AUC MAE');
title(ax,'Method error across families','FontWeight','bold');
legend(ax,methodLabels, ...
    'Location','northeast', ...
    'NumColumns',1, ...
    'Box','off');
grid(ax,'on');
ed_panel_letter(fig,ax,'a');
ed_style(ax,9);

% b
ax = axB;
scatter(ax,S.mean_sentinel_bias_sq,S.mean_sentinel_weight,34, ...
    S.transport_abs_error,'filled');
set(ax,'XScale','log');
cb = colorbar(ax);
cb.Label.String = 'True transport error';

% Restore the main axes after colorbar creation
ax.Position = [0.570 0.555 0.315 0.365];

% Dedicated colour-bar location
cb.Units = 'normalized';
cb.Position = [0.905 0.555 0.016 0.365];
xlabel(ax,'Sentinel estimated bias^2');
ylabel(ax,'Mean sentinel weight');
title(ax,'Borrowing contracts with sensed bias','FontWeight','bold');
grid(ax,'on');
ed_panel_letter(fig,ax,'b');
ed_style(ax,9);

% c
ax = axC;
scatter(ax,S.transport_abs_error,S.sentinel_gain_vs_direct,34, ...
    S.mean_sentinel_weight,'filled');
yline(ax,0,'--','Color',[1 0 0],'LineWidth',1.2);
cb = colorbar(ax);
cb.Label.String = 'Mean sentinel weight';

% Restore the main axes after colorbar creation
ax.Position = [0.075 0.085 0.350 0.365];

% Dedicated colour-bar location
cb.Units = 'normalized';
cb.Position = [0.445 0.085 0.016 0.365];
xlabel(ax,'True transport absolute error');
ylabel(ax,'Sentinel gain versus direct');
title(ax,'Utility falls as transport bias grows','FontWeight','bold');
grid(ax,'on');
ed_panel_letter(fig,ax,'c');
ed_style(ax,9);

% d
ax = axD;
hold(ax,'on');
vals = { ...
    S.static_mae-S.direct_mae, ...
    S.label_free_mae-S.direct_mae, ...
    S.sentinel_mae-S.direct_mae};
labels = {'Static','Label-free','Sentinel'};
colors = [1 .50 .05; .20 .63 .25; .84 .15 .16];

for k = 1:3
    v = vals{k};
    ed_violin(ax,k,v,[.75 .75 .75],.34,.38);
    scatter(ax,k+.055*randn(size(v)),v,17,colors(k,:),'filled', ...
        'MarkerEdgeColor','none','MarkerFaceAlpha',.72);
    med = median(v,'omitnan');
    plot(ax,[k-.20 k+.20],[med med],'k-','LineWidth',1.8);
end
yline(ax,0,'--','Color',[1 0 0],'LineWidth',1.2);
xticks(ax,1:3); xticklabels(ax,labels);
ylabel(ax,'MAE regret versus direct');
title(ax,'Sparse outcomes improve tail safety','FontWeight','bold');
grid(ax,'on');
ed_panel_letter(fig,ax,'d');
ed_style(ax,9);

ed_save(fig,outDir,'ExtendedData2_U5B_Mechanism');
end

function U5B = ed_load_u5b(dataDir,cacheDir)
d = ed_extract(dataDir,cacheDir,'StageU5B_Canonical_Records_v1.0.zip');
U5B.state = ed_read(d,'StageU5B_Audit_State_Results_v1.0.csv');
end

function stageDir = ed_extract(dataDir,cacheDir,zipName)
zipPath = fullfile(dataDir,zipName);
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

function ed_panel_letter(fig,ax,s)
% Robust panel letter placed outside the axes using figure annotation.

drawnow;  % ensure ax.Position is updated
pos = ax.Position;   % [left bottom width height] in normalized figure units

x = pos(1) - 0.048;
y = pos(2) + pos(4) + 0.008;

annotation(fig,'textbox',[x y 0.03 0.03], ...
    'String',s, ...
    'LineStyle','none', ...
    'FitBoxToText','off', ...
    'FontName','Arial', ...
    'FontSize',15, ...
    'FontWeight','bold', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','middle');
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
