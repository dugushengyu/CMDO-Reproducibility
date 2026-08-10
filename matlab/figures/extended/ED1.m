function ED1
%ED1 Generate CURRENT CMDO Extended Data Figure 1.
% Standalone: reads the frozen canonical ZIP records directly.

close all;
clc;
rng(20260728,'twister');

cfg = cmdo_config('ED1');
DATA_DIR  = cfg.canonicalRecordDir;
CACHE_DIR = fullfile(cfg.cacheRoot,'ED_CURRENT_FINAL');
OUT_DIR   = cfg.extendedOutputDir;

if ~exist(DATA_DIR,'dir')
    error('ED1:MissingData','Canonical record folder not found: %s',DATA_DIR);
end
if ~exist(CACHE_DIR,'dir'), mkdir(CACHE_DIR); end
if ~exist(OUT_DIR,'dir'), mkdir(OUT_DIR); end

U4 = ed_load_u4(DATA_DIR,CACHE_DIR);
ed_make_1(U4,OUT_DIR);

fprintf('\nED1 completed. Output folder:\n%s\n',OUT_DIR);
end


function ed_make_1(U4,outDir)

fig = figure('Position',[40 40 900 800],'Color','w', ...
    'Name','Extended Data Figure 1','NumberTitle','off');
tl = tiledlayout(fig,2,2, ...
    'TileSpacing','compact', ...
    'Padding','loose');

% a
ax = nexttile(tl,1);
pred = U4.pred;
targetOrder = [ ...
    "EMNIST_DIGITS","FL","GENRE_facetoface","GENRE_letters", ...
    "GENRE_nineeleven","GENRE_oup","GENRE_verbatim","IL","NY", ...
    "QMNIST_TEST50K","SVHN","TX","USPS"];
budgets = sort(unique(pred.budget));
H = nan(numel(targetOrder),numel(budgets));

for i = 1:numel(targetOrder)
    for j = 1:numel(budgets)
        m = string(pred.target)==targetOrder(i) & pred.budget==budgets(j);
        if any(m)
            uerr = abs(pred.component_pred(m)-pred.truth_direct_mae(m));
            rerr = abs(pred.rootn_pred(m)-pred.truth_direct_mae(m));
            H(i,j) = mean(uerr-rerr,'omitnan');
        end
    end
end

imagesc(ax,H);
colormap(ax,ed_diverging_map(256));
lim = max(abs(H(:)),[],'omitnan');
if ~isfinite(lim) || lim==0, lim=1; end
caxis(ax,[-lim lim]);
cb = colorbar(ax);
cb.Label.String = 'Universal-law MAE minus root-budget MAE';
xticks(ax,1:numel(budgets));
xticklabels(ax,string(budgets));
yticks(ax,1:numel(targetOrder));
yticklabels(ax,arrayfun(@ed_short_u4,targetOrder,'UniformOutput',false));
xlabel(ax,'Outcome budget');
title(ax,'Universal law versus root-budget baseline','FontWeight','bold');
ed_panel_letter(ax,'a');
ed_style(ax,9);

% b
ax = nexttile(tl,2);
hold(ax,'on');
F = U4.fits;
x = F.rootn_late_mae;
y = F.component_late_mae;
better = y < x;
lo = min([x;y],[],'omitnan');
hi = max([x;y],[],'omitnan');
plot(ax,[lo hi],[lo hi],'--','Color',[.45 .45 .45],'LineWidth',1.2, ...
    'DisplayName','Parity line');
scatter(ax,x(better),y(better),48,[.12 .47 .71],'filled', ...
    'DisplayName',sprintf('Universal law better (%d/13)',nnz(better)));
scatter(ax,x(~better),y(~better),48,[.84 .15 .16],'filled', ...
    'DisplayName',sprintf('Root-budget better (%d/13)',nnz(~better)));
xlim(ax,[0 hi*1.04]); ylim(ax,[0 hi*1.04]);
xlabel(ax,'Root-budget late MAE');
ylabel(ax,'Universal-law late MAE');
title(ax,'Late-budget paired comparison','FontWeight','bold');
legend(ax,'Location','southeast','Box','off');
grid(ax,'on');
ed_panel_letter(ax,'b');
ed_style(ax,9);

