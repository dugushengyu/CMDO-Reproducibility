function Figure5_PRESERVE_PCC(outputDir, repoRoot, pccDataDir)
% CMDO Figure 5 — PRESERVE
% A U9B bridge: fixed-use geometry versus adaptive outcome
% B U10 empirical matched-fixed versus adaptive risk
% C Adaptation frontier: heterogeneity opportunity versus allocation+composition cost

close all;
thisFile=mfilename('fullpath'); if isempty(thisFile), scriptDir=pwd; else, scriptDir=fileparts(thisFile); end
if nargin<2 || isempty(repoRoot), repoRoot=fileparts(fileparts(scriptDir)); end
if nargin<1 || isempty(outputDir), outputDir=fullfile(scriptDir,'output'); end
if nargin<3 || isempty(pccDataDir), pccDataDir=fullfile(repoRoot,'source_data','pcc'); end
if ~isfolder(outputDir), mkdir(outputDir); end

B=readtable(fullfile(pccDataDir,'CMDO_U9_REUSE_PRESERVE_bridge.csv'),'VariableNamingRule','preserve'); B=B(string(B.stage)=="U9B",:); [~,oo]=sort(double(B.budget)); B=B(oo,:);
U10=readtable(fullfile(repoRoot,'U10_Prospective_ECG','02_Posthoc_Diagnostics','U10_DEPENDENCE_DECOMPOSITION.csv'),'VariableNamingRule','preserve');

FONT='Arial'; green=[.02 .48 .20]; red=[.84 .08 .06]; purple=[.44 .20 .72]; blue=[.04 .30 .75]; dark=[.18 .18 .18]; grey=[.48 .48 .48];

% U10 ordered states
dataset=lower(string(U10.dataset)); budget=double(U10.budget); idxG=find(dataset=="georgia"); [~,o]=sort(budget(idxG)); idxG=idxG(o); idxC=find(dataset=="cpsc_2018"); [~,o]=sort(budget(idxC)); idxC=idxC(o);
fixG=1-double(U10.shared_constant_mean_gain_pct(idxG))'/100; adG=1-double(U10.shared_adaptive_gain_pct(idxG))'/100;
fixC=1-double(U10.shared_constant_mean_gain_pct(idxC))'/100; adC=1-double(U10.shared_adaptive_gain_pct(idxC))'/100;

% Adaptation frontier calculations (same empirical measure as frozen analysis)
Bv=double(U10.B); V=double(U10.direct_mse); mw=double(U10.shared_constant_mean_weight); fixedMSE=double(U10.shared_constant_mean_mse);
lam=(Bv.^2)./V; fixedRisk=fixedMSE./V; den=2.*mw.*(1-mw); q=(fixedRisk-(1-mw).^2-lam.*mw.^2)./den;
quad=1+lam-2*q; lin=1-q; wstar=min(1,max(0,lin./quad)); wg=min(1,max(0,mean(lin)/mean(quad)));
risk=@(w)(1-w).^2+lam.*w.^2+2.*w.*(1-w).*q;
rStar=risk(wstar); rGlob=risk(wg*ones(size(mw))); rMean=risk(mw);
Hi=rGlob-rStar; Ai=rMean-rStar; Xi=(double(U10.shared_adaptive_mse)-fixedMSE)./V; XiP=(double(U10.shared_permuted_weight_mse)-fixedMSE)./V;
H=mean(Hi); A=mean(Ai); C=mean(Xi); Cp=mean(XiP); stateCost=Ai+Xi;

fig=figure('Color','w','Position',[35 35 1280 500],'Renderer','painters','Name','CMDO Figure 5 — PRESERVE','NumberTitle','off');
t=tiledlayout(fig,1,3,'TileSpacing','loose','Padding','loose');

% A bridge
ax=nexttile(t,1); hold(ax,'on'); x=double(B.rho_realized_actual_meanweight); y=double(B.observed_adaptive_MSE_gain_pct); bud=double(B.budget);
scatter(ax,x,y,75,red,'filled'); xline(ax,1,'k--','LineWidth',1.2); yline(ax,0,'k:','LineWidth',1.1);
for i=1:numel(x), text(ax,x(i)+.025,y(i),sprintf('%d',bud(i)),'FontName',FONT,'FontSize',9,'Color',dark); end
xlabel(ax,'Post-completion fixed-use coordinate at mean weight, \rho^{real}'); ylabel(ax,'Observed adaptive MSE gain (%)'); title(ax,'Fixed-use geometry vs adaptive outcome','FontSize',11.5); grid(ax,'on');
xlim(ax,[0.58 1.22]); ylim(ax,[-16.5 0.2]);
local_style(ax,FONT); local_letter(fig,ax,'A',red);

