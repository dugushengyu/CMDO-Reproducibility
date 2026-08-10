function info = cmdo_png_to_pdf(pngPath, pdfPath, resolutionDpi)
%CMDO_PNG_TO_PDF Embed one accepted PNG losslessly in a one-page PDF.
%
% The writer deliberately bypasses MATLAB figure/axes export.  It reuses the
% PNG's existing lossless IDAT stream as a PDF FlateDecode image with PNG
% prediction, preserving every source pixel and the full canvas.  Supported
% inputs are the non-interlaced, 8-bit true-colour PNGs written by the CMDO
% figure exporters.

if nargin < 3 || isempty(resolutionDpi)
    resolutionDpi = 600;
end
if ~(isnumeric(resolutionDpi) && isscalar(resolutionDpi) && ...
        isfinite(resolutionDpi) && resolutionDpi > 0)
    error('CMDO:InvalidPdfResolution', ...
        'resolutionDpi must be a positive finite scalar.');
end

pngPath = char(string(pngPath));
pdfPath = char(string(pdfPath));
if ~isfile(pngPath)
    error('CMDO:MissingCompatibilityPng', 'Missing PNG: %s', pngPath);
end

[width, height, idatStream] = read_png_image_stream(pngPath);
pageWidth = double(width) * 72 / double(resolutionDpi);
pageHeight = double(height) * 72 / double(resolutionDpi);

pdfFolder = fileparts(pdfPath);
if isempty(pdfFolder)
    pdfFolder = pwd;
elseif ~isfolder(pdfFolder)
    mkdir(pdfFolder);
end
temporaryPdf = [tempname(pdfFolder) '.pdf'];
cleanup = onCleanup(@() delete_if_present(temporaryPdf));

fid = fopen(temporaryPdf, 'w', 'ieee-be');
if fid < 0
    error('CMDO:CompatibilityPdfOpenFailed', ...
        'Could not open temporary PDF for writing: %s', temporaryPdf);
end
fileCleanup = onCleanup(@() fclose_if_open(fid));

content = uint8(sprintf([ ...
    'q\n%.9f 0 0 %.9f 0 0 cm\n/Im0 Do\nQ\n'], ...
    pageWidth, pageHeight));

fprintf(fid, '%%PDF-1.4\n');
fwrite(fid, uint8([37 226 227 207 211 10]), 'uint8');

offsets = zeros(5,1);
offsets(1) = ftell(fid);
fprintf(fid, '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');

