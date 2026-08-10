function cmdo_safe_apply_axes_style(ax)
%CMDO_SAFE_APPLY_AXES_STYLE Apply publication defaults without changing data.

if nargin < 1 || isempty(ax)
    ax = gca;
end
set(ax, 'Box', 'off', 'FontName', 'Arial', 'FontSize', 9, ...
    'LineWidth', 0.8, 'TickDir', 'out', 'Layer', 'top');
if isprop(ax, 'GridAlpha')
    ax.GridAlpha = 0.12;
end
end
