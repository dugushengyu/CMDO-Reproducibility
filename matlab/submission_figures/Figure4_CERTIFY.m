function Figure4_CERTIFY(outputDir, pccDataDir)
% CMDO Figure 4 — CERTIFY
% A Parameter-only robust certifiability boundary
% B Exact finite-sample certification cost and phase classes
% C Certification information-cost scaling
% D Retrospective projection of completed CMDO states

close all;
thisFile=mfilename('fullpath'); if isempty(thisFile), scriptDir=pwd; else, scriptDir=fileparts(thisFile); end
if nargin<1 || isempty(outputDir), outputDir=fullfile(scriptDir,'output'); end
if nargin<2 || isempty(pccDataDir), pccDataDir=fullfile(fileparts(scriptDir),'source_data','pcc'); end
if ~isfolder(outputDir), mkdir(outputDir); end

F=readtable(fullfile(pccDataDir,'PCC_frontier_classified.csv'),'VariableNamingRule','preserve');
S=readtable(fullfile(pccDataDir,'PCC_scaling_summary_v12.csv'),'VariableNamingRule','preserve');
A=readtable(fullfile(pccDataDir,'CMDO_185_realized_projection.csv'),'VariableNamingRule','preserve');

FONT='Arial'; purple=[.44 .20 .72]; blue=[.04 .30 .75]; green=[.02 .48 .20]; red=[.82 .08 .06]; orange=[.92 .48 .07]; grey=[.48 .48 .48]; dark=[.18 .18 .18];
w0=.05; tauw=2/w0-1;

fig=figure('Color','w','Position',[35 30 1120 780],'Renderer','painters','Name','CMDO Figure 4 — CERTIFY','NumberTitle','off');
t=tiledlayout(fig,2,2,'TileSpacing','compact','Padding','loose');

% A theoretical boundary
ax=nexttile(t,1); hold(ax,'on');
mFine=logspace(log10(16),log10(512),300); ths=[.65 .75 .85]; cols=[blue;purple;orange];
for j=1:numel(ths)
    dc=zeros(size(mFine));
    for k=1:numel(mFine), mm=max(2,round(mFine(k))); dc(k)=sqrt(tauw*auc_var_lower_bound(ths(j),mm,mm)); end
    plot(ax,mFine,dc,'LineWidth',1.8,'Color',cols(j,:),'DisplayName',sprintf('AUC %.2f',ths(j)));
end
set(ax,'XScale','log'); xlabel(ax,'Future audit size per class, m'); ylabel(ax,'Critical |h-\theta|');
title(ax,'Robust certifiability boundary','FontSize',11.5); legend(ax,'Location','southwest','Box','off'); grid(ax,'on');
local_style(ax,FONT); local_letter(fig,ax,'A',purple);

% B exact cost map at theta=.75
ax=nexttile(t,2); hold(ax,'on'); q=F(abs(double(F.AUC_true)-.75)<1e-12,:);
finite=isfinite(double(q.C_labels)); structural=string(q.status)=="structurally_noncertifiable"; cens=string(q.status)=="safe_but_grid_censored";
if any(finite), scatter(ax,double(q.m_application(finite)),double(q.mismatch(finite)),55,log2(double(q.C_labels(finite))),'filled'); end
if any(cens), scatter(ax,double(q.m_application(cens)),double(q.mismatch(cens)),70,purple,'o','LineWidth',1.4,'DisplayName','Safe, grid-censored'); end
if any(structural), scatter(ax,double(q.m_application(structural)),double(q.mismatch(structural)),75,red,'x','LineWidth',1.6,'DisplayName','Structurally non-certifiable'); end
mFine=logspace(log10(16),log10(512),300); dc=arrayfun(@(mm)sqrt(tauw*auc_var_lower_bound(.75,max(2,round(mm)),max(2,round(mm)))),mFine);
plot(ax,mFine,dc,'k--','LineWidth',1.3,'HandleVisibility','off'); plot(ax,mFine,-dc,'k--','LineWidth',1.3,'HandleVisibility','off');
set(ax,'XScale','log'); xlabel(ax,'Future audit size per class, m'); ylabel(ax,'Historical mismatch, h-\theta'); title(ax,'Exact certification cost at AUC 0.75','FontSize',11.5); grid(ax,'on');
cb=colorbar(ax); cb.Label.String='log_2 outcomes'; cb.FontName=FONT; cb.FontSize=10;
local_style(ax,FONT); local_letter(fig,ax,'B',purple);