offsets(2) = ftell(fid);
fprintf(fid, ['2 0 obj\n' ...
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n']);

offsets(3) = ftell(fid);
fprintf(fid, ['3 0 obj\n' ...
    '<< /Type /Page /Parent 2 0 R ' ...
    '/MediaBox [0 0 %.9f %.9f] ' ...
    '/Resources << /XObject << /Im0 5 0 R >> ' ...
    '/ProcSet [/PDF /ImageC] >> ' ...
    '/Contents 4 0 R >>\nendobj\n'], pageWidth, pageHeight);

offsets(4) = ftell(fid);
fprintf(fid, '4 0 obj\n<< /Length %d >>\nstream\n', numel(content));
fwrite(fid, content, 'uint8');
fprintf(fid, 'endstream\nendobj\n');

offsets(5) = ftell(fid);
fprintf(fid, ['5 0 obj\n' ...
    '<< /Type /XObject /Subtype /Image ' ...
    '/Width %d /Height %d ' ...
    '/ColorSpace /DeviceRGB /BitsPerComponent 8 ' ...
    '/Interpolate false /Filter /FlateDecode ' ...
    '/DecodeParms << /Predictor 15 /Colors 3 ' ...
    '/BitsPerComponent 8 /Columns %d >> ' ...
    '/Length %d >>\nstream\n'], ...
    width, height, width, numel(idatStream));
fwrite(fid, idatStream, 'uint8');
fprintf(fid, '\nendstream\nendobj\n');

xrefOffset = ftell(fid);
fprintf(fid, 'xref\n0 6\n');
fprintf(fid, '0000000000 65535 f \n');
for objectIndex = 1:numel(offsets)
    fprintf(fid, '%010.0f 00000 n \n', offsets(objectIndex));
end
fprintf(fid, ['trailer\n<< /Size 6 /Root 1 0 R >>\n' ...
    'startxref\n%.0f\n%%%%EOF\n'], xrefOffset);

% Clearing the guard closes the file before the Windows move/replace step.
clear fileCleanup;

[moved, moveMessage] = movefile(temporaryPdf, pdfPath, 'f');
if ~moved
    error('CMDO:CompatibilityPdfMoveFailed', ...
        'Could not replace %s: %s', pdfPath, moveMessage);
end
clear cleanup;

written = dir(pdfPath);
if isempty(written) || written.bytes == 0
    error('CMDO:CompatibilityPdfEmpty', ...
        'Compatibility PDF was not written correctly: %s', pdfPath);
end

info = struct( ...
    'sourcePng', pngPath, ...
    'outputPdf', pdfPath, ...
    'pixelWidth', double(width), ...
    'pixelHeight', double(height), ...
    'resolutionDpi', double(resolutionDpi), ...
    'pageWidthPoints', pageWidth, ...
    'pageHeightPoints', pageHeight, ...
    'pdfBytes', double(written.bytes));
end

function [width, height, idatStream] = read_png_image_stream(path)
fid = fopen(path, 'r', 'ieee-be');
if fid < 0
    error('CMDO:CompatibilityPngOpenFailed', ...
        'Could not open PNG for reading: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
bytes = fread(fid, Inf, '*uint8');

signature = uint8([137 80 78 71 13 10 26 10]).';
if numel(bytes) < 8 || ~isequal(bytes(1:8), signature)
    error('CMDO:UnsupportedCompatibilityPng', ...
        'Invalid PNG signature: %s', path);
end

position = 9;
width = [];
height = [];
idatParts = cell(0,1);
sawEnd = false;
while position + 11 <= numel(bytes)
    chunkLength = read_be_u32(bytes(position:position+3));
    chunkType = char(bytes(position+4:position+7).');
    dataStart = position + 8;
    dataEnd = dataStart + double(chunkLength) - 1;
    crcEnd = dataEnd + 4;
    if crcEnd > numel(bytes)
        error('CMDO:TruncatedCompatibilityPng', ...
            'Truncated PNG chunk in %s.', path);
    end

    switch chunkType
        case 'IHDR'
            if chunkLength ~= 13
                error('CMDO:InvalidCompatibilityPngHeader', ...
                    'Invalid IHDR length in %s.', path);
            end
            header = bytes(dataStart:dataEnd);
            width = read_be_u32(header(1:4));
            height = read_be_u32(header(5:8));
            bitDepth = double(header(9));
            colorType = double(header(10));
            compressionMethod = double(header(11));
            filterMethod = double(header(12));
            interlaceMethod = double(header(13));
            if bitDepth ~= 8 || colorType ~= 2 || ...
                    compressionMethod ~= 0 || filterMethod ~= 0 || ...
                    interlaceMethod ~= 0
                error('CMDO:UnsupportedCompatibilityPng', [ ...
                    'Expected a non-interlaced 8-bit true-colour PNG; ' ...
                    'received bitDepth=%d, colorType=%d, interlace=%d: %s'], ...
                    bitDepth, colorType, interlaceMethod, path);
            end
        case 'IDAT'
            idatParts{end+1,1} = bytes(dataStart:dataEnd); %#ok<AGROW>
        case 'IEND'
            sawEnd = true;
            break;
    end
    position = crcEnd + 1;
end

if isempty(width) || isempty(height) || isempty(idatParts) || ~sawEnd
    error('CMDO:IncompleteCompatibilityPng', ...
        'PNG is missing IHDR, IDAT or IEND content: %s', path);
end
idatStream = vertcat(idatParts{:});
end

function value = read_be_u32(bytes)
bytes = double(bytes(:));
if numel(bytes) ~= 4
    error('CMDO:InvalidBigEndianInteger', ...
        'Expected exactly four bytes for a PNG integer.');
end
value = bytes(1) * 2^24 + bytes(2) * 2^16 + ...
    bytes(3) * 2^8 + bytes(4);
end

function fclose_if_open(fid)
if isnumeric(fid) && isscalar(fid) && fid >= 0
    fclose(fid);
end
end

function delete_if_present(path)
if isfile(path)
    delete(path);
end
end