% B U10 pairs
ax=nexttile(t,2); hold(ax,'on');

rf=[fixG fixC];
ra=[adG adC];
xx=[1:4 6:9];
budLabels={'128','256','512','1024','128','256','512','1024'};

for i=1:numel(xx)
    plot(ax,[xx(i) xx(i)],[rf(i) ra(i)],'-', ...
        'Color',[.72 .72 .72], ...
        'LineWidth',1.5, ...
        'HandleVisibility','off');
end

hFix=scatter(ax,xx,rf,55,green,'s','filled', ...
    'DisplayName','Matched fixed');

hAd=scatter(ax,xx,ra,55,red,'o','filled', ...
    'DisplayName','Adaptive');

yline(ax,1,'k--','LineWidth',1.1,'HandleVisibility','off');

set(ax,'XTick',xx, ...
       'XTickLabel',budLabels);

xlim(ax,[0.4 9.6]);
ylim(ax,[0.50 1.20]);

xlabel(ax,'Audit budget, m');
ylabel(ax,'Normalized risk, R/V');

title(ax,'Adaptive risk > matched fixed in 8/8 states', ...
    'FontSize',11.5);

legend(ax,[hFix hAd], ...
    'Location','northwest', ...
    'Box','off');

grid(ax,'on');
local_style(ax,FONT);

% cohort labels inside the lower part of the axes
text(ax,0.255,0.12,'Georgia', ...
    'Units','normalized', ...
    'FontName',FONT, ...
    'FontSize',9.0, ...
    'HorizontalAlignment','center', ...
    'VerticalAlignment','middle');

text(ax,0.745,0.12,'CPSC 2018', ...
    'Units','normalized', ...
    'FontName',FONT, ...
    'FontSize',9.0, ...
    'HorizontalAlignment','center', ...
    'VerticalAlignment','middle');

local_letter(fig,ax,'B',red);

% C adaptation frontier
ax=nexttile(t,3); hold(ax,'on');
scatter(ax,Hi,stateCost,50,blue,'filled','MarkerFaceAlpha',.55,'DisplayName','U10 states');
scatter(ax,H,A+C,110,red,'^','filled','MarkerEdgeColor','k','DisplayName','8-state shared adaptive');
scatter(ax,H,A+Cp,110,purple,'d','filled','MarkerEdgeColor','k','DisplayName','pairing disrupted');
mx=max([Hi;stateCost;H;A+C;A+Cp])*.1+max([Hi;stateCost;H;A+C;A+Cp]); plot(ax,[0 mx],[0 mx],'k--','LineWidth',1.1,'DisplayName','H = A + C');
xlabel(ax,'Heterogeneity opportunity, H'); ylabel(ax,'Allocation + composition cost, A + C'); title(ax,'Adaptation frontier','FontSize',11.5); grid(ax,'on'); legend(ax,'Location','north','Box','off');
local_style(ax,FONT); local_letter(fig,ax,'C',red);

png=fullfile(outputDir,'Figure5_PRESERVE_PCC.png'); pdf=fullfile(outputDir,'Figure5_PRESERVE_PCC.pdf'); exportgraphics(fig,png,'Resolution',300); exportgraphics(fig,pdf,'ContentType','vector');
fprintf('Figure 5 written:\n%s\n%s\n',png,pdf);
end
function local_style(ax,FONT), set(ax,'FontName',FONT,'FontSize',9.1,'LineWidth',.8,'TickDir','out','Box','off', ...
    'GridAlpha',0.13,'MinorGridAlpha',0.04,'XMinorGrid','off','YMinorGrid','off'); end
function local_letter(fig,ax,s,c)
drawnow;
p=ax.Position;
x=max(0.006,p(1)-0.030);
y=min(0.938,p(2)+p(4)+0.004);
annotation(fig,'textbox',[x y 0.030 0.035], ...
    'String',s,'LineStyle','none','FitBoxToText','on', ...
    'FontName','Arial','FontSize',14,'FontWeight','bold', ...
    'Color',c,'HorizontalAlignment','left','VerticalAlignment','bottom');
end
