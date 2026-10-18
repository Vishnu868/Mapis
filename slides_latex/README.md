# MAPIS final slides (LaTeX Beamer)

Structure follows the faculty's final-project presentation guidelines (22AIE437): introduction, base work and replicated baseline, implementation with logs, modification and comparison, conclusion and contributions. 15 slides plus 2 pages of references (17 pages in the PDF).

Build: `pdflatex mapis_final_slides.tex && bibtex mapis_final_slides && pdflatex mapis_final_slides.tex && pdflatex mapis_final_slides.tex`
Files: `mapis_final_slides.tex`, `refs.bib`, `images/`, compiled `MAPIS_Final_Slides.pdf`.

Mapping to the guidelines (written for an image-processing course): the task is binary classification of agent events, so the required figure is the confusion matrix and the table metrics are accuracy, precision, recall and F1. The "base paper" slot is filled by the replicated base architecture (stateless DeBERTa classifier, public detectors on identical sessions) because no single base paper's model is reproduced end to end; the slides say so.
