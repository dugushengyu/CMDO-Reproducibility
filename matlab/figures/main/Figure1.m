function Figure1
%FIGURE1 Generate the CMDO Figure1 figure and export all formats.
close all;

scriptDir = fileparts(mfilename('fullpath'));
if ~isempty(scriptDir)
    addpath(genpath(scriptDir));
end

cfg = cmdo_config('Figure1'); D = cmdo_load_all(cfg);
fig = figure('Position',[40 40 1600 1100],'Color','w');
tl = tiledlayout(fig,3,2,'TileSpacing','loose','Padding','loose');
tl.OuterPosition = [0.035 0.065 0.93 0.88];
sgtitle(tl,'The observability blind spot and the role of sparse outcomes','FontWeight','bold','FontSize',18);

% a — conceptual blind spot
ax = nexttile(tl,[1 2]); hold(ax,'on'); axis(ax,[0 1 0 1]); axis(ax,'off');
f1_panel_letter(ax,'a',true); title(ax,'Outcome-free observables do not identify current performance','FontWeight','bold','FontSize',13);
cmdo_safe_draw_box(ax,[0.02 0.18 0.17 0.66],'Inputs at deployment',sprintf('Medical images\nNatural images\nPopulation tables'),'','FaceColor',[0.95 0.97 1],'EdgeColor',[0.55 0.68 0.95]);
cmdo_safe_draw_box(ax,[0.23 0.18 0.16 0.66],'Deployed model',sprintf('Predictions\nScores\nConfidence'),'','FaceColor',[0.95 0.97 1],'EdgeColor',[0.55 0.68 0.95]);
cmdo_safe_draw_box(ax,[0.43 0.18 0.19 0.66],'Outcome-free evidence',sprintf('Input distribution\nPrediction scores\nModel confidence\nDrift summaries'),'','FaceColor',[0.95 0.97 1],'EdgeColor',[0.55 0.68 0.95]);
cmdo_safe_draw_box(ax,[0.67 0.18 0.31 0.66],'Observationally identical worlds',sprintf('World P: ranking is correct\nWorld Q: ranking is reversed\n\nSame observed evidence; opposite outcomes'),'NON-IDENTIFIABLE','FaceColor',[0.98 0.95 1],'EdgeColor',[0.65 0.45 0.85]);
cmdo_safe_arrow(ax,0.19,0.51,0.23,0.51,[0.10 0.28 0.80]); cmdo_safe_arrow(ax,0.39,0.51,0.43,0.51,[0.10 0.28 0.80]); cmdo_safe_arrow(ax,0.62,0.51,0.67,0.51,[0.10 0.28 0.80]);
text(ax,0.50,0.08,'Identical inputs, scores, confidence and drift summaries can coexist with opposite current performance.', ...
    'HorizontalAlignment','center','FontWeight','bold','Color',[0.28 0.10 0.55]);

% b — sparse outcome sensing
ax = nexttile(tl,[1 2]); hold(ax,'on'); axis(ax,[0 1 0 1]); axis(ax,'off');
f1_panel_letter(ax,'b',true); title(ax,'Sparse outcomes cross the observability boundary and enable guarded borrowing','FontWeight','bold','FontSize',13);
boxes = {[0.01 0.18 0.15 0.62],[0.20 0.18 0.18 0.62],[0.42 0.18 0.14 0.62],[0.60 0.18 0.22 0.62],[0.86 0.18 0.13 0.62]};
cmdo_safe_draw_box(ax,boxes{1},'Audit outcomes',sprintf('Observe a small\nlabelled subset'),'m outcomes','FaceColor',[1 .96 .92],'EdgeColor',[1 .65 .35]);
cmdo_safe_draw_box(ax,boxes{2},'Uncertainty shrinks','','ROOT-BUDGET','FaceColor',[1 .96 .92],'EdgeColor',[1 .65 .35]);
cmdo_safe_draw_box(ax,boxes{3},'Bias sensing',sprintf('Estimate transport\nbias B^2'),'CHECK','FaceColor',[.97 .94 1],'EdgeColor',[.65 .45 .85]);
cmdo_safe_draw_box(ax,boxes{4},'Guarded borrowing',sprintf('Continuous weight w\nExact direct fallback\nwhen support is weak'),'SAFE OBSERVER','FaceColor',[.94 1 .96],'EdgeColor',[.35 .75 .50]);
cmdo_safe_draw_box(ax,boxes{5},'Output',sprintf('Performance estimate\n+ uncertainty'),'OBSERVABLE','FaceColor',[.97 .94 1],'EdgeColor',[.65 .45 .85]);
for k=1:4, a=boxes{k}; b=boxes{k+1}; cmdo_safe_arrow(ax,a(1)+a(3),0.49,b(1),0.49,[0.25 0.35 0.45]); end
m=logspace(0,3,80); epsv=.8*m.^(-.5); drawnow; posB=ax.Position;
inset=axes(fig,'Position',[posB(1)+0.225*posB(3), posB(2)+0.405*posB(4), 0.130*posB(3), 0.175*posB(4)]);
loglog(inset,m,epsv,'LineWidth',1.4); axis(inset,'tight'); box(inset,'off');
set(inset,'FontSize',6.5); xticks(inset,[1 10 100 1000]); ylabel(inset,'uncertainty');

