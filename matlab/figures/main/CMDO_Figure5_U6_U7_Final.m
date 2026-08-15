function CMDO_Figure5_U6_U7_Final
%CMDO_FIGURE5_U6_U7_FINAL Data-driven integrated U6/U7 confirmation figure.
% Current manuscript Figure 5 route; reads only canonical U6/U7 records.
close all;
scriptDir=fileparts(mfilename('fullpath')); addpath(genpath(scriptDir));
cfg=cmdo_config('Figure5'); D=cmdo_load_all(cfg);
if ~exist(cfg.outputDir,'dir'), mkdir(cfg.outputDir); end
U6=D.u6_target; U7=D.u7_target(string(D.u7_target.metric)=="AUC",:);
U6.gain_pct=100.*double(U6.gain_vs_full_direct)./double(U6.direct_mae);
U7.gain_pct=100.*double(U7.gain)./double(U7.direct_mae);
U6=sortrows(U6,'gain_pct','descend'); U7=sortrows(U7,'gain_pct','descend');
S6=D.u6_state; S7=D.u7_state(string(D.u7_state.metric)=="AUC",:); M7=D.u7_metric;
fig=figure('Position',[40 30 900 940],'Color','w','Renderer','painters','Name','CMDO Figure 5','NumberTitle','off');
tl=tiledlayout(fig,3,2,'TileSpacing','compact','Padding','compact');
title(tl,'Frozen observer confirmation across cross-domain and clinical transitions','FontWeight','bold','FontSize',15);
ax=nexttile; hold(ax,'on'); y=1:height(U6); for i=1:height(U6), plot(ax,[U6.mae(i) U6.direct_mae(i)],[i i],'-','Color',[.75 .75 .75]); plot(ax,U6.direct_mae(i),i,'o','MarkerFaceColor','w','MarkerEdgeColor',[.3 .3 .3]); plot(ax,U6.mae(i),i,'o','MarkerFaceColor',[.2 .5 .8],'MarkerEdgeColor','w'); end; set(ax,'YDir','reverse'); yticks(ax,y); yticklabels(ax,short_names(string(U6.target))); xlabel(ax,'Same-budget AUC MAE'); grid(ax,'on'); title(ax,sprintf('U6: all 16 unseen targets improved (pooled %.2f%%)',100*(mean(S6.direct_mae)-mean(S6.mae))/mean(S6.direct_mae)),'FontWeight','bold');
ax=nexttile; hold(ax,'on'); y=1:height(U7); for i=1:height(U7), plot(ax,[U7.mae(i) U7.direct_mae(i)],[i i],'-','Color',[.75 .75 .75]); plot(ax,U7.direct_mae(i),i,'o','MarkerFaceColor','w','MarkerEdgeColor',[.3 .3 .3]); plot(ax,U7.mae(i),i,'s','MarkerFaceColor',[.2 .65 .35],'MarkerEdgeColor','w'); end; set(ax,'YDir','reverse'); yticks(ax,y); yticklabels(ax,pretty_strata(string(U7.stratum))); xlabel(ax,'Same-budget AUC MAE'); grid(ax,'on'); aucrow=M7(string(M7.metric)=="AUC",:); title(ax,sprintf('U7: all 16 clinical strata improved (pooled %.2f%%)',100*aucrow.relative_gain),'FontWeight','bold');
ax=nexttile; m=S6.budget==max(S6.budget); x=double(S6.mean_sensor_abs_gap(m)); yy=double(S6.transport_abs_error(m)); scatter(ax,x,yy,38,'filled'); hold(ax,'on'); p=polyfit(x,yy,1); xx=linspace(min(x),max(x),100); plot(ax,xx,polyval(p,xx),'-'); rho=corr(x,yy,'Type','Spearman','Rows','complete'); xlabel(ax,'Paired-sensor discrepancy'); ylabel(ax,'Transport absolute error'); grid(ax,'on'); title(ax,sprintf('U6 bias observability (\\rho = %.3f)',rho),'FontWeight','bold');
ax=nexttile; m=S7.budget==max(S7.budget); x=double(S7.mean_sensor_gap(m)); yy=double(S7.transport_abs_error(m)); scatter(ax,x,yy,38,'filled'); hold(ax,'on'); p=polyfit(x,yy,1); xx=linspace(min(x),max(x),100); plot(ax,xx,polyval(p,xx),'-'); rho=corr(x,yy,'Type','Spearman','Rows','complete'); xlabel(ax,'Paired-sensor discrepancy'); ylabel(ax,'Transport absolute error'); grid(ax,'on'); title(ax,sprintf('U7 bias observability (\\rho = %.3f)',rho),'FontWeight','bold');
ax=nexttile; hold(ax,'on'); b6=unique(S6.budget); b7=unique(S7.budget); plot(ax,b6,arrayfun(@(b)max(S6.mae_regret_vs_full_direct(S6.budget==b)),b6),'-o','DisplayName','U6 worst state'); plot(ax,b7,arrayfun(@(b)max(S7.regret(S7.budget==b)),b7),'-s','DisplayName','U7 worst state'); yline(ax,0,'--'); set(ax,'XScale','log'); xlabel(ax,'Outcome budget'); ylabel(ax,'Worst state regret'); grid(ax,'on'); legend(ax,'Box','off'); title(ax,'Safety across complete budget trajectories','FontWeight','bold');
ax=nexttile; metrics=["SENSITIVITY","SPECIFICITY","AUC","BALANCED_ACCURACY","BRIER_UTILITY"]; labels={'U6 AUC','U7 sensitivity','U7 specificity','U7 AUC','U7 balanced accuracy','U7 Brier utility'}; g=[100*(mean(S6.direct_mae)-mean(S6.mae))/mean(S6.direct_mae)]; for k=1:numel(metrics), r=M7(string(M7.metric)==metrics(k),:); g(end+1)=100*r.relative_gain; end; barh(ax,1:6,g); xline(ax,0); yticks(ax,1:6); yticklabels(ax,labels); set(ax,'YDir','reverse'); xlabel(ax,'Relative pooled MAE reduction (%)'); grid(ax,'on'); title(ax,'Cross-reserve and bounded-metric profile','FontWeight','bold'); for k=1:6, text(ax,g(k)+0.08,k,sprintf('%.2f%%',g(k)),'FontWeight','bold'); end
letters='abcdef'; for i=1:6, a=nexttile(tl,i); text(a,-0.13,1.06,letters(i),'Units','normalized','FontWeight','bold','FontSize',12); end
cmdo_safe_save_figure(fig,cfg,'Figure5_U6_U7_Final');
end
function out=short_names(s), out=replace(s,"_"," "); out=replace(out,"ACS PUBLIC COVERAGE 2024 ","ACS-"); out=replace(out,"CIFAR CAT DOG ","CIFAR "); out=replace(out,"DERMA ","Derma "); end
function out=pretty_strata(s), out=replace(lower(s),"er_",""); out=replace(out,"_"," "); end
