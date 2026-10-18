# MAPIS final slides (LaTeX Beamer)

Laid out like the faculty's reference final presentation (Beamer, Madrid theme, beaver colours, sections: Introduction, Base work, Implementation, Modification, Conclusion; numbers macro file; team-contribution blocks; Thank You slide).

Build: `python make_report.py` (writes `figures/*.png` and `figures/numbers.tex` from `data/`), then `pdflatex mapis_final_slides.tex` twice. No BibTeX pass (inline bibliography).
Files: `mapis_final_slides.tex`, `make_report.py`, `data/` (seed-42 benchmark and both training histories), `figures/`, compiled `MAPIS_Final_Slides.pdf` (20 pages).

Mapping to the course guidelines (written for an image-processing course): task = binary classification of agent events, so the figure is the confusion matrix and the table metrics are accuracy, precision, recall, F1.
Base work: no base paper reports numbers on this test set, so the replicated baseline (stateless DeBERTa, plus public detectors) was trained or run by us on identical sessions; the slides say so.
