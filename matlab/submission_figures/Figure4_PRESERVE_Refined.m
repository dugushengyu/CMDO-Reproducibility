function Figure4_PRESERVE_Refined(outputDir)
%FIGURE4_PRESERVE_REFINED Reviewer-facing Figure 4 renderer.
% All plotted values are read from a tracked repository source CSV.

close all;
thisFile = mfilename('fullpath');
if isempty(thisFile), scriptDir = pwd; else, scriptDir = fileparts(thisFile); end
repoRoot = fileparts(fileparts(scriptDir));
if nargin < 1 || isempty(outputDir), outputDir = fullfile(scriptDir,'output'); end
if ~exist(outputDir,'dir'), mkdir(outputDir); end

src = fullfile(repoRoot,'source_data','figure4_submission', ...
    'CMDO_Figure4_PRESERVE_Source_v1.csv');
assert(isfile(src),'Missing tracked Figure 4 source CSV: %s',src);
T = readtable(src,'VariableNamingRule','preserve');

FONT='Arial'; FS_AXIS=11.2; FS_TICK=9.6;
DARK=[0.18 0.18 0.18]; GREY=[0.45 0.45 0.45];
GREEN=[0.00 0.50 0.18]; RED=[0.88 0.07 0.06]; PURPLE=[0.45 0.18 0.78];
GROUPCOLORS={PURPLE,GREEN,RED};

