function handles = cmdo_safe_draw_box(ax, position, titleText, bodyText, tagText, varargin)
%CMDO_SAFE_DRAW_BOX Draw a labelled conceptual box in axes coordinates.

parser = inputParser;
addParameter(parser, 'FaceColor', [0.97 0.97 0.97]);
addParameter(parser, 'EdgeColor', [0.45 0.45 0.45]);
parse(parser, varargin{:});
opt = parser.Results;

handles = struct();
handles.rectangle = rectangle(ax, 'Position', position, 'Curvature', 0.05, ...
    'FaceColor', opt.FaceColor, 'EdgeColor', opt.EdgeColor, 'LineWidth', 1.2);
x = position(1); y = position(2); w = position(3); h = position(4);
handles.title = text(ax, x + w/2, y + 0.82*h, char(string(titleText)), ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
    'FontWeight', 'bold', 'FontSize', 9.5);
handles.body = text(ax, x + w/2, y + 0.48*h, char(string(bodyText)), ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
    'FontSize', 8.2, 'Interpreter', 'none');
if strlength(string(tagText)) > 0
    handles.tag = text(ax, x + w/2, y + 0.10*h, char(string(tagText)), ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
        'FontWeight', 'bold', 'FontSize', 7.5, 'Color', opt.EdgeColor, ...
        'Interpreter', 'none');
else
    handles.tag = gobjects(0);
end
end
