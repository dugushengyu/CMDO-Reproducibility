function Figure2
%FIGURE2 Generate the CMDO Figure2 figure and export all formats.
close all;

scriptDir = fileparts(mfilename('fullpath'));
if ~isempty(scriptDir)
    addpath(genpath(scriptDir));
end

cfg=cmdo_config('Figure2'); rng(20260728,'twister');
fig=figure('Position',[40 70 1550 760],'Color','w'); tl=tiledlayout(fig,1,3,'TileSpacing','compact','Padding','compact');
sgtitle(tl,'Observability and the information cost of outcome measurement','FontWeight','bold','FontSize',18);

% a — identical observable channel, opposite worlds
ax=nexttile(tl); hold(ax,'on'); axis(ax,[0 1 0 1]); axis(ax,'off'); cmdo_safe_panel_letter(ax,'a');
title(ax,'Identical outcome-free evidence, opposite performance','FontWeight','bold','FontSize',12);
cmdo_safe_draw_box(ax,[.04 .72 .92 .21],'Outcome-free monitoring channel',sprintf('Inputs X  |  Scores S  |  Confidence C  |  Drift statistics'),'identical in both worlds','FaceColor',[.97 .97 .97]);
cmdo_safe_draw_box(ax,[.05 .39 .42 .25],'World P',sprintf('Outcomes increase with score\nHigh current performance'),'AUC near 1','FaceColor',[.94 .97 1],'EdgeColor',[.35 .55 .90]);
cmdo_safe_draw_box(ax,[.53 .39 .42 .25],'World Q',sprintf('Outcomes decrease with score\nComplete ranking reversal'),'AUC near 0','FaceColor',[1 .95 .95],'EdgeColor',[.90 .35 .35]);
scores=linspace(.08,.92,10); scatter(ax,.10+.30*scores,.44+.12*[zeros(1,5) ones(1,5)],30,'filled');
scatter(ax,.58+.30*scores,.44+.12*[ones(1,5) zeros(1,5)],30,'filled');
cmdo_safe_draw_box(ax,[.12 .08 .76 .20],'Structural conclusion',sprintf('At m = 0, the compatible performance set spans the full range.\nNo outcome-free statistic can resolve the two worlds.'),'NON-IDENTIFIABLE','FaceColor',[.98 .95 1],'EdgeColor',[.65 .45 .85]);

% b — finite outcome intervals
ax=nexttile(tl); hold(ax,'on'); cmdo_safe_panel_letter(ax,'b'); title(ax,'Audited outcomes shrink performance uncertainty','FontWeight','bold','FontSize',12);
budgets=[16 32 64 128 256 512 1024]; theta=.70; nRep=500; n=numel(budgets);
hStruct=line(ax,[0 1],[n+1 n+1],'Color',[.55 .55 .55],'LineWidth',4); hTrue=plot(ax,theta,n+1,'d','MarkerFaceColor','k','MarkerEdgeColor','k'); hCI=gobjects(1); hMed=gobjects(1);
for i=1:n
    estimates=mean(rand(nRep,budgets(i))<theta,2); med=cmdo_quantile(estimates,.5); lo=cmdo_quantile(estimates,.025); hi=cmdo_quantile(estimates,.975);
    y=n-i+1; line(ax,[lo hi],[y y],'Color',[.20 .50 .80],'LineWidth',6); h=line(ax,[lo hi],[y y],'Color',[.05 .25 .55],'LineWidth',1.2); hm=plot(ax,med,y,'ko','MarkerFaceColor','k','MarkerSize',4); if i==1, hCI=h; hMed=hm; end
end
xline(ax,theta,'--','Color',[.85 .15 .15],'LineWidth',1.3); xlim(ax,[0 1]); ylim(ax,[.4 n+1.8]);
yticks(ax,1:n+1); yticklabels(ax,[compose('m = %d',fliplr(budgets)),"m = 0"]); xlabel(ax,'Performance (Bernoulli accuracy)'); set(ax,'XGrid','on','YGrid','on'); cmdo_safe_apply_axes_style(ax);
legend(ax,[hStruct hTrue hCI hMed],{'Structural range at m=0','True performance','95% empirical interval','Median'},'Location','southoutside','NumColumns',2,'Box','off');

% c — root-budget law simulation
ax=nexttile(tl); hold(ax,'on'); cmdo_safe_panel_letter(ax,'c'); title(ax,'Estimation error follows the root-budget law','FontWeight','bold','FontSize',12);
R=400; mae=zeros(4,n); truth=[.5*(1+erf(.5)),.70,5/7,.62];
for i=1:n
    m=budgets(i); acc=mean(rand(R,m)<truth(2),2); sens=mean(rand(R,m)<truth(4),2);
    g1=randg(5,R,m); g2=randg(2,R,m); brier=mean(g1./(g1+g2),2);
    aucv=zeros(R,1); h=max(2,floor(m/2));
    for r=1:R, aucv(r)=cmdo_auc(randn(h,1)+1,randn(h,1)); end
    mae(:,i)=[mean(abs(aucv-truth(1)));mean(abs(acc-truth(2)));mean(abs(brier-truth(3)));mean(abs(sens-truth(4)))];
end
names={'AUC','Accuracy','Brier utility','Sensitivity'}; marks={'o','s','^','d'};
for j=1:4, loglog(ax,budgets,mae(j,:),'-','Marker',marks{j},'LineWidth',1.5,'DisplayName',names{j}); end
ref=mae(1,1)*(budgets/budgets(1)).^(-.5); loglog(ax,budgets,ref,'k--','LineWidth',1.2,'DisplayName','m^{-1/2} reference');
xlabel(ax,'Number of audited outcomes, m'); ylabel(ax,'Mean absolute error'); set(ax,'XGrid','on','YGrid','on'); legend(ax,'Location','southwest','Box','off'); cmdo_safe_apply_axes_style(ax);
slopes=zeros(4,1); for j=1:4, p=polyfit(log10(budgets),log10(mae(j,:)),1); slopes(j)=p(1); end
text(ax,.98,.96,sprintf('Fitted slopes\nAUC %.3f\nAccuracy %.3f\nBrier %.3f\nSensitivity %.3f',slopes), ...
    'Units','normalized','HorizontalAlignment','right','VerticalAlignment','top','BackgroundColor','w','Margin',5);
cmdo_safe_save_figure(fig,cfg,'Figure2_Observability_And_Information_Cost');
end
