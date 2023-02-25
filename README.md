# Emo: emoji for all (ahem, modern LaTeX engines)

This package defines the `\emo{<emoji-name>}` macro for including color emoji in
a document no matter the input encoding or LaTeX engine. It uses the Noto color
emoji font if the engine supports doing so and falls back onto PDF graphics
otherwise. When used with the `extra` option, this package also defines the
`\lingchi` and `\YHWH` macros. When used with the `index` option, this package
also emits raw index entries in `.`

To extract the files embedded in [emo.dtx](emo.dtx) and build the
[documentation](emo.pdf), run `pdflatex emo.dtx`. To install this package, place
the resulting `emo.sty`, the Noto font files, and the `emo-graphics` directory
somewhere where LaTeX can find them. In a pinch, your project directory with all
the other source files is just fine.

## Licensing

This package's LaTeX code is © Copyright 2023 by Robert Grimm and has been
released under the [LPPL v1.3c](https://www.latex-project.org/lppl/lppl-1-3c/)
or later. The Noto fonts distributed with the package are subject to the [SIL
Open Font License v1.1](https://scripts.sil.org/ofl), while the PDF files in the
`emo-graphics` directory are distributed under the [Apache 2.0
license](https://www.apache.org/licenses/LICENSE-2.0), just like the [original
SVG files](https://github.com/googlefonts/noto-emoji).

