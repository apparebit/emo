pdflatex emo.dtx
makeindex -s gind.ist -o emo.ind emo.idx
# makeindex -s gglo.ist -o emo.gls emo.glo  # For tracking changes
pdflatex emo.dtx
