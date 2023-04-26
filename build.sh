# Test emo
pdflatex -jobname=pdftex-canary canary
xelatex -jobname=xetex-canary canary
lualatex -jobname=luatex-canary canary
pdfunite pdftex-canary.pdf xetex-canary.pdf luatex-canary.pdf canary.pdf

# Document emo
pdflatex emo.dtx
makeindex -s gind.ist -o emo.ind emo.idx
makeindex -s gglo.ist -o emo.gls emo.glo
pdflatex emo.dtx
pdflatex emo.dtx
