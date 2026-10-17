# MAPIS thesis (Amrita B.Tech template)

Built from the department's `Thesis_Template___Amrita_AIE` LaTeX template (`mythesis.tex`, `chapters/`, `mybib.bib`, `images/`).

- Title page background is silver (`#C0C0C0`), as required for the hard-bound copy; all other pages are white.
- Build (pdfLaTeX + BibTeX, run pdflatex twice after bibtex):
  `pdflatex mythesis.tex && bibtex mythesis && pdflatex mythesis.tex && pdflatex mythesis.tex`
- Overleaf: upload the whole folder (or the zip `MAPIS_Thesis_Source.zip`) and set the main file to `mythesis.tex`.
- Compiled copy: `MAPIS_Thesis.pdf` (42 pages).
- Chapters: 1 Introduction, 2 Literature Review, 3 System Design, 4 Datasets, 5 Model/Training/Implementation, 6 Results, 7 Live Agents and Dashboard, 8 Conclusion, Appendix A reproduction guide.

Before printing: add the date of the examination on the bonafide page, and have the advisor, examiners and the Dean sign (hard copy must be signed).
Check the advisor's designation on the bonafide page and the declaration (currently "Professor") and the place and date lines.
