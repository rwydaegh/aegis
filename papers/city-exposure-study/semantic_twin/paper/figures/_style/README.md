# Shared paper figure style

`paper_style.py` applies the SciencePlots `science` and `ieee` styles, then
adds the dimensions and font settings of the May 2026 IEEE Access class.

The exact source widths are 85.29 mm for one column and 177.53 mm for two
columns. `paper_style("single")` and `paper_style("double")` select these
widths. The helper uses TeX with New TX text and math fonts. PDF and PostScript
font embedding is explicit. The palette is safe for common color-vision
deficiencies. Line patterns and hollow marker shapes repeat every color choice,
so grayscale output remains interpretable.

Use the durable paper dependencies from the semantic-twin project:

```bash
uv run --project semantic_twin --extra paper python \
  semantic_twin/paper/figures/_style/smoke_figure.py
```

`save_figure` leaves the canvas uncropped. This preserves the exact requested
width and gives deterministic PDF metadata. The smoke test writes both PDF and
PNG review copies. Check the PDF with `pdffonts`; its `type` column must not
contain `Type 3`.
