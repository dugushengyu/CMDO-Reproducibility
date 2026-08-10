# R4.2 compatibility-PDF validation

## Scope

The R4 local acceptance run passed the environment, seven canonical-archive
hashes, twenty imported-source hashes, ten MATLAB tests, thirteen figure
actions and thirteen compatibility-PDF write actions.  External inspection
confirmed that all thirteen source PNGs are visually acceptable and preserve
the frozen results.  The ordinary vector PDFs remain scientifically correct,
but Poppler expands some font spacing.

## Defect found in the R4 compatibility export

The first image-only PDF implementation routed each PNG through an invisible
MATLAB axes and called `exportgraphics` on that axes.  Poppler and Ghostscript
both showed that this could tighten the right or lower canvas.  Figure 4d made
the defect visible because its rightmost point and annotation were clipped.
The PNG and TIFF were not affected.

## R4.2 writer and independent checks

R4.2 embeds the PNG IDAT stream directly as a PDF FlateDecode image with PNG
prediction.  The page dimensions are exactly `pixel size / 600 dpi * 72`, and
the PDF contains no live fonts.

An independent implementation of the same PDF structure was exercised on all
thirteen accepted PNGs before packaging the MATLAB hotfix.  For every figure:

- the PDF opened as a one-page document in Poppler and Ghostscript;
- the embedded image dimensions matched the source PNG;
- horizontal and vertical resolution were both 600 dpi;
- the PDF contained zero fonts;
- extracting the embedded image produced zero differing pixels relative to
  the source PNG.

The MATLAB implementation still requires one local execution on the accepted
Windows R2024b environment.  External visual review remains pending until the
rebuilt PDFs are returned and rendered independently.
