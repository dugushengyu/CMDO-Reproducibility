function handle = cmdo_safe_arrow(ax, x1, y1, x2, y2, color)
%CMDO_SAFE_ARROW Draw an arrow in the current axes' data coordinates.

if nargin < 6
    color = [0.25 0.25 0.25];
end
handle = quiver(ax, x1, y1, x2-x1, y2-y1, 0, ...
    'Color', color, 'LineWidth', 1.3, 'MaxHeadSize', 0.8, ...
    'AutoScale', 'off');
end