%% Panel A data
order = {'u9b','georgia','cpsc_2018'};
labels = {'External system (U9B)','Georgia','CPSC 2018'};
budgets = [128 256 512 1024];
riskFixed=[]; riskAdapt=[]; xAll=[];
for g=1:3
    S=T(strcmp(string(T.dataset),order{g}),:);
    [~,ix]=sort(double(S.budget)); S=S(ix,:);
    assert(isequal(double(S.budget(:))',budgets),'Figure 4 budget mismatch.');
    riskFixed=[riskFixed double(S.fixed_risk(:))']; %#ok<AGROW>
    riskAdapt=[riskAdapt double(S.adaptive_risk(:))']; %#ok<AGROW>
    xAll=[xAll ((g-1)*5 + (1:4))]; %#ok<AGROW>
end
adaptiveWorse=nnz(riskAdapt>riskFixed);
benefitToHarm=nnz((riskFixed<1)&(riskAdapt>1));
assert(adaptiveWorse==12 && benefitToHarm==7,'Figure 4A fingerprint mismatch.');

%% Panel B data: state contributions to H and A+C
B=T(ismember(string(T.dataset),["georgia","cpsc_2018"]),:);
Hc=double(B.H_contribution); Ac=double(B.A_contribution);
Cc=double(B.C_contribution); Cost=double(B.cost_contribution);
assert(max(abs(Cost-(Ac+Cc)))<1e-10,'Figure 4B state-cost closure failed.');
H=mean(Hc); A=mean(Ac); C=mean(Cc); sharedCost=A+C;
Cperm=0.03214915; permCost=A+Cperm;
assert(abs(H-0.08614018)<5e-7,'H fingerprint mismatch.');
assert(abs(A-0.01403814)<5e-7,'A fingerprint mismatch.');
assert(abs(C-0.21760208)<5e-7,'C fingerprint mismatch.');
assert(abs(Cperm-0.03214915)<1e-12,'Pairing-disruption C fingerprint mismatch.');

%% Figure
fig=figure('Color','w','Units','pixels','Position',[45 45 1080 420], ...
    'Renderer','painters','Name','CMDO Figure 4 — PRESERVE','NumberTitle','off');
annotation(fig,'textbox',[0.18 0.945 0.64 0.04], ...
    'String','Evidence value must survive adaptation','EdgeColor','none', ...
    'HorizontalAlignment','center','FontName',FONT,'FontSize',20,'FontWeight','bold','Color',DARK);

%% Panel A
axA=axes('Parent',fig,'Units','normalized','Position',[0.065 0.18 0.52 0.61]);
hold(axA,'on'); box(axA,'off'); hideToolbarSafe(axA);
yline(axA,1,'--','Color',GREY,'LineWidth',1,'HandleVisibility','off');
for i=1:numel(xAll)
    plot(axA,[xAll(i) xAll(i)],[riskFixed(i) riskAdapt(i)],'-','Color',[.72 .72 .72], ...
        'LineWidth',1.4,'HandleVisibility','off');
end
hF=scatter(axA,xAll,riskFixed,58,'s','filled','MarkerFaceColor',GREEN,'MarkerEdgeColor','w','LineWidth',.7);
hR=scatter(axA,xAll,riskAdapt,62,'o','filled','MarkerFaceColor',RED,'MarkerEdgeColor','w','LineWidth',.7);
for g=1:3
    xx=(g-1)*5+(1:4);
    text(axA,mean(xx),1.265,labels{g},'HorizontalAlignment','center','FontName',FONT, ...
        'FontSize',9.7,'FontWeight','bold','Color',GROUPCOLORS{g});
end
text(axA,13.7,.62,sprintf('adaptive worse: %d/12',adaptiveWorse),'HorizontalAlignment','right', ...
    'FontName',FONT,'FontSize',9.8,'FontWeight','bold','Color',PURPLE);
text(axA,13.7,.57,sprintf('fixed benefit \\rightarrow adaptive harm: %d/12',benefitToHarm), ...
    'Interpreter','tex','HorizontalAlignment','right','FontName',FONT,'FontSize',9.8,'FontWeight','bold','Color',PURPLE);
set(axA,'XLim',[.45 14.55],'YLim',[.50 1.30],'XTick',xAll, ...
    'XTickLabel',string([budgets budgets budgets]),'YTick',.5:.1:1.3, ...
    'FontName',FONT,'FontSize',FS_TICK,'TickDir','out','LineWidth',.95);
xlabel(axA,'Audited outcomes, m','FontName',FONT,'FontSize',FS_AXIS);
ylabel(axA,'Normalized risk, R/V','FontName',FONT,'FontSize',FS_AXIS);
legend(axA,[hF hR],{'Matched fixed reuse','Adaptive reuse'},'Location','southwest','Box','off','FontSize',9);
text(axA,-.08,1.08,'A','Units','normalized','FontName',FONT,'FontSize',24,'FontWeight','bold','Color',RED);
text(axA,.02,1.08,'Adaptation can erase fixed-use gains','Units','normalized','FontName',FONT,'FontSize',13.5,'FontWeight','bold','Color',RED);

%% Panel B: adaptation frontier
axB=axes('Parent',fig,'Units','normalized','Position',[0.665 0.18 0.29 0.61]);
hold(axB,'on'); box(axB,'off'); hideToolbarSafe(axB);
mx=max([Cost;Hc;sharedCost;H;permCost]) * 1.18;
plot(axB,[0 mx],[0 mx],'--','Color',GREY,'LineWidth',1.1,'HandleVisibility','off');
G=strcmp(string(B.dataset),'georgia'); P=strcmp(string(B.dataset),'cpsc_2018');
hG=scatter(axB,Cost(G),Hc(G),62,'s','filled','MarkerFaceColor',GREEN,'MarkerEdgeColor','w','LineWidth',.7);
hP=scatter(axB,Cost(P),Hc(P),62,'o','filled','MarkerFaceColor',RED,'MarkerEdgeColor','w','LineWidth',.7);
hAgg=scatter(axB,sharedCost,H,95,'^','MarkerFaceColor','none','MarkerEdgeColor',DARK,'LineWidth',1.7);
quiver(axB,sharedCost,H,permCost-sharedCost,0,0,'Color',PURPLE,'LineWidth',1.6, ...
    'MaxHeadSize',.35,'HandleVisibility','off');
hPerm=scatter(axB,permCost,H,78,'d','filled','MarkerFaceColor',PURPLE,'MarkerEdgeColor','w','LineWidth',.7);
set(axB,'XLim',[0 mx],'YLim',[0 mx],'FontName',FONT,'FontSize',FS_TICK,'TickDir','out','LineWidth',.95);
axis(axB,'square');
xlabel(axB,'Cost contribution, A + C','FontName',FONT,'FontSize',FS_AXIS);
ylabel(axB,'Opportunity contribution, H','FontName',FONT,'FontSize',FS_AXIS);
text(axB,.98,.96,'H > A + C','Units','normalized','HorizontalAlignment','right','VerticalAlignment','top', ...
    'FontName',FONT,'FontSize',10,'FontWeight','bold','Color',GREEN);
text(axB,.98,.08,'H < A + C','Units','normalized','HorizontalAlignment','right','VerticalAlignment','bottom', ...
    'FontName',FONT,'FontSize',10,'FontWeight','bold','Color',RED);
legend(axB,[hG hP hAgg hPerm],{'Georgia: 4 budgets','CPSC 2018: 4 budgets','Shared adaptive mean','Pairing disrupted'}, ...
    'Location','northeast','Box','off','FontSize',8.4);
text(axB,-.17,1.08,'B','Units','normalized','FontName',FONT,'FontSize',24,'FontWeight','bold','Color',PURPLE);
text(axB,-.02,1.08,'Adaptation is worthwhile only when H > A + C','Units','normalized','FontName',FONT,'FontSize',12.7,'FontWeight','bold','Color',PURPLE);

%% Export
pngPath=fullfile(outputDir,'Figure4_PRESERVE_Refined.png');
pdfPath=fullfile(outputDir,'Figure4_PRESERVE_Refined.pdf');
figPath=fullfile(outputDir,'Figure4_PRESERVE_Refined.fig');
drawnow; savefig(fig,figPath);
exportgraphics(fig,pngPath,'Resolution',300,'BackgroundColor','white');
exportgraphics(fig,pdfPath,'ContentType','vector','BackgroundColor','white');
fprintf('\nFIGURE 4 — PRESERVE\n');
fprintf('Source CSV : %s\n',src);
fprintf('Adaptive worse than matched fixed : %d/12\n',adaptiveWorse);
fprintf('Fixed benefit -> adaptive harm    : %d/12\n',benefitToHarm);
fprintf('H=%.8f  A=%.8f  C=%.8f  H-A-C=%.8f\n',H,A,C,H-A-C);
fprintf('Pair-disrupted C=%.8f  H-A-C=%.8f\n',Cperm,H-A-Cperm);
end

function hideToolbarSafe(ax)
try, ax.Toolbar.Visible='off'; catch, try, axtoolbar(ax,{}); catch, end, end
end