% C scaling law
ax=nexttile(t,3); hold(ax,'on'); x=double(S.m_application); y=double(S.zero_mismatch_median); lo=double(S.zero_mismatch_q25); hi=double(S.zero_mismatch_q75);
v=isfinite(y)&y>0; errorbar(ax,x(v),y(v),y(v)-lo(v),hi(v)-y(v),'o-','Color',purple,'MarkerFaceColor','w','LineWidth',1.3,'MarkerSize',6);
idx=find(v & x>=32,1); anchor=y(idx)/x(idx); plot(ax,x(v),anchor*x(v),'k--','LineWidth',1.3);
set(ax,'XScale','log','YScale','log'); xlabel(ax,'Future audit size per class, m'); ylabel(ax,'Verified certification outcomes'); title(ax,'Certification-cost scaling','FontSize',11.5); grid(ax,'on');
vv=v & x>=32; p=polyfit(log(x(vv)),log(y(vv)),1); text(ax,.04,.90,sprintf('observed slope = %.2f',p(1)),'Units','normalized','FontName',FONT,'FontSize',10,'FontWeight','bold','Color',purple);
text(ax,.04,.80,'theory: C^* = \Theta(m) in locally matched balanced AUC','Units','normalized','FontName',FONT,'FontSize',9,'Color',dark);
local_style(ax,FONT); local_letter(fig,ax,'C',purple);

% D completed CMDO projection
ax=nexttile(t,4); hold(ax,'on'); stages=["U6","U7","U8","U9A","U9B"]; scol=[blue;green;[.08 .58 .52];orange;red];
for j=1:numel(stages)
    m=string(A.stage)==stages(j); yy=double(A.rho_realized_w005(m)); n=sum(m); jit=linspace(-.17,.17,n)';
    scatter(ax,j+jit,yy,30,scol(j,:),'filled','MarkerFaceAlpha',.55,'HandleVisibility','off');
    scatter(ax,j,median(yy),95,scol(j,:),'filled','MarkerEdgeColor','k','LineWidth',.7,'HandleVisibility','off');
end
yline(ax,1,'k--','LineWidth',1.4,'DisplayName','\rho=1 boundary'); set(ax,'YScale','log','XTick',1:5,'XTickLabel',cellstr(stages));
xlabel(ax,'Completed CMDO stage'); ylabel(ax,'Post-completion \rho^{real}_{0.05}'); title(ax,'Completed-state projection','FontSize',11.5); grid(ax,'on');
local_style(ax,FONT); local_letter(fig,ax,'D',purple);

png=fullfile(outputDir,'Figure4_CERTIFY.png'); pdf=fullfile(outputDir,'Figure4_CERTIFY.pdf'); exportgraphics(fig,png,'Resolution',300); exportgraphics(fig,pdf,'ContentType','vector');
fprintf('Figure 4 written:\n%s\n%s\n',png,pdf);
end

function V=auc_var_lower_bound(theta,m,n)
if theta<=0 || theta>=1 || m<2 || n<2, V=0; return; end
s=min(m,n); ell=max(m,n); r=min(theta,1-theta); q=max(theta,1-theta);
if (s-1)/(ell-1) <= 2*r
    B=s-(s-1)^2/(12*(ell-1)*theta*(1-theta));
else
    B=1-(m+n-2)*r/q+4/(3*q)*sqrt(2*r*(m-1)*(n-1));
end
V=max(0,theta*(1-theta)/(m*n)*B);
end
function local_style(ax,FONT), set(ax,'FontName',FONT,'FontSize',9.1,'LineWidth',.8,'TickDir','out','Box','off', ...
    'GridAlpha',0.13,'MinorGridAlpha',0.04,'XMinorGrid','off','YMinorGrid','off'); end
function local_letter(fig,ax,s,c)
drawnow;
p=ax.Position;
x=max(0.006,p(1)-0.033);
y=min(0.945,p(2)+p(4)+0.010);
annotation(fig,'textbox',[x y 0.030 0.035], ...
    'String',s,'LineStyle','none','FitBoxToText','on', ...
    'FontName','Arial','FontSize',15,'FontWeight','bold', ...
    'Color',c,'HorizontalAlignment','left','VerticalAlignment','bottom');
end
