function handle = cmdo_safe_panel_letter(ax, letter)
%CMDO_SAFE_PANEL_LETTER Place a consistent panel letter.

if nargin < 1 || isempty(ax)
    ax = gca;
end
handle = text(ax, -0.10, 1.06, char(string(letter)), ...
    'Units', 'normalized', 'FontName', 'Arial', 'FontSize', 14, ...
    'FontWeight', 'bold', 'HorizontalAlignment', 'left', ...
    'VerticalAlignment', 'top', 'Clipping', 'off');
end
