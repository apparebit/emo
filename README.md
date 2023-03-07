# Emo: emoji for all (LaTeX engines)

This package defines the `\emo{<emoji-name>}` macro for including color emoji 🎉
in a document no matter the input encoding or LaTeX engine. It uses the Noto
color emoji font if the engine supports doing so and falls back onto PDF
graphics otherwise. When used with the `extra` option, this package also defines
the `\lingchi` and `\YHWH` macros for 凌遲 and יהוה, respectively. Both macros
preserve a subsequent space as space, no backslash needed. When used with the
`index` option, this package also emits raw index entries in an `.edx` file.

To extract the files embedded in [emo.dtx](emo.dtx) and build the
[documentation](emo.pdf), run `pdflatex emo.dtx`. To install this package, place
the resulting `emo.sty`, the Noto font files, and the `emo-graphics` directory
somewhere where LaTeX can find them. In a pinch, your project directory with all
the other source files is just fine.

## Supported Emoji

⚖️ ☣️ ✔️ 🏛 🏝 😡 🇪🇺 👁 💾 🌁 🌍 🤝 🧑‍⚖️ 1️⃣ 🏷 🔍 📟 🦜 🧾 🤖 🏟 🛑 📐 🗑

Apparently, these are the most critical emoji to my writing. I'm automating the
file conversion and record keeping for this package, so coverage will increase
soon enough.

## Implementation

The implementation depends on a PDF file for each distinct emoji and LaTeX
commands defining valid emoji names. I manually assembled currently supported
emoji based on the [SVG sources](https://github.com/googlefonts/noto-emoji) for
the Noto color emoji font, hence only less than 0.1% of all defined emoji are
included. But I learned more than I wanted to about PDF files and `/Page`
`/Group` objects that trip up `pdflatex` and [am automating](scripts/emo.py) PDF
file generation and LaTeX command creation.

While the package ships with Noto fonts for Simplified Chinese and Hebrew to
enable the extra macros, it does not include the all critical Noto color emoji
font. The latter is already included with major TeX distributions.

## Licensing

This package's LaTeX code is © Copyright 2023 by Robert Grimm and has been
released under the [LPPL v1.3c](https://www.latex-project.org/lppl/lppl-1-3c/)
or later. The Noto fonts distributed with the package are subject to the [SIL
Open Font License v1.1](https://scripts.sil.org/ofl), while the PDF files in the
`emo-graphics` directory are distributed under the [Apache 2.0
license](https://www.apache.org/licenses/LICENSE-2.0), just like the [original
SVG files](https://github.com/googlefonts/noto-emoji).

