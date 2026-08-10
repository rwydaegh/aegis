.PHONY: all main si pm-assemble pm-roundtrip clean

all: paper.pdf paper_SI.pdf

main: paper.pdf

si: paper_SI.pdf

pm-assemble:
	uv run --project /home/user/PaperMaker9000 papermaker assemble main --out paper.tex

pm-roundtrip:
	uv run --project /home/user/PaperMaker9000 papermaker roundtrip main --source paper.tex

paper.pdf: paper.tex $(wildcard figures/*.pdf) $(wildcard figures/*.png)
	pdflatex -interaction=nonstopmode paper.tex
	pdflatex -interaction=nonstopmode paper.tex

paper_SI.pdf: paper_SI.tex $(wildcard figures/*.pdf)
	pdflatex -interaction=nonstopmode paper_SI.tex
	pdflatex -interaction=nonstopmode paper_SI.tex

clean:
	rm -f *.aux *.log *.out *.acn *.ist *.glo *.glg *.gls *.toc *.bbl *.blg *.fdb_latexmk *.fls *.synctex.gz
	rm -rf build/papermaker