% c
ax = nexttile(tl,3);
hold(ax,'on');
E = U4.expiry;
xp = min(max(E.predicted_expiry_budget_from_budget8,8),256);
yp = min(max(E.empirical_expiry_budget,8),256);
insideRaw = E.within_one_budget_level;

if islogical(insideRaw)
    inside = insideRaw;

elseif isnumeric(insideRaw)
    inside = insideRaw ~= 0;

else
    % Handles cell arrays, strings and categorical values such as
    % True / False, TRUE / FALSE, 1 / 0, Yes / No.
    insideText = lower(strtrim(string(insideRaw)));

    inside = ismember( ...
        insideText, ...
        ["true","1","yes","y"]);
end

inside = inside(:);
plot(ax,[8 256],[8 256],'--','Color',[.45 .45 .45],'LineWidth',1.2, ...
    'DisplayName','Parity line');
scatter(ax,xp(inside),yp(inside),46,[.12 .47 .71],'filled', ...
    'DisplayName',sprintf('Within one budget step (%d/13)',nnz(inside)));
scatter(ax,xp(~inside),yp(~inside),46,[1 .50 .05],'filled', ...
    'DisplayName',sprintf('>1-step miss (%d/13)',nnz(~inside)));
set(ax,'XScale','log','YScale','log');
ticks = [8 16 32 64 128 256];
xticks(ax,ticks); yticks(ax,ticks);
xlim(ax,[8 256]); ylim(ax,[8 256]);
xlabel(ax,'Predicted expiry budget');
ylabel(ax,'Empirical expiry budget');
title(ax,'Evidence expiry is not universal','FontWeight','bold');
legend(ax,'Location','southoutside','Box','off');
text(ax,.03,.08,'All 13 targets shown','Units','normalized', ...
    'FontAngle','italic','Color',[.35 .35 .35]);
grid(ax,'on');
ed_panel_letter(ax,'c');
ed_style(ax,9);

% d
ax = nexttile(tl,4);
hold(ax,'on');
A = U4.audit;
families = ["ACS_INCOME","MULTINLI_GENRES","DIGITS"];
familyLabels = {'Population','Language','Vision'};
familyColors = [.12 .47 .71; 1 .50 .05; .20 .63 .25];

for k = 1:3
    m = string(A.family)==families(k);
    values = A.static_fusion_mae(m)-A.direct_mae(m);
    ed_violin(ax,k,values,[.75 .75 .75],.34,.38);
    jitter = .055*randn(size(values));
    scatter(ax,k+jitter,values,18,familyColors(k,:),'filled', ...
        'MarkerEdgeColor','none','MarkerFaceAlpha',.75);
    med = median(values,'omitnan');
    plot(ax,[k-.20 k+.20],[med med],'k-','LineWidth',1.8);
end
yline(ax,0,'--','Color',[1 0 0],'LineWidth',1.2);
xticks(ax,1:3); xticklabels(ax,familyLabels);
ylabel(ax,'Label-free MAE - direct MAE');
title(ax,'Outcome-free transport can be unsafe','FontWeight','bold');
grid(ax,'on');
ed_panel_letter(ax,'d');
ed_style(ax,9);

ed_save(fig,outDir,'ExtendedData1_Prospective_Rejection');
end

function U4 = ed_load_u4(dataDir,cacheDir)
d = ed_extract(dataDir,cacheDir,'StageU4C_Canonical_Records_v1.1.zip');
U4.audit  = ed_read(d,'StageU4C_Audit_State_Results_v1.1.csv');
U4.fits   = ed_read(d,'StageU4C_Component_Fits_v1.1.csv');
U4.pred   = ed_read(d,'StageU4C_Component_Trajectory_Predictions_v1.1.csv');
U4.expiry = ed_read(d,'StageU4C_Evidence_Expiry_Map_v1.1.csv');
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
% Place panel letter clearly outside the upper-left corner of each axes.

text(ax, ...
    -0.20, ...   % move farther left
     1.12, ...   % move farther upward
    s, ...
    'Units','normalized', ...
    'FontName','Arial', ...
    'FontSize',15, ...
    'FontWeight','bold', ...
    'HorizontalAlignment','left', ...
    'VerticalAlignment','top', ...
    'Clipping','off');
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