% c — U6 and U7 independent validation
u6 = D.u6_target; u6rr = 100*(u6.direct_mae-u6.mae)./u6.direct_mae; u6rr=sort(u6rr);
ax = nexttile(tl); bar(ax,u6rr,'FaceColor',[0.15 0.38 0.82]); yline(ax,0,'--');
title(ax,'Cross-domain reserve U6: 16 unseen targets','FontWeight','bold'); xlabel(ax,'Targets (ordered)'); ylabel(ax,'Relative MAE reduction (%)'); f1_panel_letter(ax,'c',false); cmdo_safe_apply_axes_style(ax);
ylim(ax,[0 max(u6rr)*1.18]);
text(ax,0.98,0.96,sprintf('16/16 improved\nPooled reduction %.2f%%',100*(mean(u6.direct_mae)-mean(u6.mae))/mean(u6.direct_mae)), ...
    'Units','normalized','HorizontalAlignment','right','VerticalAlignment','top', ...
    'FontWeight','bold','BackgroundColor','w','Margin',2);
u7 = D.u7_target(string(D.u7_target.metric)=="AUC",:); u7rr=100*(u7.direct_mae-u7.mae)./u7.direct_mae; u7rr=sort(u7rr);
ax = nexttile(tl); f1_panel_letter(ax,'d',false); bar(ax,u7rr,'FaceColor',[0.94 0.42 0.12]); yline(ax,0,'--');
title(ax,'Clinical transition U7: 16 prespecified strata','FontWeight','bold'); xlabel(ax,'Strata (ordered)'); ylabel(ax,'Relative AUC-MAE reduction (%)'); cmdo_safe_apply_axes_style(ax);
ylim(ax,[0 max(u7rr)*1.18]);
text(ax,0.98,0.96,sprintf('16/16 improved\nPooled reduction %.2f%%',100*(mean(u7.direct_mae)-mean(u7.mae))/mean(u7.direct_mae)), ...
    'Units','normalized','HorizontalAlignment','right','VerticalAlignment','top', ...
    'FontWeight','bold','BackgroundColor','w','Margin',2);
annotation(fig,'textbox',[.04 .005 .92 .04],'String','Performance observability is the design principle: outcome-free monitoring alone cannot generally determine current performance.', ...
    'EdgeColor','none','HorizontalAlignment','center','FontWeight','bold','Color',[.28 .10 .55]);
cmdo_safe_save_figure(fig,cfg,'Figure1_Blind_Spot_Outcome_Sensing_And_Validation');
end

function h = f1_panel_letter(ax,letter,fullWidth)
if fullWidth
    x = 0.003;
    y = 0.99;
else
    x = -0.065;
    y = 1.04;
end
h = text(ax,x,y,char(string(letter)), ...
    'Units','normalized','FontName','Arial','FontSize',14, ...
    'FontWeight','bold','HorizontalAlignment','left', ...
    'VerticalAlignment','top','Clipping','off');
end
