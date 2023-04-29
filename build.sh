# Test emo
pdflatex -jobname=pdftex-canary canary
xelatex -jobname=xetex-canary canary
lualatex -jobname=luatex-canary canary
pdfunite pdftex-canary.pdf xetex-canary.pdf luatex-canary.pdf canary.pdf

# LaTeXML: --includestyles handles emo-test class
latexmlc --includestyles --dest=demo-latexml.html demo.tex

# TeX4ht: -l is necessary for selecting LuaTeX engine
make4ht -l -j demo-tex4ht demo.tex

# Document emo
pdflatex emo.dtx
makeindex -s gind.ist -o emo.ind emo.idx
makeindex -s gglo.ist -o emo.gls emo.glo
pdflatex emo.dtx
pdflatex emo.dtx
