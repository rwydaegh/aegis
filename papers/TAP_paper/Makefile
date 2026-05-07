.PHONY: all main si clean

all: paper.pdf paper_SI.pdf

main: paper.pdf

si: paper_SI.pdf

paper.pdf: paper.tex $(wildcard figures/*.pdf) $(wildcard figures/*.png)
	pdflatex -interaction=nonstopmode paper.tex
	pdflatex -interaction=nonstopmode paper.tex

paper_SI.pdf: paper_SI.tex $(wildcard figures/*.pdf)
	pdflatex -interaction=nonstopmode paper_SI.tex
	pdflatex -interaction=nonstopmode paper_SI.tex

clean:
	rm -f *.aux *.log *.out *.acn *.ist *.glo *.glg *.gls *.toc *.bbl *.blg *.fdb_latexmk *.fls *.synctex.gz
